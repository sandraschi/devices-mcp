"""
Tapo Lighting Control Tools for Devices MCP
This module provides MCP tools for controlling Tapo smart lighting devices
like L900 lightstrips with color control, brightness, and effects.
"""

import concurrent.futures
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ...config import get_config
from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)
# Try to import pytapo library
try:
    from pytapo import Tapo

    PYTAPO_AVAILABLE = True
except ImportError:
    PYTAPO_AVAILABLE = False
    Tapo = None  # type: ignore[assignment, misc]


class TapoLight(BaseModel):
    """Tapo smart light device data model."""

    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Device name")
    location: str = Field(..., description="Device location")
    model: str = Field(default="Tapo Light", description="Device model")
    manufacturer: str = Field(default="TP-Link", description="Manufacturer")
    on: bool = Field(..., description="Current power state")
    brightness: int = Field(..., description="Brightness (0-100)")
    color_temp: int = Field(default=0, description="Color temperature (Kelvin)")
    hue: int = Field(default=0, description="Hue (0-360)")
    saturation: int = Field(default=0, description="Saturation (0-100)")
    rgb: list[int] = Field(default_factory=lambda: [255, 255, 255], description="RGB color values (0-255)")
    effect: str = Field(default="", description="Current light effect/mode")
    reachable: bool = Field(..., description="Whether device is reachable")
    last_seen: str = Field(..., description="Last communication timestamp")


class TapoLightingManager:
    """Manager for Tapo smart lighting devices."""

    def __init__(self):
        self.devices: dict[str, TapoLight] = {}
        self._initialized = False
        self._device_hosts: dict[str, str] = {}
        self._device_readonly: dict[str, bool] = {}
        self._connection_error: str | None = None
        self._last_scan_time: datetime | None = None
        self._account_email: str | None = None
        self._account_password: str | None = None

    async def initialize(self) -> bool:
        """Initialize connection to Tapo lighting devices."""
        try:
            if not PYTAPO_AVAILABLE:
                self._connection_error = "pytapo library not installed. Install with: pip install pytapo"
                logger.warning(self._connection_error)
                return False
            # Load configuration
            # Load config from project directory, not user directory
            import os

            # Go up from src/devices_mcp/tools/lighting/ to project root
            project_config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
                "config.yaml",
            )
            if os.path.exists(project_config_path):
                import yaml

                with open(project_config_path) as f:
                    cfg = yaml.safe_load(f) or {}
                logger.info(f"Loaded config from project path: {project_config_path}")
            else:
                cfg = get_config() or {}
                logger.warning(f"Project config not found at {project_config_path}, using default config")
            lighting_cfg = cfg.get("lighting", {}).get("tapo_lighting", {})
            if not lighting_cfg:
                self._connection_error = "No Tapo lighting configuration found"
                logger.warning(self._connection_error)
                return False
            # Get account credentials
            account_cfg = lighting_cfg.get("account", {})
            self._account_email = account_cfg.get("email")
            self._account_password = account_cfg.get("password")
            if not self._account_email or not self._account_password:
                self._connection_error = "Tapo lighting account credentials not configured"
                logger.warning(self._connection_error)
                return False
            # Load device configurations
            devices_cfg = lighting_cfg.get("devices", [])
            for device_cfg in devices_cfg:
                device_id = device_cfg.get("device_id")
                host = device_cfg.get("host")
                name = device_cfg.get("name", f"Tapo Light {device_id}")
                location = device_cfg.get("location", "")
                readonly = device_cfg.get("readonly", False)
                if device_id and host:
                    self._device_hosts[device_id] = host
                    self._device_readonly[device_id] = readonly
                    # Initialize device with basic info
                    device = TapoLight(
                        device_id=device_id,
                        name=name,
                        location=location,
                        on=False,
                        brightness=50,
                        reachable=False,
                        last_seen=datetime.now().isoformat(),
                    )
                    self.devices[device_id] = device
                    logger.info(f"Configured Tapo light: {name} ({device_id}) at {host}")
            self._initialized = True
            logger.info(f"Tapo lighting initialized with {len(self.devices)} devices")
            return True
        except Exception as e:
            self._connection_error = f"Failed to initialize Tapo lighting: {e}"
            logger.exception(self._connection_error)
            return False

    def _sync_get_device_status(self, host: str, email: str, password: str) -> dict[str, Any]:
        """Synchronous method to get device status (runs in separate thread)."""
        try:
            tapo_device = Tapo(host, email, password)
            device_info = tapo_device.getDeviceInfo()
            result = {
                "device_on": device_info.get("device_on", False),
                "brightness": 50,
                "rgb": [255, 255, 255],
                "hue": 0,
                "saturation": 0,
                "effect": "",
            }
            # Try to get LED module info for L900
            try:
                led_info = tapo_device.getLedModule()
                if led_info:
                    result["brightness"] = led_info.get("brightness", 50)
                    result["effect"] = led_info.get("lighting_effect", "")
                    hue_info = led_info.get("hue", {})
                    result["hue"] = hue_info.get("hue", 0)
                    result["saturation"] = hue_info.get("saturation", 0)
                    rgb_info = led_info.get("rgb", {})
                    result["rgb"] = [
                        rgb_info.get("red", 255),
                        rgb_info.get("green", 255),
                        rgb_info.get("blue", 255),
                    ]
            except Exception:
                pass  # LED info not available for all device types
            return result
        except Exception:
            logger.exception("Failed to get device status for {host}:")
            raise

    def _sync_set_device_state(self, host: str, email: str, password: str, **kwargs) -> bool:
        """Synchronous method to set device state (runs in separate thread)."""
        try:
            tapo_device = Tapo(host, email, password)
            # Apply state changes
            if "on" in kwargs:
                if kwargs["on"]:
                    tapo_device.on()
                else:
                    tapo_device.off()
            if "brightness" in kwargs:
                brightness = max(0, min(100, kwargs["brightness"]))
                tapo_device.setBrightness(brightness)
            if "rgb" in kwargs and len(kwargs["rgb"]) >= 3:
                tapo_device.setRgbColor(kwargs["rgb"][0], kwargs["rgb"][1], kwargs["rgb"][2])
            if "hue" in kwargs and "saturation" in kwargs:
                tapo_device.setHueSaturation(kwargs["hue"], kwargs["saturation"])
            if kwargs.get("effect"):
                tapo_device.setLightingEffect(kwargs["effect"])
            return True
        except Exception:
            logger.exception("Failed to set device state for {host}:")
            raise

    async def rescan_devices(self) -> bool:
        """Rescan all Tapo lighting devices to update status."""
        try:
            if not self._initialized:
                return False
            logger.info("Rescanning Tapo lighting devices...")
            updated_count = 0
            # Use ThreadPoolExecutor to run synchronous pytapo calls
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for device_id, device in self.devices.items():
                    host = self._device_hosts.get(device_id)
                    if not host:
                        continue
                    # Submit the synchronous call to the thread pool
                    future = executor.submit(
                        self._sync_get_device_status,
                        host,
                        self._account_email,
                        self._account_password,
                    )
                    futures[future] = (device_id, device)
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    device_id, device = futures[future]
                    try:
                        status = future.result()
                        # Update device state
                        device.on = status.get("device_on", False)
                        device.brightness = status.get("brightness", 50)
                        device.rgb = status.get("rgb", [255, 255, 255])
                        device.hue = status.get("hue", 0)
                        device.saturation = status.get("saturation", 0)
                        device.effect = status.get("effect", "")
                        device.reachable = True
                        device.last_seen = datetime.now().isoformat()
                        updated_count += 1
                        logger.debug(f"Updated Tapo light {device_id}: on={device.on}, brightness={device.brightness}")
                    except Exception as e:
                        logger.warning(f"Failed to update Tapo light {device_id}: {e}")
                        device.reachable = False
                        device.last_seen = datetime.now().isoformat()
            self._last_scan_time = datetime.now()
            logger.info(f"Rescanned {len(self.devices)} Tapo lights, updated {updated_count}")
            return True
        except Exception:
            logger.exception("Failed to rescan Tapo lighting devices:")
            return False

    async def get_all_lights(self) -> list[TapoLight]:
        """Get all configured Tapo lights."""
        if not self._initialized:
            await self.initialize()
        # Rescan to get current status
        await self.rescan_devices()
        return list(self.devices.values())

    async def get_light(self, light_id: str) -> TapoLight | None:
        """Get a specific Tapo light by ID."""
        if not self._initialized:
            await self.initialize()
        return self.devices.get(light_id)

    async def set_light_state(
        self,
        light_id: str,
        on: bool | None = None,
        brightness_percent: int | None = None,
        hue: int | None = None,
        saturation: int | None = None,
        rgb: list[int] | None = None,
        effect: str | None = None,
    ) -> bool:
        """Set Tapo light state."""
        try:
            if not self._initialized:
                await self.initialize()
            device = self.devices.get(light_id)
            if not device:
                logger.error(f"Tapo light {light_id} not found")
                return False
            # Always update local state for UI responsiveness
            if on is not None:
                device.on = on
            if brightness_percent is not None:
                device.brightness = max(0, min(100, brightness_percent))
            if rgb is not None and len(rgb) >= 3:
                device.rgb = rgb[:3]
            if hue is not None and saturation is not None:
                device.hue = hue
                device.saturation = saturation
            if effect is not None:
                device.effect = effect
            device.last_seen = datetime.now().isoformat()
            # Try to control the physical device if it's reachable
            if device.reachable:
                if self._device_readonly.get(light_id, False):
                    logger.warning(f"Tapo light {light_id} is read-only")
                    return True  # Still return true since local state was updated
                host = self._device_hosts.get(light_id)
                if not host:
                    logger.error(f"No host configured for Tapo light {light_id}")
                    return False
                # Prepare arguments for the synchronous call
                kwargs = {}
                if on is not None:
                    kwargs["on"] = on
                if brightness_percent is not None:
                    kwargs["brightness"] = brightness_percent
                if hue is not None:
                    kwargs["hue"] = hue
                if saturation is not None:
                    kwargs["saturation"] = saturation
                if rgb is not None:
                    kwargs["rgb"] = rgb
                if effect is not None:
                    kwargs["effect"] = effect
                # Use ThreadPoolExecutor to run the synchronous pytapo call
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._sync_set_device_state,
                        host,
                        self._account_email,
                        self._account_password,
                        **kwargs,
                    )
                    # Wait for the result
                    success = future.result(timeout=5)  # 5 second timeout
                    if success:
                        logger.info(
                            f"Successfully set physical Tapo light {light_id} state: on={on}, brightness={brightness_percent}, rgb={rgb}"
                        )
                    else:
                        logger.warning(f"Failed to set physical Tapo light {light_id} state, but local state updated")
            else:
                logger.info(
                    f"Tapo light {light_id} not reachable, updated local state only: on={on}, brightness={brightness_percent}, rgb={rgb}"
                )
            return True
        except Exception:
            logger.exception("Failed to set Tapo light {light_id} state:")
            return False

    async def toggle_light(self, light_id: str) -> bool:
        """Toggle Tapo light on/off."""
        try:
            device = await self.get_light(light_id)
            if not device:
                return False
            return await self.set_light_state(light_id, on=not device.on)
        except Exception:
            logger.exception("Failed to toggle Tapo light {light_id}:")
            return False


# Global manager instance
tapo_lighting_manager = TapoLightingManager()


# MCP Tools
class TapoLightingTool(BaseTool):
    """Base class for Tapo lighting MCP tools."""

    def __init__(self):
        super().__init__(category=ToolCategory.LIGHTING, description="Control Tapo smart lighting devices")

    async def ensure_initialized(self) -> bool:
        """Ensure the lighting manager is initialized."""
        if not tapo_lighting_manager._initialized:
            return await tapo_lighting_manager.initialize()
        return True


@tool()
class ListTapoLights(TapoLightingTool):
    """List all Tapo smart lights."""

    def __init__(self):
        super().__init__()

    async def execute(self) -> dict[str, Any]:
        """List all configured Tapo lights."""
        try:
            if not await self.ensure_initialized():
                return {
                    "success": False,
                    "message": "Failed to initialize Tapo lighting",
                    "error": "Failed to initialize Tapo lighting",
                    "lights": [],
                }
            lights = await tapo_lighting_manager.get_all_lights()
            return {
                "success": True,
                "lights": [
                    {
                        "device_id": light.device_id,
                        "name": light.name,
                        "location": light.location,
                        "on": light.on,
                        "brightness": light.brightness,
                        "rgb": light.rgb,
                        "effect": light.effect,
                        "reachable": light.reachable,
                        "last_seen": light.last_seen,
                    }
                    for light in lights
                ],
                "count": len(lights),
            }
        except Exception as e:
            logger.exception("Failed to list Tapo lights:")
            return {
                "success": False,
                "message": f"Failed to list Tapo lights: {e}",
                "error": f"Failed to list Tapo lights: {e}",
                "lights": [],
            }


@tool()
class ControlTapoLight(TapoLightingTool):
    """Control a Tapo smart light."""

    def __init__(self):
        super().__init__()

    async def execute(
        self,
        device_id: str,
        action: str,
        brightness_percent: int | None = None,
        hue: int | None = None,
        saturation: int | None = None,
        rgb: list[int] | None = None,
        effect: str | None = None,
    ) -> dict[str, Any]:
        """Control a Tapo light."""
        try:
            if not await self.ensure_initialized():
                return {
                    "success": False,
                    "message": "Failed to initialize Tapo lighting",
                    "error": "Failed to initialize Tapo lighting",
                }
            # Parse action
            if action.lower() == "on":
                success = await tapo_lighting_manager.set_light_state(
                    device_id, on=True, brightness_percent=brightness_percent
                )
            elif action.lower() == "off":
                success = await tapo_lighting_manager.set_light_state(device_id, on=False)
            elif action.lower() == "toggle":
                success = await tapo_lighting_manager.toggle_light(device_id)
            elif action.lower() == "brightness" and brightness_percent is not None:
                success = await tapo_lighting_manager.set_light_state(device_id, brightness_percent=brightness_percent)
            elif action.lower() == "color" and rgb:
                success = await tapo_lighting_manager.set_light_state(device_id, rgb=rgb)
            elif action.lower() == "hsv" and hue is not None and saturation is not None:
                success = await tapo_lighting_manager.set_light_state(device_id, hue=hue, saturation=saturation)
            elif action.lower() == "effect" and effect:
                success = await tapo_lighting_manager.set_light_state(device_id, effect=effect)
            else:
                return {
                    "success": False,
                    "message": f"Unknown action '{action}' or missing parameters",
                }
            if success:
                light = await tapo_lighting_manager.get_light(device_id)
                return {
                    "success": True,
                    "action": action,
                    "device_id": device_id,
                    "light": {
                        "name": light.name if light else "Unknown",
                        "on": light.on if light else False,
                        "brightness": light.brightness if light else 0,
                        "rgb": light.rgb if light else [255, 255, 255],
                        "effect": light.effect if light else "",
                    }
                    if light
                    else None,
                }
            return {
                "success": False,
                "message": f"Failed to {action} light {device_id}",
                "error": f"Failed to {action} light {device_id}",
            }
        except Exception as e:
            logger.exception("Failed to control Tapo light {device_id}:")
            return {
                "success": False,
                "message": f"Failed to control light: {e}",
                "error": f"Failed to control light: {e}",
            }


@tool()
class GetTapoLightStatus(TapoLightingTool):
    """Get status of a specific Tapo light."""

    def __init__(self):
        super().__init__()

    async def execute(self, device_id: str) -> dict[str, Any]:
        """Get Tapo light status."""
        try:
            if not await self.ensure_initialized():
                return {
                    "success": False,
                    "message": "Failed to initialize Tapo lighting",
                    "error": "Failed to initialize Tapo lighting",
                }
            light = await tapo_lighting_manager.get_light(device_id)
            if light:
                return {
                    "success": True,
                    "light": {
                        "device_id": light.device_id,
                        "name": light.name,
                        "location": light.location,
                        "on": light.on,
                        "brightness": light.brightness,
                        "rgb": light.rgb,
                        "hue": light.hue,
                        "saturation": light.saturation,
                        "effect": light.effect,
                        "reachable": light.reachable,
                        "last_seen": light.last_seen,
                    },
                }
            return {
                "success": False,
                "message": f"Tapo light {device_id} not found",
                "error": f"Tapo light {device_id} not found",
            }
        except Exception as e:
            logger.exception("Failed to get Tapo light status for {device_id}:")
            return {
                "success": False,
                "message": f"Failed to get light status: {e}",
                "error": f"Failed to get light status: {e}",
            }
