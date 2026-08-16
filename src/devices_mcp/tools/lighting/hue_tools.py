"""
Philips Hue Lighting Control Tools for Devices MCP
This module provides MCP tools for controlling Philips Hue lights, groups, and scenes.
"""

import asyncio
import json
import logging
import ssl
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ...config import get_config
from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)
# Hue Bridge Pro (BSB003) and newer bridges require HTTPS on port 443 for the v1 local API.
HUE_HTTPS_MODEL_IDS = frozenset({"BSB003"})


# Repo-local cache (optional): bridge_ip + username when not only in config.yaml
def _hue_repo_root() -> Path:
    # .../src/devices_mcp/tools/lighting/hue_tools.py -> parents[4] = repo root
    return Path(__file__).resolve().parents[4]


def hue_bridge_cache_path() -> Path:
    return _hue_repo_root() / "hue_bridge.cache"


def load_hue_bridge_cache() -> dict[str, Any]:
    p = hue_bridge_cache_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("Could not read hue_bridge.cache")
        return {}


def save_hue_bridge_cache(data: dict[str, Any]) -> None:
    p = hue_bridge_cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved Hue bridge cache to %s", p)


def _hue_api_error(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        err = payload[0].get("error")
        if isinstance(err, dict):
            return err
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        return payload["error"]
    return None


async def probe_hue_bridge(bridge_ip: str) -> dict[str, Any]:
    """Detect bridge model and whether HTTPS is required (Hue Bridge Pro)."""
    import httpx

    ip = bridge_ip.strip()
    result: dict[str, Any] = {
        "bridge_ip": ip,
        "reachable": False,
        "requires_https": False,
        "modelid": None,
        "name": None,
        "apiversion": None,
        "port": 80,
    }
    if not ip:
        result["error"] = "bridge_ip is empty"
        return result
    async with httpx.AsyncClient(verify=False, timeout=12.0) as client:
        try:
            resp = await client.get(f"https://{ip}/api/config")
            if resp.status_code == 200:
                cfg = resp.json()
                if isinstance(cfg, dict):
                    result["reachable"] = True
                    result["requires_https"] = True
                    result["port"] = 443
                    result["modelid"] = cfg.get("modelid")
                    result["name"] = cfg.get("name")
                    result["apiversion"] = cfg.get("apiversion")
                    if cfg.get("modelid") in HUE_HTTPS_MODEL_IDS:
                        result["bridge_type"] = "Hue Bridge Pro"
                    return result
        except Exception as exc:
            result["https_error"] = str(exc)
        try:
            resp = await client.get(f"http://{ip}/api/config")
            if resp.status_code == 200:
                cfg = resp.json()
                if isinstance(cfg, dict):
                    result["reachable"] = True
                    result["requires_https"] = False
                    result["port"] = 80
                    result["modelid"] = cfg.get("modelid")
                    result["name"] = cfg.get("name")
                    result["apiversion"] = cfg.get("apiversion")
                    return result
        except Exception as exc:
            result["http_error"] = str(exc)
    if not result["reachable"]:
        result["error"] = result.get("https_error") or result.get("http_error") or "Bridge not reachable"
    return result


async def validate_hue_username(bridge_ip: str, username: str, bridge: Any | None = None) -> tuple[bool, str | None]:
    """Return (ok, error_message). Detects stale credentials after bridge replacement."""
    if not username:
        return False, "Hue API username missing — pair with the link button."
    if bridge is not None:
        try:
            payload = bridge.request("GET", f"/api/{username}/config")
        except Exception as exc:
            return False, f"Cannot reach Hue Bridge API: {exc}"
    else:
        import httpx

        probe = await probe_hue_bridge(bridge_ip)
        if not probe.get("reachable"):
            return False, probe.get("error") or "Bridge not reachable"
        scheme = "https" if probe.get("requires_https") else "http"
        try:
            async with httpx.AsyncClient(verify=False, timeout=12.0) as client:
                resp = await client.get(f"{scheme}://{bridge_ip}/api/{username}/config")
            payload = resp.json()
        except Exception as exc:
            return False, f"Cannot validate Hue username: {exc}"
    err = _hue_api_error(payload)
    if err:
        if err.get("type") == 1:
            return False, (
                "Hue API username is unauthorized — typical after replacing the bridge. "
                "Press the link button on the new bridge and pair again."
            )
        return False, err.get("description") or str(err)
    if not isinstance(payload, dict):
        return False, "Unexpected Hue bridge response while validating username"
    return True, None


def create_hue_bridge_client(bridge_ip: str, username: str | None, requires_https: bool) -> Any:
    """Create a phue Bridge client using HTTP or HTTPS as required."""
    if not PHUE_AVAILABLE or Bridge is None:
        raise RuntimeError("phue is not installed")
    if requires_https:
        if HueHttpsBridge is None:
            raise RuntimeError("HTTPS Hue bridge support unavailable")
        return HueHttpsBridge(bridge_ip, username=username)
    return Bridge(bridge_ip, username=username)


def _clip_v2_data_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract ``data`` list from a Hue CLIP v2 JSON body."""
    if not isinstance(payload, dict):
        return []
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []
    return [x for x in rows if isinstance(x, dict)]


def _clip_v2_errors_hint(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    errs = payload.get("errors")
    if not isinstance(errs, list) or not errs:
        return None
    first = errs[0] if isinstance(errs[0], dict) else {}
    desc = first.get("description") or first.get("detail")
    return str(desc) if desc else json.dumps(errs)[:500]


def _motion_area_motion_flag(area: dict[str, Any]) -> bool:
    m = area.get("motion")
    if isinstance(m, dict):
        return bool(m.get("motion"))
    return False


def _motion_area_name(area: dict[str, Any]) -> str:
    meta = area.get("metadata")
    if isinstance(meta, dict) and meta.get("name"):
        return str(meta["name"])
    return ""


async def hue_clip_v2_get(
    bridge_ip: str,
    app_key: str,
    resource_path: str,
) -> tuple[int, Any | None, str | None]:
    """GET ``/clip/v2/resource/{resource_path}`` (Signify Hue API v2).
    Uses the v1 local API username as ``hue-application-key``. Tries HTTPS first
    (bridge self-signed cert), then HTTP.
    """
    import httpx

    path = resource_path.strip().lstrip("/")
    urls = (
        f"https://{bridge_ip}/clip/v2/resource/{path}",
        f"http://{bridge_ip}/clip/v2/resource/{path}",
    )
    headers = {
        "hue-application-key": app_key,
        "Accept": "application/json",
    }
    last_err: str | None = None
    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        for url in urls:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    try:
                        return resp.status_code, resp.json(), None
                    except Exception as e:
                        return resp.status_code, None, f"Invalid JSON: {e}"
                last_err = f"HTTP {resp.status_code}: {(resp.text or '')[:240]}"
            except Exception as e:
                last_err = str(e)
    return 0, None, last_err or "CLIP v2 request failed"


# Try to import phue library
try:
    import http.client as httplib

    from phue import Bridge

    PHUE_AVAILABLE = True

    class HueHttpsBridge(Bridge):
        """phue Bridge using HTTPS — required for Hue Bridge Pro (BSB003)."""

        def request(self, mode="GET", address=None, data=None):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connection = httplib.HTTPSConnection(self.ip, port=443, timeout=15, context=ctx)
            try:
                if mode in ("GET", "DELETE"):
                    connection.request(mode, address)
                elif mode in ("PUT", "POST"):
                    connection.request(mode, address, json.dumps(data))
                else:
                    raise ValueError(f"Unsupported HTTP mode: {mode}")
            except TimeoutError as exc:
                error = f"{mode} request to {self.ip}{address} timed out."
                logger.exception(error)
                from phue import PhueRequestTimeout

                raise PhueRequestTimeout(None, error) from exc
            result = connection.getresponse()
            response = result.read()
            connection.close()
            response_text = response.decode("utf-8")
            logger.debug(response_text)
            return json.loads(response_text)
except ImportError:
    PHUE_AVAILABLE = False
    Bridge = None  # type: ignore[assignment, misc]
    HueHttpsBridge = None  # type: ignore[assignment, misc]


class HueLight(BaseModel):
    """Philips Hue light device data model."""

    light_id: str = Field(..., description="Unique light identifier (Hue ID)")
    name: str = Field(..., description="Light name")
    room: str = Field(default="", description="Room/group name")
    model: str = Field(default="", description="Light model")
    manufacturer: str = Field(default="Philips", description="Manufacturer")
    on: bool = Field(..., description="Current power state")
    brightness: int = Field(..., description="Brightness (0-254)")
    brightness_percent: int = Field(..., description="Brightness percentage (0-100)")
    color_mode: str = Field(default="ct", description="Color mode (xy, ct, hs)")
    color_temp: int = Field(default=0, description="Color temperature (mireds)")
    color_temp_kelvin: int = Field(default=0, description="Color temperature (Kelvin)")
    hue: int = Field(default=0, description="Hue (0-65535)")
    saturation: int = Field(..., description="Saturation (0-254)")
    xy: list[float] = Field(default_factory=list, description="XY color coordinates")
    rgb: list[int] = Field(default_factory=list, description="RGB color values (0-255)")
    reachable: bool = Field(..., description="Whether light is reachable")
    last_seen: str = Field(..., description="Last communication timestamp")
    energy_usage: float | None = Field(default=None, description="Power consumption in watts (if available)")


class HueHomeAware(BaseModel):
    """Philips Hue HomeAware motion detection via Zigbee mesh signal monitoring."""

    light_id: str = Field(..., description="Light identifier")
    signal_strength: int = Field(..., description="Current Zigbee signal strength (0-255)")
    signal_quality: str = Field(default="unknown", description="Signal quality assessment")
    last_updated: str = Field(..., description="Last signal measurement timestamp")
    baseline_strength: int | None = Field(None, description="Established baseline signal strength")
    signal_variance: float = Field(default=0.0, description="Signal variance from baseline")
    motion_confidence: float = Field(default=0.0, description="Motion detection confidence (0-1)")
    motion_detected: bool = Field(default=False, description="Active motion detection")
    last_motion_time: str | None = Field(None, description="Timestamp of last detected motion")
    room: str = Field(default="", description="Room/location for motion context")


class HueGroup(BaseModel):
    """Philips Hue group/room data model."""

    group_id: str = Field(..., description="Unique group identifier")
    name: str = Field(..., description="Group/room name")
    type: str = Field(default="Room", description="Group type (Room, Zone, etc.)")
    lights: list[str] = Field(default_factory=list, description="Light IDs in this group")
    on: bool = Field(..., description="Whether any lights in group are on")
    brightness: int = Field(default=0, description="Average brightness")
    reachable_lights: int = Field(default=0, description="Number of reachable lights")


class HueScene(BaseModel):
    """Philips Hue scene data model."""

    scene_id: str = Field(..., description="Unique scene identifier")
    name: str = Field(..., description="Scene name")
    group: str = Field(default="", description="Group/room this scene belongs to")
    lights: list[str] = Field(default_factory=list, description="Light IDs in this scene")
    active: bool = Field(default=False, description="Whether scene is currently active")


class HueManager:
    """Manager for Philips Hue lights, groups, and scenes.
    Uses caching to avoid slow bridge queries on every operation.
    Call rescan() to refresh the cache when needed.
    """

    def __init__(self):
        self.lights: dict[str, HueLight] = {}
        self.groups: dict[str, HueGroup] = {}
        self.scenes: dict[str, HueScene] = {}
        self.homeaware_sensors: dict[str, HueHomeAware] = {}
        self._initialized = False
        self._bridge: Any | None = None
        self._homeaware_enabled = False  # MotionAware: Hue CLIP v2 available
        self._clip_v2_available = False
        self._clip_v2_error: str | None = None
        self._motionaware_last_state: dict[str, bool] = {}
        self._bridge_ip: str | None = None
        self._bridge_username: str | None = None
        self._requires_https = False
        self._bridge_model: str | None = None
        self._bridge_name: str | None = None
        self._connection_error: str | None = None
        self._cache_loaded = False  # Track if we've loaded from bridge at least once
        self._last_scan_time: datetime | None = None

    async def initialize(self) -> bool:
        """Initialize connection to Philips Hue Bridge."""
        try:
            if not PHUE_AVAILABLE:
                self._connection_error = "phue library not installed. Install with: pip install phue"
                logger.warning(self._connection_error)
                return False
            # Load configuration (YAML overrides hue_bridge.cache)
            cfg = get_config() or {}
            hue_cfg = cfg.get("lighting", {}).get("philips_hue", {})
            if hue_cfg.get("enabled") is False:
                self._connection_error = "Philips Hue is disabled in config (lighting.philips_hue.enabled)"
                logger.info(self._connection_error)
                return False
            cache = load_hue_bridge_cache()
            bridge_ip = hue_cfg.get("bridge_ip") or cache.get("bridge_ip")
            bridge_username = hue_cfg.get("username") or cache.get("username")
            if not bridge_ip:
                self._connection_error = (
                    "Hue Bridge IP not set. Use the Lighting page to discover the bridge or "
                    "set lighting.philips_hue.bridge_ip in config.yaml."
                )
                logger.warning(self._connection_error)
                return False
            self._bridge_ip = str(bridge_ip).strip()
            self._bridge_username = str(bridge_username).strip() if bridge_username else None
            probe = await probe_hue_bridge(self._bridge_ip)
            if not probe.get("reachable"):
                self._connection_error = probe.get("error") or f"Cannot reach Hue Bridge at {self._bridge_ip}"
                logger.warning(self._connection_error)
                return False
            self._requires_https = bool(probe.get("requires_https"))
            self._bridge_model = probe.get("modelid")
            self._bridge_name = probe.get("name")
            logger.info(
                "Hue bridge probe: %s model=%s https=%s",
                self._bridge_name or self._bridge_ip,
                self._bridge_model,
                self._requires_https,
            )
            # Connect to bridge
            try:
                if self._bridge_username:
                    self._bridge = create_hue_bridge_client(
                        self._bridge_ip,
                        self._bridge_username,
                        self._requires_https,
                    )
                    valid, auth_err = await validate_hue_username(
                        self._bridge_ip,
                        self._bridge_username,
                        self._bridge,
                    )
                    if not valid:
                        self._connection_error = auth_err
                        logger.warning(self._connection_error)
                        return False
                else:
                    # First-time connection - user needs to press bridge button (or use web UI pairing)
                    self._bridge = create_hue_bridge_client(self._bridge_ip, None, self._requires_https)
                    self._bridge_username = self._bridge.username
                    logger.info("Hue Bridge connected. Username: %s", self._bridge_username)
                    merged = {**cache, "bridge_ip": self._bridge_ip, "username": self._bridge_username}
                    save_hue_bridge_cache(merged)
            except Exception as e:
                self._connection_error = f"Failed to connect to Hue Bridge: {e!s}"
                logger.exception(self._connection_error)
                if "link button not pressed" in str(e).lower():
                    self._connection_error += " - Press the button on your Hue Bridge and try again"
                return False
            save_hue_bridge_cache(
                {
                    **cache,
                    "bridge_ip": self._bridge_ip,
                    "username": self._bridge_username,
                    "requires_https": self._requires_https,
                    "modelid": self._bridge_model,
                    "name": self._bridge_name,
                }
            )
            # Skip initial discovery - do lazy loading instead
            # This makes initialization near-instant instead of 10-30 seconds
            self.lights.clear()
            self.groups.clear()
            self.scenes.clear()
            self._initialized = True
            self._cache_loaded = False  # Will load on first access
            self._last_scan_time = None
            logger.info("Philips Hue bridge connection initialized (lazy loading enabled)")
            await self._probe_clip_v2()
            return True
        except Exception as e:
            logger.exception("Failed to initialize Philips Hue")
            self._connection_error = str(e)
            return False

    async def _probe_clip_v2(self) -> None:
        """Detect Hue API v2 (HTTPS CLIP). MotionAware uses ``convenience_area_motion`` / ``security_area_motion``."""
        self._clip_v2_available = False
        self._clip_v2_error = None
        self._homeaware_enabled = False
        if not self._bridge_ip or not self._bridge_username:
            self._clip_v2_error = "Missing bridge IP or API username"
            return
        code, payload, err = await hue_clip_v2_get(self._bridge_ip, self._bridge_username, "bridge")
        if code != 200 or payload is None:
            self._clip_v2_error = err or "CLIP v2 bridge probe failed"
            logger.info("Hue CLIP v2 not available: %s", self._clip_v2_error)
            return
        eh = _clip_v2_errors_hint(payload)
        if eh:
            self._clip_v2_error = eh
            logger.info("Hue CLIP v2 bridge response noted: %s", eh)
        rows = _clip_v2_data_rows(payload)
        if not rows:
            self._clip_v2_error = self._clip_v2_error or "CLIP v2 returned no bridge resource"
            return
        self._clip_v2_available = True
        self._homeaware_enabled = True
        logger.info("Hue CLIP v2 OK (MotionAware API reachable)")

    async def _fetch_motionaware_area_lists(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
        """Read MotionAware-style motion areas (Signify Hue API v2)."""
        if not self._bridge_ip or not self._bridge_username:
            return [], [], "Bridge not configured"
        conv_err: str | None = None
        sec_err: str | None = None
        conv: list[dict[str, Any]] = []
        sec: list[dict[str, Any]] = []
        c1, p1, e1 = await hue_clip_v2_get(self._bridge_ip, self._bridge_username, "convenience_area_motion")
        if c1 == 200 and p1 is not None:
            conv = _clip_v2_data_rows(p1)
            conv_err = _clip_v2_errors_hint(p1)
        else:
            conv_err = e1 or f"HTTP {c1}"
        c2, p2, e2 = await hue_clip_v2_get(self._bridge_ip, self._bridge_username, "security_area_motion")
        if c2 == 200 and p2 is not None:
            sec = _clip_v2_data_rows(p2)
            sec_err = _clip_v2_errors_hint(p2)
        else:
            sec_err = e2 or f"HTTP {c2}"
        merge_err = conv_err or sec_err
        return conv, sec, merge_err

    async def _discover_devices(self):
        """Discover all Hue lights, groups, and scenes (threaded)."""
        if not self._bridge:
            return
        # phue is SYNCHRONOUS: property access (lights list AND every
        # per-light attribute) performs blocking HTTP requests. Running the
        # whole discovery in a thread keeps the event loop free so wait_for
        # timeouts actually fire (observed 2026-08-16: a 40s rescan that
        # ignored every timeout because the loop was blocked).
        await asyncio.to_thread(self._discover_devices_sync)

    def _discover_devices_sync(self):
        """Synchronous discovery body - runs inside a worker thread."""
        try:
            # Discover lights (handle individual light errors gracefully)
            # Limit processing to essential data for faster startup
            self.lights.clear()
            bridge_lights = self._bridge.lights
            for light in bridge_lights[:50]:  # Limit to first 50 lights for faster discovery
                try:
                    light_data = self._create_light_from_bridge(light)
                    self.lights[light_data.light_id] = light_data
                except Exception as e:
                    logger.debug(f"Failed to process light {getattr(light, 'light_id', 'unknown')}: {e}")
                    # Continue with other lights even if one fails
            # Discover groups
            self.groups.clear()
            try:
                bridge_groups = self._bridge.groups
                for group in bridge_groups:
                    try:
                        group_data = self._create_group_from_bridge(group)
                        self.groups[group_data.group_id] = group_data
                    except Exception as e:
                        logger.warning(f"Failed to process group {getattr(group, 'group_id', 'unknown')}: {e}")
            except Exception as e:
                logger.warning(f"Failed to discover groups: {e}")
            # Discover scenes
            self.scenes.clear()
            try:
                bridge_scenes = self._bridge.scenes
                for scene in bridge_scenes:
                    try:
                        scene_data = self._create_scene_from_bridge(scene)
                        self.scenes[scene_data.scene_id] = scene_data
                    except Exception as e:
                        logger.warning(f"Failed to process scene {getattr(scene, 'scene_id', 'unknown')}: {e}")
            except Exception as e:
                logger.warning(f"Failed to discover scenes: {e}")
            logger.info(
                "Discovered %s lights, %s groups, %s scenes",
                len(self.lights),
                len(self.groups),
                len(self.scenes),
            )
        except Exception:
            logger.exception("Failed to discover Hue devices")
            # Don't raise - return what we have

    def _create_light_from_bridge(self, light: Any) -> HueLight:
        """Create HueLight from phue Light object.
        Note: phue raises exceptions when accessing properties that don't exist
        for certain light types (e.g., colormode on white-only bulbs). We wrap
        all property accesses in try/except to handle this gracefully.
        """
        # Get brightness safely
        brightness = 0
        try:
            brightness = light.brightness
        except Exception as e:
            logger.debug(f"Could not get brightness for light {light.name}: {e}")
        brightness_percent = int((brightness / 254) * 100) if brightness > 0 else 0
        # Get color temperature safely (not all lights support this)
        color_temp = 0
        color_temp_mireds = 0
        try:
            color_temp = light.colortemp_k
        except Exception as e:
            logger.debug(f"Could not get color temp K for light {light.name}: {e}")
        try:
            color_temp_mireds = light.colortemp
        except Exception as e:
            logger.debug(f"Could not get color temp mireds for light {light.name}: {e}")
        # Get XY color coordinates safely (color bulbs only)
        xy = []
        rgb = []
        try:
            xy_value = light.xy
            if xy_value:
                xy = list(xy_value) if isinstance(xy_value, (list, tuple)) else []
                # Convert XY to RGB for display
                rgb = self._xy_to_rgb(xy[0], xy[1], brightness) if len(xy) >= 2 else [255, 255, 255]
        except Exception as e:
            logger.debug(f"Could not get XY color for light {light.name}: {e}")
        # Get hue and saturation safely (color bulbs only)
        hue = 0
        saturation = 0
        try:
            hue = light.hue
        except Exception as e:
            logger.debug(f"Could not get hue for light {light.name}: {e}")
        try:
            saturation = light.saturation
        except Exception:
            pass
        # Get color mode safely - determines if bulb is color-capable
        # Possible values: 'xy', 'ct' (color temp), 'hs' (hue/sat), or None for white-only
        color_mode = "none"  # Default for white-only bulbs
        try:
            color_mode = light.colormode or "none"
        except Exception:
            pass  # White-only bulbs don't have colormode
        # Get model info safely
        model = "Unknown"
        manufacturer = "Philips"
        try:
            model = light.modelid or "Unknown"
        except Exception:
            pass
        try:
            manufacturer = light.manufacturername or "Philips"
        except Exception:
            pass
        # Get reachable status safely
        reachable = True
        try:
            reachable = light.reachable
        except Exception:
            pass
        return HueLight(
            light_id=str(light.light_id),
            name=light.name,
            room="",  # Will be populated from groups
            model=model,
            manufacturer=manufacturer,
            on=light.on,
            brightness=brightness,
            brightness_percent=brightness_percent,
            color_mode=color_mode,
            color_temp=color_temp_mireds,
            color_temp_kelvin=color_temp,
            hue=hue,
            saturation=saturation,
            xy=xy,
            rgb=rgb,
            reachable=reachable,
            last_seen=datetime.now().isoformat(),
            energy_usage=None,  # Hue API doesn't provide energy data directly
        )

    def _create_group_from_bridge(self, group: Any) -> HueGroup:
        """Create HueGroup from phue Group object.
        Note: phue raises exceptions when accessing certain properties,
        so we wrap all accesses in try/except.
        """
        # Get light IDs safely
        light_ids = []
        try:
            light_ids = [str(lid) for lid in group.lights]
        except Exception:
            pass
        # Calculate group state from individual lights
        on = False
        total_brightness = 0
        reachable_count = 0
        for light_id in light_ids:
            if light_id in self.lights:
                light = self.lights[light_id]
                if light.on:
                    on = True
                    total_brightness += light.brightness
                if light.reachable:
                    reachable_count += 1
        avg_brightness = int(total_brightness / len(light_ids)) if light_ids else 0
        # Get group name safely
        name = "Unknown"
        try:
            name = group.name or "Unknown"
        except Exception:
            pass
        # Get group type safely - phue raises exception if not available
        group_type = "Room"
        try:
            group_type = group.type or "Room"
        except Exception:
            pass  # Default to "Room" if type property not accessible
        return HueGroup(
            group_id=str(group.group_id),
            name=name,
            type=group_type,
            lights=light_ids,
            on=on,
            brightness=avg_brightness,
            reachable_lights=reachable_count,
        )

    def _create_scene_from_bridge(self, scene: Any) -> HueScene:
        """Create HueScene from phue Scene object."""
        light_ids = [str(lid) for lid in scene.lights] if hasattr(scene, "lights") else []
        return HueScene(
            scene_id=scene.scene_id,
            name=scene.name,
            group=getattr(scene, "group", ""),
            lights=light_ids,
            active=False,  # Would need to check current state
        )

    async def monitor_homeaware_motion(self) -> list[dict[str, Any]]:
        """
        Poll MotionAware motion areas via Hue CLIP v2 (Signify ``convenience_area_motion`` /
        ``security_area_motion``).
        Emits events on false-to-true motion edges per area (same poll interval as caller).
        """
        if not self._initialized:
            await self.initialize()
        if not self._clip_v2_available:
            return []
        motion_events: list[dict[str, Any]] = []
        try:
            conv, sec, _err = await self._fetch_motionaware_area_lists()
            grouped = (
                ("convenience_area_motion", conv),
                ("security_area_motion", sec),
            )
            for kind, areas in grouped:
                for area in areas:
                    aid = str(area.get("id") or "")
                    if not aid:
                        continue
                    key = f"{kind}:{aid}"
                    motion = _motion_area_motion_flag(area)
                    prev = self._motionaware_last_state.get(key, False)
                    self._motionaware_last_state[key] = motion
                    if motion and not prev:
                        name = _motion_area_name(area)
                        motion_events.append(
                            {
                                "area_kind": kind,
                                "area_id": aid,
                                "name": name or aid,
                                "motion": True,
                                "enabled": bool(area.get("enabled", True)),
                                "api": "hue_clip_v2",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
        except Exception as e:
            logger.warning("MotionAware poll failed: %s", e)
        return motion_events

    async def get_homeaware_status(self) -> dict[str, Any]:
        """MotionAware status from Signify Hue API v2 (motion areas configured in the Hue app)."""
        if not self._initialized:
            await self.initialize()
        base: dict[str, Any] = {
            "feature": "MotionAware",
            "api": "hue_clip_v2",
            "clip_v2_available": self._clip_v2_available,
            "clip_v2_error": self._clip_v2_error,
        }
        if not self._bridge_ip or not self._bridge_username:
            return {**base, "enabled": False, "reason": "Bridge not configured"}
        if not self._clip_v2_available:
            return {
                **base,
                "enabled": False,
                "reason": self._clip_v2_error or "Hue CLIP v2 not available",
            }
        conv, sec, err = await self._fetch_motionaware_area_lists()
        conv_areas = [
            {
                "id": a.get("id"),
                "name": _motion_area_name(a) or a.get("id"),
                "enabled": a.get("enabled"),
                "motion": _motion_area_motion_flag(a),
            }
            for a in conv
        ]
        sec_areas = [
            {
                "id": a.get("id"),
                "name": _motion_area_name(a) or a.get("id"),
                "enabled": a.get("enabled"),
                "motion": _motion_area_motion_flag(a),
            }
            for a in sec
        ]
        with_motion = sum(1 for a in conv_areas if a.get("motion")) + sum(1 for a in sec_areas if a.get("motion"))
        return {
            **base,
            "enabled": True,
            "convenience_area_motions": conv_areas,
            "security_area_motions": sec_areas,
            "areas_reporting_motion": with_motion,
            "fetch_hint": err,
        }

    async def get_all_lights(self) -> list[HueLight]:
        """Get all discovered lights (from cache, with auto-rescan if stale)."""
        if not self._initialized:
            await self.initialize()
        # Auto-rescan if cache is older than 30 minutes OR if we have no cache at all
        # Removed the flawed "all lights off" logic that caused constant rescanning
        now = datetime.now()
        cache_age_minutes = (now - self._last_scan_time).total_seconds() / 60 if self._last_scan_time else float("inf")
        if not self.lights or cache_age_minutes > 10:
            logger.info(f"Cache is stale (age: {cache_age_minutes:.1f} minutes), rescanning...")
            await self.rescan()
        return list(self.lights.values())

    async def get_light(self, light_id: str) -> HueLight | None:
        """Get a specific light by ID (from cache, fast)."""
        if not self._initialized:
            await self.initialize()
        return self.lights.get(light_id)

    def _get_light_by_id(self, light_id: int):
        """Get a light object by ID (phue doesn't have lights_by_id)."""
        for light in self._bridge.lights:
            if light.light_id == light_id:
                return light
        return None

    def _xy_to_rgb(self, x: float, y: float, brightness: int = 254) -> list[int]:
        """Convert CIE 1931 XY color space to RGB for Hue lights.
        Converts XY coordinates back to RGB for display purposes.
        Uses sRGB color space with D65 white point.
        """
        try:
            # Normalize brightness (0-254 to 0-1)
            brightness_norm = brightness / 254.0 if brightness > 0 else 1.0
            # Convert xy to XYZ (using Y as brightness)
            # We need to reconstruct Z from x, y, and Y
            # x = X / (X + Y + Z), y = Y / (X + Y + Z)
            # If we set Y = brightness_norm, we can solve for X and Z
            if y == 0:
                return [255, 255, 255]  # Avoid division by zero
            Y = brightness_norm
            X = (x / y) * Y
            Z = ((1 - x - y) / y) * Y
            # Convert XYZ to linear RGB (inverse of sRGB to XYZ matrix)
            r_linear = X * 3.2404542 + Y * -1.5371385 + Z * -0.4985314
            g_linear = X * -0.9692660 + Y * 1.8760108 + Z * 0.0415560
            b_linear = X * 0.0556434 + Y * -0.2040259 + Z * 1.0572252

            # Apply inverse gamma correction (sRGB)
            def inv_gamma_correct(val):
                if val > 0.0031308:
                    return 1.055 * (val ** (1.0 / 2.4)) - 0.055
                return 12.92 * val

            r_norm = max(0.0, min(1.0, inv_gamma_correct(r_linear)))
            g_norm = max(0.0, min(1.0, inv_gamma_correct(g_linear)))
            b_norm = max(0.0, min(1.0, inv_gamma_correct(b_linear)))
            # Convert to 0-255 RGB
            r = round(r_norm * 255)
            g = round(g_norm * 255)
            b = round(b_norm * 255)
            return [r, g, b]
        except Exception:
            logger.exception("Failed to convert XY to RGB")
            return [255, 255, 255]  # Default to white on error

    def _rgb_to_xy(self, r: int, g: int, b: int) -> list[float] | None:
        """Convert RGB (0-255) to CIE 1931 XY color space for Hue lights.
        Based on Philips Hue API specification for RGB to XY conversion.
        Uses sRGB color space with D65 white point.
        """
        try:
            # Normalize RGB values to 0-1
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0

            # Apply gamma correction (sRGB gamma)
            def gamma_correct(val):
                if val > 0.04045:
                    return ((val + 0.055) / 1.055) ** 2.4
                return val / 12.92

            r_gamma = gamma_correct(r_norm)
            g_gamma = gamma_correct(g_norm)
            b_gamma = gamma_correct(b_norm)
            # Convert to XYZ color space (sRGB to XYZ matrix, D65 white point)
            x = r_gamma * 0.4124564 + g_gamma * 0.3575761 + b_gamma * 0.1804375
            y = r_gamma * 0.2126729 + g_gamma * 0.7151522 + b_gamma * 0.0721750
            z = r_gamma * 0.0193339 + g_gamma * 0.1191920 + b_gamma * 0.9503041
            # Convert XYZ to xy (chromaticity coordinates)
            total = x + y + z
            if total == 0:
                return None
            x_xy = x / total
            y_xy = y / total
            # Hue lights use a specific color gamut (most use Gamut B)
            # Clamp to valid range for Hue lights (approximate)
            x_xy = max(0.0, min(1.0, x_xy))
            y_xy = max(0.0, min(1.0, y_xy))
            return [round(x_xy, 4), round(y_xy, 4)]
        except Exception:
            logger.exception("Failed to convert RGB to XY")
            return None

    def _get_group_by_id(self, group_id: int):
        """Get a group object by ID (phue doesn't have groups_by_id)."""
        for group in self._bridge.groups:
            if group.group_id == group_id:
                return group
        return None

    async def set_light_state(
        self,
        light_id: str,
        on: bool | None = None,
        brightness: int | None = None,
        brightness_percent: int | None = None,
        color_temp: int | None = None,
        hue: int | None = None,
        saturation: int | None = None,
        rgb: list[int] | None = None,
    ) -> bool:
        """Set light state."""
        if not self._bridge:
            raise RuntimeError("Hue Bridge not connected")
        try:
            light = self._get_light_by_id(int(light_id))
            if not light:
                raise ValueError(f"Light {light_id} not found")
            # Set power state
            if on is not None:
                light.on = on
            # Set brightness (accept both 0-254 and 0-100)
            if brightness is not None:
                light.brightness = max(0, min(254, brightness))
            elif brightness_percent is not None:
                light.brightness = int((brightness_percent / 100) * 254)
            # Set color temperature (mireds)
            if color_temp is not None:
                light.colortemp_k = color_temp
            # Set hue and saturation
            if hue is not None:
                light.hue = hue
            if saturation is not None:
                light.saturation = saturation
            # Set RGB (convert to XY)
            if rgb and len(rgb) == 3:
                # Convert RGB to XY color space (CIE 1931)
                # This is the color space that Hue lights use
                xy = self._rgb_to_xy(rgb[0], rgb[1], rgb[2])
                if xy:
                    light.xy = xy
                    # Also set colormode to 'xy' for color bulbs
                    try:
                        light.colormode = "xy"
                    except Exception:
                        pass  # Some lights may not support setting colormode
            # Update local cache instead of re-querying entire bridge
            # The phue library sends the command directly, we just update our cache
            if light_id in self.lights:
                if on is not None:
                    self.lights[light_id].on = on
                if brightness is not None:
                    self.lights[light_id].brightness = brightness
                    self.lights[light_id].brightness_percent = int((brightness / 254) * 100)
                elif brightness_percent is not None:
                    self.lights[light_id].brightness = int((brightness_percent / 100) * 254)
                    self.lights[light_id].brightness_percent = brightness_percent
                if hue is not None:
                    self.lights[light_id].hue = hue
                if saturation is not None:
                    self.lights[light_id].saturation = saturation
                if rgb and len(rgb) == 3:
                    self.lights[light_id].rgb = rgb
                    # Update XY coordinates in cache
                    xy = self._rgb_to_xy(rgb[0], rgb[1], rgb[2])
                    if xy:
                        self.lights[light_id].xy = xy
                        self.lights[light_id].color_mode = "xy"
            return True
        except Exception:
            logger.exception(f"Failed to set light {light_id} state")
            raise

    async def get_all_groups(self) -> list[HueGroup]:
        """Get all groups/rooms (from cache, with auto-rescan if stale)."""
        if not self._initialized:
            await self.initialize()
        # Use same time-based staleness check as lights
        now = datetime.now()
        cache_age_minutes = (now - self._last_scan_time).total_seconds() / 60 if self._last_scan_time else float("inf")
        if not self.groups or cache_age_minutes > 10:
            logger.info(f"Groups cache is stale (age: {cache_age_minutes:.1f} minutes), rescanning...")
            await self.rescan()
        return list(self.groups.values())

    async def get_all_scenes(self) -> list[HueScene]:
        """Get all scenes (from cache, with auto-rescan if stale)."""
        if not self._initialized:
            await self.initialize()
        # Use same time-based staleness check as lights/groups
        now = datetime.now()
        cache_age_minutes = (now - self._last_scan_time).total_seconds() / 60 if self._last_scan_time else float("inf")
        if not self.scenes or cache_age_minutes > 10:
            logger.info(f"Scenes cache is stale (age: {cache_age_minutes:.1f} minutes), rescanning...")
            await self.rescan()
        return list(self.scenes.values())

    async def rescan(self) -> dict[str, int]:
        """Manually rescan all devices from bridge. Use when devices change."""
        # Try to initialize if not already done
        if not self._initialized:
            init_success = await self.initialize()
            if not init_success:
                error_msg = self._connection_error or "Hue Bridge not connected"
                raise RuntimeError(error_msg)
        if not self._bridge:
            error_msg = self._connection_error or "Hue Bridge not connected"
            raise RuntimeError(error_msg)
        # Add timeout protection to prevent hanging. The discovery is now
        # threaded, so this bound is real (previously phue's sync calls
        # blocked the loop and ignored every timeout). 60s: per-attribute
        # phue discovery on a large bridge legitimately takes 30-40s.
        try:
            import asyncio

            await asyncio.wait_for(self._discover_devices(), timeout=60.0)  # 60 second timeout for rescans
        except TimeoutError:
            logger.warning("Hue bridge rescan timed out after 15 seconds")
            raise RuntimeError("Hue bridge rescan timed out - bridge may be unresponsive") from None
        except Exception:
            logger.exception("Hue bridge rescan failed")
            raise
        self._last_scan_time = datetime.now()
        self._cache_loaded = True
        await self._probe_clip_v2()
        return {
            "lights": len(self.lights),
            "groups": len(self.groups),
            "scenes": len(self.scenes),
            "scanned_at": self._last_scan_time.isoformat() if self._last_scan_time else None,
        }

    async def set_group_state(
        self,
        group_id: str,
        on: bool | None = None,
        brightness: int | None = None,
    ) -> bool:
        """Set group/room state."""
        if not self._bridge:
            raise RuntimeError("Hue Bridge not connected")
        try:
            group = self._get_group_by_id(int(group_id))
            if not group:
                raise ValueError(f"Group {group_id} not found")
            if on is not None:
                group.on = on
            if brightness is not None:
                brightness_val = max(0, min(254, brightness))
                group.brightness = brightness_val
            # Update local cache instead of re-querying entire bridge
            if group_id in self.groups:
                if on is not None:
                    self.groups[group_id].on = on
                if brightness is not None:
                    self.groups[group_id].brightness = brightness
            return True
        except Exception:
            logger.exception(f"Failed to set group {group_id} state")
            raise

    async def activate_scene(self, scene_id: str, group_id: str | None = None) -> bool:
        """Activate a scene."""
        if not self._bridge:
            raise RuntimeError("Hue Bridge not connected")
        try:
            # Find scene by iterating through scenes
            scene = None
            for s in self._bridge.scenes:
                if s.scene_id == scene_id:
                    scene = s
                    break
            if not scene:
                raise ValueError(f"Scene {scene_id} not found")
            # Determine which group to use
            target_group_id = None
            if group_id:
                target_group_id = int(group_id)
            else:
                # Get scene's associated group
                scene_group = getattr(scene, "group", None)
                if scene_group:
                    target_group_id = int(scene_group)
                # If scene has no group, find a group that contains the scene's lights
                elif hasattr(scene, "lights") and scene.lights:
                    scene_light_ids = set(str(lid) for lid in scene.lights)
                    for grp in self._bridge.groups:
                        if grp.group_id != 0:  # Skip group 0 (all lights)
                            try:
                                group_light_ids = set(str(lid) for lid in grp.lights)
                            except Exception:
                                continue
                            if scene_light_ids.intersection(group_light_ids):
                                target_group_id = grp.group_id
                                break
            if target_group_id is None:
                raise ValueError(f"Could not determine group for scene {scene_id}")
            # Activate scene using the bridge's set_group method
            # The phue Group object's .scene property doesn't work for activation
            # Must use bridge.set_group(group_id, 'scene', scene_id)
            self._bridge.set_group(target_group_id, "scene", scene_id)
            logger.info(f"Activated scene {scene_id} on group {target_group_id}")
            return True
        except Exception:
            logger.exception("Failed to activate scene")
            raise


# Global manager instance
# Global Hue manager instance (lazy initialization)
_hue_manager_instance: HueManager | None = None


def get_hue_manager() -> HueManager:
    """Get the global Hue manager instance (lazy initialization)."""
    global _hue_manager_instance
    if _hue_manager_instance is None:
        _hue_manager_instance = HueManager()
    return _hue_manager_instance


def reset_hue_manager() -> None:
    """Recreate the Hue manager (reload bridge_ip/username from config and hue_bridge.cache)."""
    global _hue_manager_instance, hue_manager
    _hue_manager_instance = None
    hue_manager = get_hue_manager()


# For backward compatibility - initialize immediately since it's a singleton
hue_manager = get_hue_manager()


async def discover_hue_bridges_cloud() -> list[dict[str, Any]]:
    """Return bridges from Philips discovery service (requires outbound HTTPS)."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get("https://discovery.meethue.com/")
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []
        out: list[dict[str, Any]] = []
        for b in data:
            if not isinstance(b, dict):
                continue
            ip = b.get("internalipaddress")
            if not ip:
                continue
            out.append(
                {
                    "bridge_id": b.get("id"),
                    "internalipaddress": ip,
                    "macaddress": b.get("macaddress"),
                    "name": b.get("name") or "Hue Bridge",
                    "port": b.get("port") or 443,
                    "requires_https": bool(b.get("port") == 443),
                }
            )
        return out
    except Exception as e:
        logger.warning("Hue cloud discovery failed: %s", e)
        return []


async def pair_philips_hue_bridge(bridge_ip: str) -> dict[str, Any]:
    """Create a local API user on the bridge (link button must be pressed). Saves hue_bridge.cache."""
    import httpx

    cfg = get_config() or {}
    hue_cfg = (cfg.get("lighting") or {}).get("philips_hue") or {}
    if hue_cfg.get("enabled") is False:
        return {
            "success": False,
            "message": "Philips Hue is disabled in config (lighting.philips_hue.enabled).",
            "error": "Philips Hue is disabled in config (lighting.philips_hue.enabled).",
        }
    ip = bridge_ip.strip()
    if not ip:
        return {"success": False, "message": "bridge_ip is required", "error": "bridge_ip is required"}
    probe = await probe_hue_bridge(ip)
    if not probe.get("reachable"):
        msg = probe.get("error") or f"Cannot reach bridge at {ip}"
        return {"success": False, "message": msg, "error": msg}
    scheme = "https" if probe.get("requires_https") else "http"
    url = f"{scheme}://{ip}/api"
    payload = {"devicetype": "devices-mcp#web"}
    try:
        async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
            resp = await client.post(url, json=payload)
    except Exception as e:
        return {
            "success": False,
            "message": f"Cannot reach bridge at {ip}: {e}",
            "error": f"Cannot reach bridge at {ip}: {e}",
        }
    try:
        data = resp.json()
    except Exception:
        return {
            "success": False,
            "message": f"Invalid response (HTTP {resp.status_code})",
            "error": f"Invalid response (HTTP {resp.status_code})",
        }
    if not isinstance(data, list):
        return {"success": False, "message": "Unexpected bridge response", "error": "Unexpected bridge response"}
    username: str | None = None
    for item in data:
        if not isinstance(item, dict):
            continue
        if "error" in item:
            err = item["error"]
            typ = err.get("type")
            desc = err.get("description", "")
            if typ == 101:
                return {
                    "success": False,
                    "message": "Link button not pressed on the bridge",
                    "error": "Link button not pressed on the bridge",
                    "needs_button": True,
                    "hint": (
                        "On the Hue Bridge v2 (white box), press the large round button on the front once, "
                        "then tap Pair again within about 30 seconds. The phone app does not replace this step."
                    ),
                }
            return {"success": False, "message": desc or str(err), "error": desc or str(err)}
        if "success" in item:
            su = item["success"]
            if isinstance(su, dict) and su.get("username"):
                username = str(su["username"])
    if not username:
        return {
            "success": False,
            "message": "No username in bridge response",
            "error": "No username in bridge response",
        }
    cache = load_hue_bridge_cache()
    cache["bridge_ip"] = ip
    cache["username"] = username
    cache["requires_https"] = probe.get("requires_https", False)
    cache["modelid"] = probe.get("modelid")
    cache["name"] = probe.get("name")
    save_hue_bridge_cache(cache)
    reset_hue_manager()
    mgr = get_hue_manager()
    ok = await mgr.initialize()
    if not ok:
        return {
            "success": False,
            "message": mgr._connection_error or "Initialization failed after pairing",
            "error": mgr._connection_error or "Initialization failed after pairing",
            "username_saved": True,
        }
    return {
        "success": True,
        "bridge_ip": ip,
        "username": username,
        "message": "Hue Bridge paired. Your lights should appear after refresh.",
    }


# MCP Tools
@tool(
    category=ToolCategory.LIGHTING,
    description="Get status of all Philips Hue lights",
)
class GetHueLightsTool(BaseTool):
    """Get all Philips Hue lights."""

    async def run(self) -> dict[str, Any]:
        """Get all lights."""
        lights = await hue_manager.get_all_lights()
        return {
            "lights": [light.model_dump() for light in lights],
            "count": len(lights),
        }


@tool(
    category=ToolCategory.LIGHTING,
    description="Control a Philips Hue light (on/off, brightness, color)",
)
class ControlHueLightTool(BaseTool):
    """Control a Philips Hue light."""

    light_id: str = Field(..., description="Light ID")
    on: bool | None = Field(None, description="Turn light on/off")
    brightness_percent: int | None = Field(None, description="Brightness (0-100)")
    color_temp_kelvin: int | None = Field(None, description="Color temperature in Kelvin")

    async def run(self) -> dict[str, Any]:
        """Control light."""
        success = await hue_manager.set_light_state(
            self.light_id,
            on=self.on,
            brightness_percent=self.brightness_percent,
            color_temp=self.color_temp_kelvin,
        )
        light = await hue_manager.get_light(self.light_id)
        return {
            "success": success,
            "light": light.model_dump() if light else None,
        }


@tool(
    category=ToolCategory.LIGHTING,
    description="Get all Philips Hue groups/rooms",
)
class GetHueGroupsTool(BaseTool):
    """Get all Hue groups/rooms."""

    async def run(self) -> dict[str, Any]:
        """Get all groups."""
        groups = await hue_manager.get_all_groups()
        return {
            "groups": [group.model_dump() for group in groups],
            "count": len(groups),
        }


@tool(
    category=ToolCategory.LIGHTING,
    description="Control a Philips Hue group/room (all lights in room)",
)
class ControlHueGroupTool(BaseTool):
    """Control a Hue group/room."""

    group_id: str = Field(..., description="Group ID")
    on: bool | None = Field(None, description="Turn all lights in group on/off")
    brightness: int | None = Field(None, description="Brightness (0-254)")

    async def run(self) -> dict[str, Any]:
        """Control group."""
        success = await hue_manager.set_group_state(
            self.group_id,
            on=self.on,
            brightness=self.brightness,
        )
        return {"success": success}


@tool()
class GetHomeAwareStatus(BaseTool):
    """Get MotionAware motion area status (Hue CLIP v2; Bridge Pro)."""

    def __init__(self):
        super().__init__(
            category=ToolCategory.LIGHTING,
            description="Get MotionAware motion areas from Signify Hue API v2 (convenience_area_motion / security_area_motion)",
        )

    async def run(self) -> dict[str, Any]:
        """Return MotionAware motion area state (CLIP v2)."""
        try:
            status = await hue_manager.get_homeaware_status()
            return {"success": True, "motionaware": status, "homeaware": status}
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get MotionAware status: {e}",
                "error": f"Failed to get MotionAware status: {e}",
            }


@tool()
class MonitorHomeAwareMotion(BaseTool):
    """Poll MotionAware areas for new motion edges (Hue CLIP v2)."""

    def __init__(self):
        super().__init__(
            category=ToolCategory.LIGHTING,
            description="Poll MotionAware motion areas (false-to-true motion edges per area)",
        )

    async def run(self) -> dict[str, Any]:
        """Poll MotionAware motion areas (CLIP v2)."""
        try:
            motion_events = await hue_manager.monitor_homeaware_motion()
            if motion_events:
                return {
                    "success": True,
                    "motion_detected": True,
                    "events": motion_events,
                    "message": f"Motion edge in {len(motion_events)} MotionAware area(s)",
                }
            return {
                "success": True,
                "motion_detected": False,
                "events": [],
                "message": "No new motion edges",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to monitor motion: {e}",
                "error": f"Failed to monitor motion: {e}",
            }
