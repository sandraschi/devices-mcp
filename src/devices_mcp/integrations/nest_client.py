"""
Nest Protect Client - Direct Google Account Authentication

Uses the unofficial Google Home API approach (similar to badnest/Home Assistant)
to get real Nest Protect device data.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class NestProtectStatus(str, Enum):
    """Nest Protect detector status."""

    OK = "ok"
    WARNING = "warning"
    EMERGENCY = "emergency"
    OFFLINE = "offline"


@dataclass
class NestProtectDevice:
    """Nest Protect device data."""

    device_id: str
    name: str
    location: str
    smoke_status: NestProtectStatus
    co_status: NestProtectStatus
    battery_health: str  # "ok", "replace"
    is_online: bool
    last_manual_test: Optional[datetime]
    software_version: str
    model: str  # "Nest Protect" or "Nest Protect (Wired)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "location": self.location,
            "smoke_status": self.smoke_status.value,
            "co_status": self.co_status.value,
            "battery_health": self.battery_health,
            "is_online": self.is_online,
            "last_manual_test": self.last_manual_test.isoformat()
            if self.last_manual_test
            else None,
            "software_version": self.software_version,
            "model": self.model,
        }


class NestClient:
    """
    Client for Nest devices using Google account authentication.

    Uses the same approach as Home Assistant's Nest integration
    and badnest library - authenticates with Google and accesses
    the internal Nest API.
    """

    # Google OAuth endpoints
    NEST_API_URL = "https://home.nest.com"
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    NEST_AUTH_URL = "https://nestauthproxyservice-pa.googleapis.com/v1/issue_jwt"

    # OAuth client ID (public - from Google Home app)
    CLIENT_ID = "733249279899-1gpkq9duqmdp55a7e5lft1pr2smumdla.apps.googleusercontent.com"

    def __init__(
        self,
        refresh_token: Optional[str] = None,
        token_file: str = "nest_token.cache",
        cache_ttl: int = 60,
    ):
        self.refresh_token = refresh_token
        # Adjust token file path for Docker (use mounted volume)
        self.token_file = self._adjust_token_path(token_file)
        self.cache_ttl = cache_ttl

        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._jwt_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._devices: dict[str, NestProtectDevice] = {}
        self._cache_time: Optional[datetime] = None
        self._initialized = False

    @staticmethod
    def _adjust_token_path(token_file: str) -> Path:
        """Adjust token file path for Docker environment."""
        import os

        token_path = Path(token_file)

        # In Docker, use mounted volume for token persistence
        if os.getenv("CONTAINER") == "yes":
            # If token file is in current directory, move to /app/tokens
            if not token_path.is_absolute():
                tokens_dir = Path("/app/tokens")
                tokens_dir.mkdir(parents=True, exist_ok=True)
                return tokens_dir / token_path.name
            # If absolute path, ensure parent directory exists
            token_path.parent.mkdir(parents=True, exist_ok=True)

        return token_path

    async def initialize(self) -> bool:
        """Initialize the Nest client."""
        try:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

            # Try to load cached token
            if self.token_file.exists():
                logger.info("Loading Nest token from cache")
                token_data = json.loads(self.token_file.read_text())
                self.refresh_token = token_data.get("refresh_token")

            if not self.refresh_token:
                logger.warning("No Nest refresh token. Run OAuth flow to authenticate.")
                return False

            # Get access token
            await self._refresh_access_token()
            if not self._access_token:
                return False

            # Get JWT for Nest API
            await self._get_nest_jwt()
            if not self._jwt_token:
                return False

            # Fetch initial device data
            await self._fetch_devices()

            self._initialized = True
            logger.info(f"Nest client initialized with {len(self._devices)} devices")
            return True

        except Exception:
            logger.exception("Failed to initialize Nest client")
            return False

    async def close(self) -> None:
        """Close the client session."""
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def _refresh_access_token(self) -> None:
        """Refresh the Google access token."""
        if not self._session or not self.refresh_token:
            return

        try:
            async with self._session.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "refresh_token": self.refresh_token,
                    "client_id": self.CLIENT_ID,
                    "grant_type": "refresh_token",
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._access_token = data.get("access_token")
                    logger.debug("Google access token refreshed")
                else:
                    text = await response.text()
                    logger.error(f"Failed to refresh token: {response.status} - {text}")
        except Exception:
            logger.exception("Error refreshing access token")

    async def _get_nest_jwt(self) -> None:
        """Get JWT token for Nest API access."""
        if not self._session or not self._access_token:
            return

        try:
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "x-goog-api-key": "AIzaSyAdkSIMNc51XGNEAYWasX9UOWkS5P6sZE4",
            }

            async with self._session.post(
                self.NEST_AUTH_URL,
                headers=headers,
                json={
                    "embed_google_oauth_access_token": True,
                    "expire_after": "3600s",
                    "google_oauth_access_token": self._access_token,
                    "policy_id": "authproxy-oauth-policy",
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._jwt_token = data.get("jwt")
                    logger.debug("Nest JWT obtained")
                else:
                    text = await response.text()
                    logger.error(f"Failed to get Nest JWT: {response.status} - {text}")
        except Exception:
            logger.exception("Error getting Nest JWT")

    async def _fetch_devices(self) -> None:
        """Fetch Nest Protect devices from API."""
        if not self._session or not self._jwt_token:
            return

        try:
            # First, get the user ID and structure
            headers = {
                "Authorization": f"Basic {self._jwt_token}",
                "Content-Type": "application/json",
            }

            # Get app launch data which contains device info
            async with self._session.post(
                f"{self.NEST_API_URL}/api/0.1/user/{self._user_id}/app_launch"
                if self._user_id
                else f"{self.NEST_API_URL}/api/0.1/user/me/app_launch",
                headers=headers,
                json={
                    "known_bucket_types": ["topaz"],  # topaz = Nest Protect
                    "known_bucket_versions": [],
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._user_id = data.get("user_id", self._user_id)
                    await self._parse_devices(data)
                else:
                    text = await response.text()
                    logger.error(f"Failed to fetch devices: {response.status} - {text}")

            self._cache_time = datetime.now()

        except Exception:
            logger.exception("Error fetching Nest devices")

    async def _parse_devices(self, data: dict[str, Any]) -> None:
        """Parse device data from API response."""
        self._devices.clear()

        # Look for topaz (Nest Protect) devices in buckets
        for bucket in data.get("updated_buckets", []):
            if bucket.get("object_key", "").startswith("topaz."):
                device_data = bucket.get("value", {})
                device_id = bucket["object_key"].split(".")[1]

                # Extract relevant fields
                device = NestProtectDevice(
                    device_id=device_id,
                    name=device_data.get("description", f"Protect {device_id[:4]}"),
                    location=device_data.get("where_name", "Unknown"),
                    smoke_status=self._map_status(device_data.get("smoke_status", 0)),
                    co_status=self._map_status(device_data.get("co_status", 0)),
                    battery_health="ok"
                    if device_data.get("battery_health_state", 0) == 0
                    else "replace",
                    is_online=device_data.get("component_wifi_test_passed", False),
                    last_manual_test=self._parse_timestamp(
                        device_data.get("last_manual_test_utc_secs")
                    ),
                    software_version=device_data.get("software_version", "unknown"),
                    model="Nest Protect (Wired)"
                    if device_data.get("line_power_present")
                    else "Nest Protect",
                )
                self._devices[device_id] = device

        logger.info(f"Parsed {len(self._devices)} Nest Protect devices")

    def _map_status(self, status_code: int) -> NestProtectStatus:
        """Map Nest status code to enum."""
        if status_code == 0:
            return NestProtectStatus.OK
        if status_code == 1:
            return NestProtectStatus.WARNING
        if status_code == 2:
            return NestProtectStatus.EMERGENCY
        return NestProtectStatus.OFFLINE

    def _parse_timestamp(self, ts: Optional[int]) -> Optional[datetime]:
        """Parse Unix timestamp to datetime."""
        if ts:
            return datetime.fromtimestamp(ts)
        return None

    async def get_devices(self) -> list[NestProtectDevice]:
        """Get all Nest Protect devices."""
        # Check cache
        if self._cache_time:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age > self.cache_ttl:
                await self._fetch_devices()

        return list(self._devices.values())

    async def get_device(self, device_id: str) -> Optional[NestProtectDevice]:
        """Get a specific device by ID."""
        await self.get_devices()  # Ensure fresh data
        return self._devices.get(device_id)

    async def get_summary(self) -> dict[str, Any]:
        """Get summary of all Nest Protect devices."""
        devices = await self.get_devices()

        smoke_ok = all(d.smoke_status == NestProtectStatus.OK for d in devices)
        co_ok = all(d.co_status == NestProtectStatus.OK for d in devices)
        all_online = all(d.is_online for d in devices)

        return {
            "total_devices": len(devices),
            "online_count": sum(1 for d in devices if d.is_online),
            "smoke_status": "ok" if smoke_ok else "alert",
            "co_status": "ok" if co_ok else "alert",
            "battery_warnings": [d.name for d in devices if d.battery_health != "ok"],
            "all_ok": smoke_ok and co_ok and all_online,
            "devices": [d.to_dict() for d in devices],
        }

    def save_token(self) -> None:
        """Save refresh token to cache file."""
        if self.refresh_token:
            self.token_file.write_text(json.dumps({"refresh_token": self.refresh_token}))

    @classmethod
    def get_oauth_url(cls, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """
        Get OAuth URL for user to authenticate.

        User visits this URL, logs in with Google, and gets a code to exchange.
        """
        import urllib.parse

        params = {
            "client_id": cls.CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/nest-account",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{cls.GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> bool:
        """
        Exchange authorization code for refresh token.

        After user authorizes at OAuth URL, they get a code to paste here.
        """
        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            async with self._session.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.CLIENT_ID,
                    "grant_type": "authorization_code",
                    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.refresh_token = data.get("refresh_token")
                    self._access_token = data.get("access_token")
                    self.save_token()
                    logger.info("Nest OAuth completed successfully")
                    return True
                text = await response.text()
                logger.error(f"OAuth code exchange failed: {text}")
                return False
        except Exception:
            logger.exception("Error exchanging OAuth code")
            return False


# Global client instance
_nest_client: Optional[NestClient] = None


async def init_nest_client(
    refresh_token: Optional[str] = None,
    token_file: str = "nest_token.cache",
    cache_ttl: int = 60,
) -> Optional[NestClient]:
    """Initialize the global Nest client."""
    global _nest_client

    if _nest_client:
        await _nest_client.close()

    _nest_client = NestClient(
        refresh_token=refresh_token,
        token_file=token_file,
        cache_ttl=cache_ttl,
    )

    if await _nest_client.initialize():
        return _nest_client
    return None


def get_nest_client() -> Optional[NestClient]:
    """Get the global Nest client instance."""
    return _nest_client
