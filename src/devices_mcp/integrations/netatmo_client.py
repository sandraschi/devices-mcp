"""
Netatmo Weather Station Integration Client

Uses pyatmo 8.x async API to fetch real weather data from Netatmo stations.
Falls back to simulated data if not configured or on error.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

from ..config import get_model
from ..config.models import WeatherSettings
from ..db import TimeSeriesDB
from ..utils import get_logger

logger = get_logger(__name__)


# Check if pyatmo is available
try:
    import pyatmo
    from pyatmo.auth import AbstractAsyncAuth
    from pyatmo.exceptions import ApiError as PyatmoApiError

    PYATMO_AVAILABLE = True
except ImportError:
    PYATMO_AVAILABLE = False
    AbstractAsyncAuth = object  # type: ignore[misc,assignment]
    PyatmoApiError = Exception  # type: ignore[misc,assignment]


@dataclass
class NetatmoConfig:
    enabled: bool
    client_id: str | None
    client_secret: str | None
    redirect_uri: str | None
    refresh_token: str | None
    username: str | None
    password: str | None
    home_id: str | None


def get_netatmo_config() -> NetatmoConfig:
    cfg = get_model(WeatherSettings)
    netatmo_dict = cfg.integrations.get("netatmo", {}) if cfg else {}
    return NetatmoConfig(
        enabled=bool(netatmo_dict.get("enabled", False)),
        client_id=netatmo_dict.get("client_id"),
        client_secret=netatmo_dict.get("client_secret"),
        redirect_uri=netatmo_dict.get("redirect_uri"),
        refresh_token=netatmo_dict.get("refresh_token"),
        username=netatmo_dict.get("username"),
        password=netatmo_dict.get("password"),
        home_id=netatmo_dict.get("home_id"),
    )


class NetatmoOAuth2Auth(AbstractAsyncAuth):
    """OAuth2 authentication handler for pyatmo 8.x using refresh token."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        token_update_callback=None,
    ):
        super().__init__(websession)
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token: str | None = None
        self._token_expiry: float = 0
        self._token_update_callback = token_update_callback  # Callback to save token updates

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        # Refresh the token
        url = "https://api.netatmo.com/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
        }

        try:
            async with self.websession.post(url, data=data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    error_msg = f"Token refresh failed: {resp.status} - {error_text}"
                    logger.error(f"Netatmo OAuth token refresh failed: {error_msg}")

                    # Check for specific error types
                    if "invalid" in error_text.lower() or "invalid_token" in error_text.lower():
                        raise RuntimeError(
                            f"Invalid refresh token. Please re-authenticate with Netatmo. Error: {error_text}"
                        )
                    if "expired" in error_text.lower():
                        raise RuntimeError(
                            f"Refresh token expired. Please re-authenticate with Netatmo. Error: {error_text}"
                        )
                    if resp.status == 401:
                        raise RuntimeError(
                            f"Authentication failed (401). Invalid credentials or token. Error: {error_text}"
                        )
                    if resp.status == 403:
                        raise RuntimeError(
                            f"Access forbidden (403). Check API permissions. Error: {error_text}"
                        )
                    raise RuntimeError(error_msg)

                try:
                    tokens = await resp.json()
                except Exception as json_error:
                    error_text = await resp.text()
                    error_msg = f"Failed to parse token response as JSON: {json_error}. Response: {error_text}"
                    logger.exception("Netatmo token response parsing failed:")
                    raise RuntimeError(error_msg) from json_error

                # Check if access_token is present in response
                if "access_token" not in tokens:
                    error_msg = (
                        f"Access token not found in response. Response keys: {list(tokens.keys())}"
                    )
                    logger.error(f"Netatmo token response missing access_token: {error_msg}")
                    # Check for error in response
                    if "error" in tokens:
                        error_desc = tokens.get(
                            "error_description", tokens.get("error", "Unknown error")
                        )
                        raise RuntimeError(
                            f"Netatmo API error: {error_desc}. Full response: {tokens}"
                        )
                    raise RuntimeError(f"Access token not found in Netatmo response: {error_msg}")

                self._access_token = tokens["access_token"]
                self._token_expiry = time.time() + tokens.get("expires_in", 10800)

                # Update refresh token if a new one was issued
                if "refresh_token" in tokens:
                    new_refresh_token = tokens["refresh_token"]
                    self._refresh_token = new_refresh_token
                    # Call callback to save token if provided
                    if self._token_update_callback:
                        try:
                            self._token_update_callback(new_refresh_token)
                        except Exception as e:
                            logger.warning(f"Failed to save refresh token via callback: {e}")
                    logger.info("Netatmo refresh token updated")

                logger.debug("Netatmo access token refreshed successfully")
                return self._access_token
        except RuntimeError:
            # Re-raise RuntimeError as-is (already has proper error message)
            raise
        except aiohttp.ClientError as e:
            error_msg = f"Network error refreshing Netatmo token: {e}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
        except KeyError as e:
            error_msg = f"Missing required field in Netatmo token response: {e}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error refreshing Netatmo token: {e}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e


class NetatmoService:
    """Netatmo weather station service with real API calls via pyatmo 8.x.

    Uses singleton pattern to ensure only one instance exists across the app.
    This prevents race conditions between web API, hardware_init, and connection_supervisor.
    """

    # Singleton instance
    _instance: NetatmoService | None = None
    _init_lock: asyncio.Lock | None = None

    @classmethod
    async def get_instance(cls, token_file: str = "netatmo_token.cache") -> NetatmoService:
        """Get or create the singleton NetatmoService instance.

        This ensures only one Netatmo connection exists across all components.
        """
        if cls._init_lock is None:
            cls._init_lock = asyncio.Lock()

        async with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls(token_file)

            # Initialize if not already done
            if not cls._instance._initialized:
                await cls._instance.initialize()

            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing or reconnection)."""
        cls._instance = None

    @classmethod
    def get_existing_instance(cls) -> NetatmoService | None:
        """Return the singleton if it exists (may not be connected to the API yet)."""
        return cls._instance

    @classmethod
    async def reset_for_reconnect(cls) -> None:
        """Close the current singleton (session, background task) so a fresh login can run."""
        if cls._instance is not None:
            await cls._instance.close()
        cls._instance = None

    def __init__(self, token_file: str = "netatmo_token.cache") -> None:
        self.config = get_netatmo_config()
        self._initialized = False
        self._last_error: str | None = None
        self._account: Any = None  # pyatmo.AsyncAccount
        self._session: aiohttp.ClientSession | None = None
        self._db = TimeSeriesDB()
        self._use_real_api = False
        # Token cache file for persisting refresh token updates
        self.token_file = self._adjust_token_path(token_file)
        # Load refresh token from cache if available (overrides config)
        self._load_token_cache()

        # Background update task
        self._background_task: asyncio.Task | None = None
        self._last_update_success: float = 0
        self._update_interval = 600  # 10 minutes (Netatmo update rate)

    @staticmethod
    def _adjust_token_path(token_file: str) -> Path:
        """Adjust token file path for Docker vs native environments."""
        import os

        token_path = Path(token_file)
        # In Docker, store tokens in /app/tokens (mounted volume)
        if os.getenv("CONTAINER") == "yes" or Path("/.dockerenv").exists():
            tokens_dir = Path("/app/tokens")
            tokens_dir.mkdir(parents=True, exist_ok=True)
            return tokens_dir / token_path.name
        if token_path.is_absolute():
            return token_path
        # Repo root: .../src/devices_mcp/integrations/netatmo_client.py -> parents[3]
        root = Path(__file__).resolve().parents[3]
        return root / token_path.name

    def _load_token_cache(self) -> None:
        """Load refresh token from cache file if it exists (overrides config)."""
        if self.token_file.exists():
            try:
                with open(self.token_file) as f:
                    cached_token = f.read().strip()
                    if cached_token:
                        logger.info(f"Loaded Netatmo refresh token from cache: {self.token_file}")
                        self.config.refresh_token = cached_token
            except Exception as e:
                logger.warning(f"Failed to load Netatmo token cache: {e}")

    def _save_token_cache(self, refresh_token: str) -> None:
        """Save refresh token to cache file for persistence across restarts."""
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as f:
                f.write(refresh_token)
            logger.info(f"Saved Netatmo refresh token to cache: {self.token_file}")
        except Exception:
            logger.exception("Failed to save Netatmo token cache:")

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def initialized(self) -> bool:
        return self._initialized

    def is_api_ready(self) -> bool:
        """True when OAuth session is up and pyatmo account object exists."""
        if not self._use_real_api or not self._account:
            return False
        if self._session is None or self._session.closed:
            return False
        return True

    async def initialize(self) -> None:
        """Initialize Netatmo client if enabled and credentials provided."""
        import asyncio

        if self._initialized and self._use_real_api:
            # Already successfully initialized with real API
            return

        # Don't set _initialized = True here! Only set after SUCCESSFUL init

        if not self.config.enabled:
            self._last_error = None
            logger.info("Netatmo disabled in config; using simulated data")
            return

        if not PYATMO_AVAILABLE:
            self._last_error = "pyatmo is not installed. Install with: pip install pyatmo"
            logger.warning(
                "pyatmo not installed; using simulated data. Install with: pip install pyatmo"
            )
            return

        # Check for required credentials
        if not all(
            [
                self.config.client_id,
                self.config.client_secret,
                self.config.refresh_token,
            ]
        ):
            self._last_error = (
                "Missing Netatmo OAuth settings: set client_id, client_secret, and refresh_token "
                "under weather.integrations.netatmo in config.yaml (see scripts/netatmo_oauth_helper.py)."
            )
            logger.warning(
                "Netatmo enabled but missing credentials (client_id, client_secret, refresh_token). "
                "Using simulated data."
            )
            return

        self._last_error = None

        try:
            # Create aiohttp session with IPv4-only connector to fix Windows DNS issues
            # Windows async DNS can fail with IPv6/IPv4 conflicts - force IPv4
            import socket

            from aiohttp import TCPConnector
            from aiohttp.resolver import DefaultResolver

            # Custom resolver that uses sync socket.getaddrinfo (works on Windows)
            class SyncDNSResolver(DefaultResolver):
                """Resolver that uses sync socket.getaddrinfo to bypass Windows async DNS bug."""

                async def resolve(self, host, port=0, family=socket.AF_INET):
                    loop = asyncio.get_event_loop()
                    # Use sync getaddrinfo in thread pool (works on Windows when async fails)
                    addrinfo = await loop.run_in_executor(
                        None, socket.getaddrinfo, host, port, family, socket.SOCK_STREAM
                    )
                    return [
                        {
                            "hostname": host,
                            "host": addr[4][0],
                            "port": port,
                            "family": family,
                            "proto": 0,
                            "flags": 0,
                        }
                        for addr in addrinfo
                    ]

            # Force IPv4 + sync DNS resolver to avoid Windows async DNS issues
            connector = TCPConnector(
                family=socket.AF_INET,  # Force IPv4 only
                resolver=SyncDNSResolver(),  # Use sync DNS resolver
                limit=10,
                limit_per_host=5,
            )
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)

            # Create auth handler with callback to save token updates
            auth = NetatmoOAuth2Auth(
                websession=self._session,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                refresh_token=self.config.refresh_token,
                token_update_callback=self._save_token_cache,
            )

            # Create account and fetch initial data with timeout
            self._account = pyatmo.AsyncAccount(auth)

            # Initial fetch to ensure we have data
            logger.info("Performing initial Netatmo data fetch...")
            try:
                await asyncio.wait_for(self._account.async_update_weather_stations(), timeout=15.0)
                self._last_update_success = time.time()
                logger.info(
                    f"Netatmo initialized: {len(self._account.homes)} homes, weather stations loaded"
                )

                # Start background update loop
                if self._background_task is None or self._background_task.done():
                    self._background_task = asyncio.create_task(self._update_loop())
                    logger.info("Netatmo background update loop started")

                self._use_real_api = True
                self._initialized = True
                self._last_error = None
            except Exception as e:
                logger.exception("Initial Netatmo data fetch failed:")
                self._last_error = (
                    f"Initial weather sync failed ({type(e).__name__}: {e}). "
                    "Background retries will continue; check token and network if this persists."
                )
                # We still consider it initialized if we have the account,
                # the background loop will try again
                self._use_real_api = True
                self._initialized = True
                if self._background_task is None or self._background_task.done():
                    self._background_task = asyncio.create_task(self._update_loop())

        except asyncio.TimeoutError:
            self._last_error = (
                "Netatmo API timed out during first sync. Check firewall, DNS, or api.netatmo.com reachability."
            )
            logger.exception(
                "Netatmo initialization timed out - async_update_weather_stations took too long"
            )
            if self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.debug(f"Error closing Netatmo session: {e}")
                self._session = None
            self._account = None
            self._use_real_api = False
            self._initialized = False
        except RuntimeError as e:
            # OAuth token refresh errors
            error_msg = str(e)
            self._last_error = error_msg
            if "Token refresh failed" in error_msg:
                logger.exception("Netatmo authentication failed during initialization:")
            else:
                logger.exception("Netatmo runtime error during initialization:")
            if self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.debug(f"Error closing Netatmo session: {e}")
                self._session = None
            self._account = None
            self._use_real_api = False
            self._initialized = False
        except AttributeError as e:
            self._last_error = f"pyatmo API mismatch or missing attribute: {e}"
            # pyatmo API changes or missing attributes
            logger.exception(
                f"Netatmo API attribute error during initialization (pyatmo version mismatch?): {e}"
            )
            if self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.debug(f"Error closing Netatmo session: {e}")
                self._session = None
            self._account = None
            self._use_real_api = False
            self._initialized = False
        except KeyError as e:
            self._last_error = f"Unexpected Netatmo API response shape (missing key: {e})"
            # Missing expected data in pyatmo response
            logger.exception("Netatmo API data structure error during initialization:")
            if self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.debug(f"Error closing Netatmo session: {e}")
                self._session = None
            self._account = None
            self._use_real_api = False
            self._initialized = False
        except aiohttp.ClientError as e:
            # Network/HTTP errors
            error_msg = str(e)
            error_type = type(e).__name__
            self._last_error = f"{error_type}: {error_msg}"
            if "getaddrinfo" in error_msg or "ClientConnectorDNSError" in error_type:
                logger.exception("Netatmo DNS error during initialization: {error_type}:")
                logger.exception(
                    "This indicates a network/DNS configuration issue, not just async DNS bug"
                )
            else:
                logger.exception(
                    f"Netatmo network error during initialization: {error_type}: {error_msg}"
                )
            if self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.debug(f"Error closing Netatmo session: {e}")
                self._session = None
            self._account = None
            self._use_real_api = False
            self._initialized = False
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            self._last_error = f"{error_type}: {error_msg}"
            # Log the actual error for debugging
            logger.exception("Failed to initialize Netatmo: {error_type}:")

            # Check if it's a DNS error - should already be using sync resolver, but log it
            if (
                "getaddrinfo" in error_msg
                or "ClientConnectorDNSError" in error_type
                or "DNS" in error_type
            ):
                logger.exception(
                    f"Netatmo DNS error persists even with sync DNS resolver: {error_type}: {error_msg}"
                )
                logger.exception(
                    "This indicates a network/DNS configuration issue, not just async DNS bug"
                )
            # Check for pyatmo-specific exceptions
            elif "pyatmo" in error_type.lower() or "netatmo" in error_type.lower():
                logger.exception(
                    f"Netatmo/pyatmo exception during initialization: {error_type}: {error_msg}"
                )
            else:
                logger.exception(
                    f"Unexpected error during Netatmo initialization: {error_type}: {error_msg}"
                )

            # Clean up and return - no simulated data
            if self._session:
                try:
                    await self._session.close()
                except Exception as e:
                    logger.debug(f"Error closing Netatmo session: {e}")
                self._session = None
            self._account = None
            self._use_real_api = False
            self._initialized = False

    async def _update_loop(self) -> None:
        """Background task to periodically update Netatmo data."""
        logger.info("Netatmo background update loop running")
        while True:
            try:
                await asyncio.sleep(self._update_interval)

                if not self._use_real_api or not self._account:
                    continue

                logger.debug("Running periodic Netatmo data update...")

                # Update data
                await self._refresh_data()

            except asyncio.CancelledError:
                logger.info("Netatmo background update loop cancelled")
                break
            except Exception:
                logger.exception("Error in Netatmo background update loop:")
                # Wait a bit before retrying to avoid tight loops on error
                await asyncio.sleep(60)

    async def _refresh_data(self) -> bool:
        """Internal method to refresh data from Netatmo API."""
        if not self._account:
            return False

        try:
            # Force token refresh logic is handled inside pyatmo/auth usually,
            # but we wrap the call to handle errors
            await asyncio.wait_for(self._account.async_update_weather_stations(), timeout=15.0)
            self._last_update_success = time.time()
            self._last_error = None
            logger.debug("Netatmo data updated successfully")
            return True
        except Exception:
            logger.exception("Failed to refresh Netatmo data:")
            # Try to handle token errors specifically?
            # For now just log and return False
            return False

    async def close(self) -> None:
        """Clean up resources."""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None

        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_session_valid(self) -> bool:
        """Check if session is valid and reinitialize if needed."""
        # Check if session exists and is open
        if self._session is None or self._session.closed:
            logger.warning("Netatmo session invalid/closed - reinitializing...")
            self._initialized = False
            self._session = None
            self._account = None
            self._use_real_api = False
            return False
        return True

    async def list_stations(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Return list of weather stations with basic info."""
        # Ensure session is valid before proceeding
        await self._ensure_session_valid()
        await self.initialize()

        if self._use_real_api and self._account:
            # Check if data is stale (over 15 minutes old) or force refresh requested
            is_stale = (time.time() - self._last_update_success) > 900

            if force_refresh or is_stale:
                logger.info(f"Refresing Netatmo data (force={force_refresh}, stale={is_stale})")
                await self._refresh_data()

            # Helper function to process stations
            def _process_stations():
                stations = []
                # Safety check for homes
                if not hasattr(self._account, "homes") or not self._account.homes:
                    return []

                for home_id, home in self._account.homes.items():
                    # Find weather station modules in this home
                    for module_id, module in home.modules.items():
                        if hasattr(module, "device_type") and "NAMain" in str(module.device_type):
                            station = {
                                "station_id": module_id,
                                "station_name": getattr(module, "name", "Weather Station"),
                                "location": home.name if hasattr(home, "name") else home_id,
                                "is_online": getattr(module, "reachable", True),
                                "home_id": home_id,
                                "modules": [],
                                "last_update": getattr(module, "last_seen", time.time()),
                            }

                            # Add connected modules
                            for sub_id, sub_module in home.modules.items():
                                if sub_id != module_id:
                                    mod_info = {
                                        "module_id": sub_id,
                                        "module_name": getattr(sub_module, "name", sub_id),
                                        "module_type": self._get_module_type(sub_module),
                                        "is_online": getattr(sub_module, "reachable", True),
                                        "battery_percent": getattr(sub_module, "battery", None),
                                    }
                                    station["modules"].append(mod_info)

                            stations.append(station)
                return stations

            try:
                # Just process the existing data in self._account
                stations = _process_stations()
                return stations

            except Exception:
                logger.exception("Error processing Netatmo stations:")
                return []

        # NO simulated data - return empty list
        logger.warning("Netatmo API unavailable - return empty list")
        return []

    async def current_data(self, station_id: str, module_type: str) -> tuple[dict[str, Any], float]:
        """Return current weather data and timestamp."""
        # Ensure session is valid before proceeding
        await self._ensure_session_valid()
        await self.initialize()

        if self._use_real_api and self._account:
            try:
                # Add timeout to prevent hanging on DNS errors
                import asyncio

                try:
                    await asyncio.wait_for(
                        self._account.async_update_weather_stations(), timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Netatmo data update timed out in current_data")
                    # Return empty data instead of raising
                    return {}, time.time()
                except RuntimeError as e:
                    # OAuth token refresh errors
                    error_msg = str(e)
                    if "Token refresh failed" in error_msg:
                        logger.exception("Netatmo authentication failed in current_data:")
                    else:
                        logger.exception("Netatmo runtime error in current_data:")
                    return {}, time.time()
                except AttributeError as e:
                    # pyatmo API changes or missing attributes
                    logger.exception(
                        f"Netatmo API attribute error in current_data (pyatmo version mismatch?): {e}"
                    )
                    return {}, time.time()
                except KeyError:
                    # Missing expected data in pyatmo response
                    logger.exception("Netatmo API data structure error in current_data:")
                    return {}, time.time()
                except PyatmoApiError as e:
                    # Handle pyatmo API errors (403 Invalid access token, etc.)
                    error_msg = str(e)
                    if "403" in error_msg or "Invalid access token" in error_msg:
                        logger.warning(
                            "Netatmo access token invalid (403) in current_data. Attempting token refresh..."
                        )
                        # Try to force token refresh and retry once
                        try:
                            if hasattr(self._account, "auth") and hasattr(
                                self._account.auth, "async_get_access_token"
                            ):
                                # Clear cached token AND expiry to force refresh
                                if hasattr(self._account.auth, "_access_token"):
                                    self._account.auth._access_token = None
                                if hasattr(self._account.auth, "_token_expiry"):
                                    self._account.auth._token_expiry = (
                                        0  # Force expiry check to fail
                                    )
                                # Force token refresh
                                await self._account.auth.async_get_access_token()
                                logger.info(
                                    "Netatmo access token refreshed in current_data, retrying API call..."
                                )
                                # Retry the API call
                                await asyncio.wait_for(
                                    self._account.async_update_weather_stations(), timeout=10.0
                                )
                                logger.info(
                                    "Netatmo token refreshed successfully in current_data, continuing..."
                                )
                                # Continue processing - don't return empty data yet
                            else:
                                logger.exception(
                                    "Cannot refresh token in current_data - auth object missing"
                                )
                                return {}, time.time()
                        except (RuntimeError, PyatmoApiError) as refresh_error:
                            refresh_msg = str(refresh_error)
                            if (
                                "Invalid refresh token" in refresh_msg
                                or "expired" in refresh_msg.lower()
                            ):
                                logger.exception(
                                    "Netatmo refresh token is invalid or expired in current_data. Please re-authenticate."
                                )
                            else:
                                logger.exception(
                                    f"Netatmo token refresh failed in current_data: {refresh_error}"
                                )
                            return {}, time.time()
                    else:
                        logger.exception("Netatmo API error in current_data:")
                        return {}, time.time()
                except aiohttp.ClientError as e:
                    # Network/HTTP errors
                    error_msg = str(e)
                    if "getaddrinfo" in error_msg or "ClientConnectorDNSError" in type(e).__name__:
                        logger.warning(f"Netatmo DNS error in current_data: {e}")
                    else:
                        logger.exception("Netatmo network error in current_data:")
                    return {}, time.time()
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)
                    # Check for DNS errors
                    if (
                        "getaddrinfo" in error_msg
                        or "ClientConnectorDNSError" in error_type
                        or "DNS" in error_type
                    ):
                        logger.warning(
                            f"Netatmo DNS error in current_data: {error_type}: {error_msg}"
                        )
                    # Check for pyatmo-specific exceptions
                    elif "pyatmo" in error_type.lower() or "netatmo" in error_type.lower():
                        logger.exception(
                            f"Netatmo/pyatmo exception in current_data: {error_type}: {error_msg}"
                        )
                    else:
                        logger.exception("Unexpected error in current_data: {error_type}:")
                    return {}, time.time()

                data = {}
                timestamp = time.time()

                # Find the station by station_id first
                target_home = None
                target_station_module = None

                for home_id, home in self._account.homes.items():
                    for mod_id, module in home.modules.items():
                        # Check if this is the station we're looking for
                        if mod_id == station_id and "NAMain" in str(
                            getattr(module, "device_type", "")
                        ):
                            target_home = home
                            target_station_module = module
                            break
                    if target_station_module:
                        break

                if not target_station_module or not target_home:
                    logger.warning(f"Station {station_id} not found in Netatmo account")
                    return {}, time.time()

                # Now process modules from the correct station/home
                for mod_id, module in target_home.modules.items():
                    # Main indoor module (NAMain) - this is the station itself
                    if mod_id == station_id and "NAMain" in str(getattr(module, "device_type", "")):
                        if module_type in ("indoor", "all"):
                            indoor = {
                                "temperature": getattr(module, "temperature", None),
                                "humidity": getattr(module, "humidity", None),
                                "co2": getattr(module, "co2", None),
                                "noise": getattr(module, "noise", None),
                                "pressure": getattr(module, "pressure", None),
                                "temp_trend": getattr(module, "temp_trend", "stable"),
                                "pressure_trend": getattr(module, "pressure_trend", "stable"),
                            }
                            if module_type == "all":
                                data["indoor"] = indoor
                            else:
                                data = indoor
                            timestamp = getattr(module, "last_seen", time.time())

                    # Outdoor module (NAModule1) - belongs to this station
                    elif "NAModule1" in str(getattr(module, "device_type", "")) and module_type in (
                        "outdoor",
                        "all",
                    ):
                        outdoor = {
                            "temperature": getattr(module, "temperature", None),
                            "humidity": getattr(module, "humidity", None),
                            "temp_trend": getattr(module, "temp_trend", "stable"),
                        }
                        if module_type == "all":
                            data["outdoor"] = outdoor
                        else:
                            data = outdoor

                    # Additional indoor modules (NAModule4) - e.g., Bathroom - belongs to this station
                    elif "NAModule4" in str(getattr(module, "device_type", "")) and module_type in (
                        "indoor_extra",
                        "all",
                    ):
                        module_name = getattr(module, "name", "Extra Indoor Module")
                        extra_indoor = {
                            "name": module_name,
                            "temperature": getattr(module, "temperature", None),
                            "humidity": getattr(module, "humidity", None),
                            "co2": getattr(module, "co2", None),
                            "temp_trend": getattr(module, "temp_trend", "stable"),
                            "battery_percent": getattr(module, "battery_percent", None),
                        }
                        if module_type == "all":
                            # Store additional modules in a list under "extra_indoor"
                            if "extra_indoor" not in data:
                                data["extra_indoor"] = []
                            data["extra_indoor"].append(extra_indoor)
                        else:
                            data = extra_indoor

                if data:
                    self._store_data(station_id, module_type, data, netatmo_timestamp=timestamp)
                    return data, timestamp
                logger.warning(
                    f"No data found for station {station_id} with module_type {module_type}"
                )
                return {}, time.time()

            except Exception as e:
                # This catch-all should not be reached due to specific handlers above,
                # but kept as safety net
                error_type = type(e).__name__
                error_msg = str(e)
                # Check for DNS errors
                if (
                    "getaddrinfo" in error_msg
                    or "ClientConnectorDNSError" in error_type
                    or "DNS" in error_type
                ):
                    logger.warning(
                        f"Netatmo DNS error in current_data (catch-all): {error_type} - returning empty data"
                    )
                elif "TimeoutError" in error_type or "asyncio.TimeoutError" in error_type:
                    logger.warning(
                        "Netatmo data update timed out (catch-all) - returning empty data"
                    )
                elif "pyatmo" in error_type.lower() or "netatmo" in error_type.lower():
                    logger.exception(
                        f"Netatmo/pyatmo exception in current_data (catch-all): {error_type}: {error_msg}"
                    )
                else:
                    logger.exception(
                        f"Unexpected error fetching Netatmo data (catch-all): {error_type}: {error_msg}"
                    )

        # NO simulated data - return empty dict
        logger.warning(
            f"Netatmo API unavailable - returning empty data for {station_id} (no simulated data)"
        )
        return {}, time.time()

    def _get_module_type(self, module: Any) -> str:
        """Determine module type from device_type."""
        device_type = str(getattr(module, "device_type", ""))
        if "NAMain" in device_type:
            return "indoor"
        if "NAModule1" in device_type:
            return "outdoor"
        if "NAModule2" in device_type:
            return "wind"
        if "NAModule3" in device_type:
            return "rain"
        if "NAModule4" in device_type:
            return "indoor_extra"
        return "unknown"

    def _store_data(
        self,
        station_id: str,
        module_type: str,
        data: dict[str, Any],
        netatmo_timestamp: float | None = None,
    ) -> None:
        """Store weather data in the database.

        Args:
            station_id: The station ID
            module_type: Type of module (indoor, outdoor, all)
            data: Weather data to store
            netatmo_timestamp: Unix timestamp from Netatmo (to avoid duplicates)
        """
        try:
            # Use Netatmo's timestamp if provided, otherwise use current time
            if netatmo_timestamp:
                timestamp = datetime.fromtimestamp(netatmo_timestamp, tz=timezone.utc)
                # Check if we already stored data at this timestamp (dedup)
                cache_key = f"last_stored_{station_id}_{module_type}"
                last_stored = getattr(self, "_last_stored_timestamps", {}).get(cache_key, 0)
                if netatmo_timestamp <= last_stored:
                    logger.debug(
                        f"Skipping duplicate data for {station_id}/{module_type} at {netatmo_timestamp}"
                    )
                    return
                # Update cache
                if not hasattr(self, "_last_stored_timestamps"):
                    self._last_stored_timestamps = {}
                self._last_stored_timestamps[cache_key] = netatmo_timestamp
            else:
                timestamp = datetime.now(timezone.utc)

            if module_type in ("indoor", "all"):
                indoor_data = data.get("indoor") if module_type == "all" else data
                if indoor_data:
                    self._db.store_weather_data(
                        station_id=station_id,
                        module_type="indoor",
                        timestamp=timestamp,
                        temperature_c=indoor_data.get("temperature"),
                        humidity_percent=indoor_data.get("humidity"),
                        co2_ppm=indoor_data.get("co2"),
                        pressure_mbar=indoor_data.get("pressure"),
                        noise_db=indoor_data.get("noise"),
                    )

            if module_type in ("outdoor", "all"):
                outdoor_data = data.get("outdoor") if module_type == "all" else data
                if outdoor_data:
                    self._db.store_weather_data(
                        station_id=station_id,
                        module_type="outdoor",
                        timestamp=timestamp,
                        temperature_c=outdoor_data.get("temperature"),
                        humidity_percent=outdoor_data.get("humidity"),
                    )

            # Store extra indoor modules (e.g., Bathroom)
            if module_type == "all" and "extra_indoor" in data:
                for extra_module in data["extra_indoor"]:
                    module_name = extra_module.get("name", "unknown")
                    # Use module name as unique identifier (e.g., "Bathroom")
                    module_id = f"extra_{module_name.lower().replace(' ', '_')}"
                    self._db.store_weather_data(
                        station_id=station_id,
                        module_type=module_id,  # e.g., "extra_bathroom"
                        timestamp=timestamp,
                        temperature_c=extra_module.get("temperature"),
                        humidity_percent=extra_module.get("humidity"),
                        co2_ppm=extra_module.get("co2"),
                    )
        except Exception as e:
            logger.warning(f"Failed to store weather data: {e}")

    async def fetch_historical_data(
        self,
        station_id: str,
        module_id: str | None = None,
        data_type: str = "temperature",
        time_range: str = "7d",
    ) -> list[dict[str, Any]]:
        """Fetch historical data from Netatmo API (up to 2 years).

        Uses direct API call to /api/getmeasure endpoint since weather stations
        don't support pyatmo's async_update_measures (which is for thermostats).

        Args:
            station_id: Station ID (NAMain device ID)
            module_id: Specific module ID (None = main indoor module)
            data_type: Data type (temperature, humidity, co2, pressure, noise)
            time_range: Time range (1d, 7d, 30d, 90d, 1y, 2y)

        Returns:
            List of {timestamp, value} dicts
        """
        await self._ensure_session_valid()
        await self.initialize()

        if not self._use_real_api or not self._account:
            logger.warning("Netatmo API not available for historical data")
            return []

        try:
            import asyncio

            # Parse time range to days
            time_range_days = {
                "1d": 1,
                "7d": 7,
                "30d": 30,
                "90d": 90,
                "1y": 365,
                "2y": 730,
            }.get(time_range, 7)

            # Determine scale based on time range (for reasonable data density)
            # API returns max 1024 points, so adjust scale to fit
            if time_range_days <= 1:
                scale = "30min"  # 48 points/day
            elif time_range_days <= 7:
                scale = "1hour"  # 168 points/week
            elif time_range_days <= 30:
                scale = "1hour"  # 720 points/month (close to limit)
            elif time_range_days <= 90:
                scale = "3hours"  # 720 points/90 days
            else:
                scale = "1day"  # 365 points/year

            # Map data_type to Netatmo API type name
            type_map = {
                "temperature": "Temperature",
                "humidity": "Humidity",
                "co2": "CO2",
                "pressure": "Pressure",
                "noise": "Noise",
            }
            netatmo_type = type_map.get(data_type, "Temperature")

            # Calculate time range
            end_time = int(time.time())
            start_time = end_time - (time_range_days * 86400)

            # Get access token from pyatmo auth
            access_token = None
            if hasattr(self._account, "auth") and hasattr(
                self._account.auth, "async_get_access_token"
            ):
                access_token = await self._account.auth.async_get_access_token()

            if not access_token:
                logger.error("Could not get Netatmo access token")
                return []

            logger.info(
                f"Fetching Netatmo history: device={station_id}, module={module_id or 'main'}, "
                f"type={netatmo_type}, days={time_range_days}, scale={scale}"
            )

            # Make direct API call to getmeasure
            url = "https://api.netatmo.com/api/getmeasure"
            params = {
                "device_id": station_id,
                "scale": scale,
                "type": netatmo_type,
                "date_begin": start_time,
                "date_end": end_time,
                "optimize": "false",
                "real_time": "true",
            }

            # Add module_id if specified (for outdoor sensor, etc.)
            if module_id:
                params["module_id"] = module_id

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Netatmo API error {response.status}: {error_text}")
                        return []

                    data = await response.json()

            # Parse response - format is {"body": {"timestamp1": [value1], "timestamp2": [value2], ...}}
            body = data.get("body", {})
            if not body:
                logger.warning("No data in Netatmo response")
                return []

            result = []
            for ts_str, values in body.items():
                try:
                    ts = int(ts_str)
                    # Values is a list, first element is the requested type
                    value = values[0] if values and values[0] is not None else None
                    if value is not None:
                        result.append(
                            {
                                "timestamp": ts,
                                "value": value,
                            }
                        )
                except (ValueError, IndexError, TypeError) as e:
                    logger.warning(f"Error parsing Netatmo data point: {e}")
                    continue

            # Sort by timestamp
            result.sort(key=lambda x: x["timestamp"])

            logger.info(f"Fetched {len(result)} historical data points from Netatmo")

            # Store in local DB for caching
            stored_count = 0
            for point in result:
                try:
                    ts = datetime.fromtimestamp(point["timestamp"], tz=timezone.utc)
                    # Build kwargs dynamically based on data_type
                    kwargs = {}
                    if data_type == "temperature":
                        kwargs["temperature_c"] = point["value"]
                    elif data_type == "humidity":
                        kwargs["humidity_percent"] = point["value"]
                    elif data_type == "co2":
                        kwargs["co2_ppm"] = int(point["value"])
                    elif data_type == "pressure":
                        kwargs["pressure_mbar"] = point["value"]
                    elif data_type == "noise":
                        kwargs["noise_db"] = point["value"]

                    self._db.store_weather_data(
                        station_id=station_id,
                        module_type=module_id or "indoor",
                        timestamp=ts,
                        **kwargs,
                    )
                    stored_count += 1
                except Exception as e:
                    logger.debug(f"Ignoring storage error for data point: {e}")

            logger.info(f"Stored {stored_count} data points in local DB")
            return result

        except asyncio.TimeoutError:
            logger.exception("Netatmo historical data fetch timed out")
            return []
        except Exception:
            logger.exception("Error fetching Netatmo historical data:")
            return []

    def _get_simulated_stations(self) -> list[dict[str, Any]]:
        """Return empty list - NO simulated data in production."""
        logger.warning("Netatmo API unavailable - returning empty list (no simulated data)")
        return []

    def _get_simulated_data(
        self, station_id: str, module_type: str
    ) -> tuple[dict[str, Any], float]:
        """Return empty data - NO simulated data in production."""
        logger.warning(
            f"Netatmo API unavailable for {station_id} - returning empty data (no simulated data)"
        )
        # Return empty dict - no fake data
        return {}, time.time()
