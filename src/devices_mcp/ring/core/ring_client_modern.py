"""
Modern Ring API Client using python-ring-doorbell.

This module provides an asynchronous interface to Ring devices using the official
python-ring-doorbell library, which handles the reverse-engineered Ring API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any, Union, cast

import aiocache
from ring_doorbell import Auth, Ring, RingDoorBell, RingStickUpCam
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import (
    AuthenticationError,
    DeviceNotFoundError,
    RateLimitError,
    RingError,
    StreamingError,
)
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

# Type aliases
RingDevice = Union[RingDoorBell, RingStickUpCam]
DeviceData = dict[str, Any]

# Cache configuration
CACHE_TTL = 300  # 5 minutes


class RingClient:
    """Modern Ring client with async support and rate limiting."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        cache_ttl: int = CACHE_TTL,
        token_storage_path: str | None = None,
    ):
        """Initialize the Ring client.

        Args:
            username: Ring account username
            password: Ring account password
            token: OAuth token (alternative to username/password)
            cache_ttl: Cache TTL in seconds
            token_storage_path: Optional path to store tokens securely
        """
        self.username = username or os.getenv("RING_USERNAME")
        self.password = password or os.getenv("RING_PASSWORD")
        self.token = token or os.getenv("RING_TOKEN")
        self.cache_ttl = cache_ttl

        self._ring: Ring | None = None
        self._auth: Auth | None = None
        self._devices: dict[str, RingDevice] = {}
        self._token_manager = TokenManager(storage_path=token_storage_path)
        self._token_refresh_task: asyncio.Task | None = None

        # Initialize cache
        self.cache = aiocache.Cache(
            aiocache.SimpleMemoryCache,
            ttl=cache_ttl,
            namespace="ring_mcp",
        )

    async def __aenter__(self) -> RingClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _load_saved_token(self) -> bool:
        """Load and validate a saved token from the token manager.

        Returns:
            bool: True if a valid token was loaded, False otherwise
        """
        if not self.username:
            return False

        try:
            # Load tokens from storage
            await self._token_manager.load_tokens()

            # Try to get a valid token
            token_data = await self._token_manager.get_token(self.username)
            if not token_data:
                return False

            # Use the token to authenticate
            self.token = token_data  # Store the full token data dict
            self._auth = Auth("ring_mcp/1.0", self.token, token_updater=self._on_token_updated)

            # Initialize Ring with the auth
            self._ring = Ring(self._auth)

            # Verify the token is still valid by making a simple API call
            await asyncio.to_thread(self._ring.devices)

            logger.info("Successfully authenticated with saved token")
            return True

        except Exception as e:
            logger.warning("Failed to use saved token: %s", str(e))
            return False

    def _on_token_updated(self, token: dict[str, Any]) -> None:
        """Callback when the token is updated by the Ring API.

        Args:
            token: The updated token data
        """
        if not self.username:
            return

        logger.debug("Token updated, saving new token")

        # Schedule the token save in the event loop
        if asyncio.iscoroutinefunction(self._token_manager.save_token):
            asyncio.create_task(
                self._token_manager.save_token(
                    username=self.username,
                    access_token=token["access_token"],
                    refresh_token=token.get("refresh_token"),
                    expires_in=token.get("expires_in", 3600),
                )
            )

    async def _start_token_refresh_task(self) -> None:
        """Start a background task to refresh tokens before they expire."""
        if self._token_refresh_task and not self._token_refresh_task.done():
            return

        async def refresh_loop() -> None:
            while True:
                try:
                    if not self.username or not self._ring:
                        await asyncio.sleep(60)  # Check again in 1 minute
                        continue

                    # Get the current token data
                    token_data = await self._token_manager.get_token(self.username)
                    if not token_data:
                        await asyncio.sleep(300)  # Check again in 5 minutes
                        continue

                    # Calculate when to refresh (5 minutes before expiration)
                    expires_at = datetime.fromisoformat(token_data["expires_at"])
                    now = datetime.utcnow()
                    refresh_time = expires_at - timedelta(minutes=5)

                    if now >= refresh_time:
                        # Time to refresh
                        logger.info("Refreshing token before expiration")
                        try:
                            # This will trigger _on_token_updated with the new token
                            await asyncio.to_thread(self._ring.update_data)
                        except Exception as e:
                            logger.exception("Failed to refresh token: %s", str(e))

                    # Sleep until it's time to refresh or for a maximum of 1 hour
                    sleep_time = min((refresh_time - now).total_seconds(), 3600)
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                except Exception as e:
                    logger.exception("Error in token refresh loop: %s", str(e))
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying

        self._token_refresh_task = asyncio.create_task(refresh_loop())

    async def connect(self, two_factor_callback: Callable[[], Awaitable[str]] | None = None) -> None:
        """Initialize connection to Ring API with support for 2FA and token management.

        Args:
            two_factor_callback: Optional async callback function that will be called if 2FA is required.
                The function should return the 2FA code as a string.
                If not provided, will raise AuthenticationError when 2FA is required.
        """
        if self._ring is not None:
            return

        try:
            # First, try to use a saved token if available
            if not self.token and self.username and await self._load_saved_token():
                # Successfully loaded and validated a saved token
                await self._start_token_refresh_task()
                return

            # If we have a token, try to use it directly
            if self.token:
                self._auth = Auth("ring_mcp/1.0", self.token, token_updater=self._on_token_updated)
            # Fall back to username/password
            elif self.username and self.password:
                # Create Auth object
                self._auth = Auth("ring_mcp/1.0", token_updater=self._on_token_updated)

                try:
                    # First try without 2FA
                    token = await self._auth.async_fetch_token(self.username, self.password)
                    logger.info("Successfully authenticated with Ring API")
                except Exception as e:
                    # Check if 2FA is required
                    if "Verification Code" in str(e) or "2FA" in str(e) or "verification" in str(e).lower():
                        logger.info("2FA verification code required")
                        if two_factor_callback and asyncio.iscoroutinefunction(two_factor_callback):
                            # Get 2FA code from callback
                            two_factor_code = await two_factor_callback()
                            if not two_factor_code:
                                raise AuthenticationError("2FA code is required but not provided")

                            # Retry with 2FA code
                            token = await self._auth.async_fetch_token(self.username, self.password, two_factor_code)
                            logger.info("Successfully authenticated with Ring API (with 2FA)")
                        else:
                            raise AuthenticationError("2FA is required but no callback provided")
                    else:
                        raise AuthenticationError(f"Authentication failed: {e}")

                # Extract token from auth object
                self.token = self._auth._token

                # Save the new token
                if self.username and self.token:
                    await self._token_manager.save_token(
                        username=self.username,
                        access_token=self.token,
                        refresh_token=getattr(self._auth, "refresh_token", None),
                        expires_in=3600,  # Default expiration
                    )
            else:
                raise AuthenticationError("Either a valid token or username/password is required")

            # Initialize the Ring API client
            self._ring = Ring(self._auth)

            # Update device cache
            await self._update_devices()

            # Start the token refresh task
            await self._start_token_refresh_task()

            logger.info("Successfully connected to Ring API")

        except Exception as e:
            self._ring = None
            self._auth = None
            logger.exception("Failed to connect to Ring API: %s", str(e))
            raise AuthenticationError(f"Failed to authenticate with Ring: {e!s}") from e

    async def close(self) -> None:
        """Close the Ring client and clean up resources."""
        # Cancel the token refresh task if it's running
        if self._token_refresh_task and not self._token_refresh_task.done():
            self._token_refresh_task.cancel()
            try:
                await self._token_refresh_task
            except asyncio.CancelledError:
                pass
            self._token_refresh_task = None

        if self._ring is not None:
            try:
                # Clear any active sessions
                await asyncio.to_thread(self._ring.update_data, force_logout=True)
            except Exception as e:
                logger.warning("Error during logout: %s", str(e))
            finally:
                self._ring = None
                self._auth = None

        # Clear the cache
        try:
            await self.cache.clear()
        except Exception as e:
            logger.warning("Error clearing cache: %s", str(e))

        self._devices.clear()

        logger.info("Ring client closed")

    def _save_token(self, token: str) -> None:
        """Callback to save the updated OAuth token."""
        self.token = token
        # In a real application, you'd want to persist this token
        logger.debug("Received new OAuth token")

    @retry(
        retry=retry_if_exception_type((RateLimitError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an authenticated request to the Ring API with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to the request

        Returns:
            The response from the API

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            RingConnectionError: For network-related errors
            RingError: For other Ring API errors
        """

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((RateLimitError, asyncio.TimeoutError)),
            reraise=True,
        )
        async def _request():
            try:
                # Ensure we're connected
                if not self._ring or not self._auth:
                    await self.connect()

                # Make the request with timeout
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            getattr(self._auth, method.lower()),
                            f"https://api.ring.com/clients_api{endpoint}",
                            **kwargs,
                        ),
                        timeout=60.0,  # 60 second timeout for API requests
                    )
                except TimeoutError as e:
                    raise RingConnectionError("Request to Ring API timed out") from e

                # Check for rate limiting and other error responses
                if isinstance(response, dict):
                    if response.get("code") == 429:
                        retry_after = int(response.get("retry_after", 60))
                        logger.warning("Rate limit exceeded. Retrying after %s seconds", retry_after)
                        raise RateLimitError(
                            f"Rate limit exceeded. Try again in {retry_after} seconds.",
                            retry_after=retry_after,
                        )
                    if response.get("code") == 401:
                        # Clear the auth token if it's invalid
                        self._auth = None
                        self._ring = None
                        logger.error("Authentication failed: %s", response.get("error", "Unknown error"))
                        raise AuthenticationError("Invalid or expired token. Please re-authenticate.")
                    if "error" in response:
                        error_msg = response.get("error", "Unknown error")
                        logger.error("Ring API error: %s", error_msg)

                        # Handle specific error cases
                        if "not found" in str(error_msg).lower():
                            raise DeviceNotFoundError(f"Resource not found: {endpoint}")
                        if "permission" in str(error_msg).lower():
                            raise AuthenticationError("Insufficient permissions to access this resource")
                        raise RingError(f"Ring API error: {error_msg}")

                return response

            except (requests.exceptions.RequestException, httpx.RequestError) as e:
                # Handle network-related errors
                error_msg = str(e).lower()
                if "timeout" in error_msg or "timed out" in error_msg:
                    raise RingConnectionError("Connection to Ring API timed out") from e
                if "connection" in error_msg or "network" in error_msg:
                    raise RingConnectionError("Network error connecting to Ring servers") from e
                raise RingError(f"Request failed: {e!s}") from e

            except json.JSONDecodeError as e:
                raise RingError("Failed to parse response from Ring API") from e

            except Exception as e:
                # For any other unexpected errors, wrap them in RingError
                raise RingError(f"Unexpected error: {e!s}") from e

        try:
            return await _request()
        except Exception as e:
            # Log the full error with traceback for debugging
            logger.exception("Error in _make_request: %s", str(e))
            raise

    async def _update_devices(self) -> None:
        """Update the internal device cache."""
        if self._ring is None:
            raise RingError("Not connected to Ring API")

        try:
            # Get all devices from Ring with retry logic
            devices = await asyncio.to_thread(
                lambda: list(self._ring.devices())  # type: ignore
            )

            # Update internal device cache
            self._devices = {str(device.id): device for device in devices if hasattr(device, "id")}

            logger.info("Updated device cache with %d devices", len(self._devices))

        except Exception as e:
            logger.exception("Failed to update devices: %s", str(e))
            if "429" in str(e):
                raise RateLimitError("Rate limit exceeded while updating devices") from e
            if "401" in str(e):
                self._auth = None  # Clear invalid auth
                raise AuthenticationError("Authentication failed while updating devices") from e
            raise RingError(f"Failed to update devices: {e!s}") from e

    async def get_devices(self, force_refresh: bool = False) -> list[DeviceData]:
        """Get all Ring devices.

        Args:
            force_refresh: If True, force refresh the device cache.

        Returns:
            List of device dictionaries with their details.
        """
        cache_key = f"devices_{self.username}"

        if not force_refresh:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cast("list[DeviceData]", cached)

        if not self._devices or force_refresh:
            await self._update_devices()

        devices_data = []
        for device_id, device in self._devices.items():
            try:
                device_info = await self._get_device_info(device)
                devices_data.append(device_info)
            except Exception as e:
                logger.exception("Error getting info for device %s: %s", device_id, str(e))

        await self.cache.set(cache_key, devices_data, ttl=self.cache_ttl)
        return devices_data

    async def _get_device_info(self, device: RingDevice) -> DeviceData:
        """Get standardized device information."""
        device_info: DeviceData = {
            "id": str(device.id),
            "name": device.name,
            "type": device.family,
            "model": device.model,
            "firmware": device.firmware,
            "battery_life": getattr(device, "battery_life", None),
            "alarm": getattr(device, "alarm", None),
            "online": device.online,
            "address": getattr(device, "address", None),
            "timezone": getattr(device, "timezone", None),
            "has_subscription": getattr(device, "has_subscription", False),
            "last_update": datetime.utcnow().isoformat(),
        }
        return device_info

    async def get_device(self, device_id: str) -> DeviceData | None:
        """Get a specific device by ID."""
        devices = await self.get_devices()
        return next((d for d in devices if d["id"] == device_id), None)

    async def get_device_events(self, device_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent events for a device."""
        if not self._devices:
            await self._update_devices()

        device = self._devices.get(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        try:
            events = await asyncio.to_thread(lambda: device.history(limit=limit, kind="alarm"))
            return [
                {
                    "id": str(e["id"]),
                    "created_at": e["created_at"],
                    "answered": e.get("answered", False),
                    "kind": e.get("kind"),
                    "recording_status": e.get("recording", {}).get("status"),
                }
                for e in events
                if e
            ]
        except Exception as e:
            logger.exception("Error getting events for device %s: %s", device_id, str(e))
            raise RingError(f"Failed to get device events: {e!s}") from e

    async def get_live_stream_url(self, device_id: str) -> str:
        """Get a live stream URL for a camera device."""
        if not self._devices:
            await self._update_devices()

        device = self._devices.get(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        if not hasattr(device, "live_streaming"):
            raise StreamingError("Device does not support live streaming")

        try:
            # This will trigger the camera to start streaming
            stream_url = await asyncio.to_thread(lambda: device.live_streaming.rtsp_url)
            if not stream_url:
                raise StreamingError("Failed to get stream URL")

            return stream_url

        except Exception as e:
            logger.exception("Error getting stream URL for %s: %s", device_id, str(e))
            raise StreamingError(f"Failed to get stream URL: {e!s}") from e

    async def set_arm_status(self, device_id: str, status: bool) -> bool:
        """Arm or disarm a security device."""
        if not self._devices:
            await self._update_devices()

        device = self._devices.get(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        if not hasattr(device, "alarm"):
            raise RingError("Device does not support arming/disarming")

        try:
            result = await asyncio.to_thread(lambda: device.alarm.set_status("home" if status else "disarmed"))
            # Invalidate cache
            await self.cache.delete(f"devices_{self.username}")
            return bool(result)

        except Exception as e:
            logger.exception("Error setting arm status for %s: %s", device_id, str(e))
            raise RingError(f"Failed to set arm status: {e!s}") from e

    async def trigger_chime(self, device_id: str) -> bool:
        """Trigger a doorbell chime."""
        if not self._devices:
            await self._update_devices()

        device = self._devices.get(device_id)
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        if not hasattr(device, "test_sound"):
            raise RingError("Device does not support chime testing")

        try:
            return await asyncio.to_thread(device.test_sound)

        except Exception as e:
            logger.exception("Error triggering chime for %s: %s", device_id, str(e))
            raise RingError(f"Failed to trigger chime: {e!s}") from e
