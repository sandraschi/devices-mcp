"""
Tapo Control Portmanteau Tool

Unified tool for controlling all hardware via natural commands.
When you say "tapo list lights", this tool handles it.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager
from devices_mcp.tools.lighting.hue_tools import hue_manager
from devices_mcp.tools.lighting.tapo_lighting_tools import tapo_lighting_manager

logger = logging.getLogger(__name__)


def _model_dump(model: Any) -> dict[str, Any]:
    """Serialize Pydantic models across v1/v2."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()  # type: ignore[attr-defined]


DEVICE_ACTIONS = {
    # Lighting (Hue + Tapo)
    "list_lights": "List all lights (Hue + Tapo)",
    "list_light": "List all lights (alias for list_lights)",
    "list_hue_lights": "List Philips Hue lights only",
    "list_tapo_lights": "List Tapo smart lights only",
    "turn_on_light": "Turn on a light (specify light_id)",
    "turn_off_light": "Turn off a light (specify light_id)",
    "set_brightness": "Set light brightness (specify light_id and brightness_percent)",
    "set_color": "Set light color (specify light_id and rgb values)",
    "set_effect": "Set light effect/mode (specify light_id and effect name)",
    "list_groups": "List all Hue groups/rooms",
    "list_scenes": "List all available scenes",
    "activate_scene": "Activate a lighting scene",
    # Energy
    "list_plugs": "List all smart plugs",
    "list_plug": "List all smart plugs (alias for list_plugs)",
    "turn_on_plug": "Turn on a smart plug",
    "turn_off_plug": "Turn off a smart plug",
    # Kitchen
    "list_kitchen": "List all kitchen appliances",
    "turn_on_kettle": "Turn on Zojirushi kettle",
    "turn_off_kettle": "Turn off Zojirushi kettle",
    # Status
    "status": "Get overall system status",
}


def register_device_control_tool(mcp: FastMCP) -> None:
    """Register the unified device control tools."""

    @mcp.tool()
    async def device_control(
        action: str,
        device_id: str | None = None,
        light_id: str | None = None,
        group_id: str | None = None,
        scene_id: str | None = None,
        brightness_percent: int | str | None = None,
        power_state: str | None = None,
        effect: str | None = None,
    ) -> dict[str, Any]:
        """
        Unified device control tool for all hardware operations.

        This tool provides a natural interface for controlling all hardware.
        Use intuitive commands like "list lights", "turn on light", etc.

        Args:
            action (str, required): The action to perform. Examples:
                - "list lights" or "list_lights" - List all Hue lights
                - "list plugs" or "list_plugs" - List all smart plugs
                - "turn on light" or "turn_on_light" - Turn on a light (requires: light_id)
                - "turn off light" or "turn_off_light" - Turn off a light (requires: light_id)
                - "set brightness" or "set_brightness" - Set light brightness (requires: light_id, brightness_percent)
                - "list groups" or "list_groups" - List all Hue groups
                - "list scenes" or "list_scenes" - List all scenes
                - "activate scene" or "activate_scene" - Activate a scene (requires: scene_id)
                - "turn on plug" or "turn_on_plug" - Turn on a smart plug (requires: device_id)
                - "turn off plug" or "turn_off_plug" - Turn off a smart plug (requires: device_id)
                - "list kitchen" - List kitchen appliances
                - "turn on kettle" - Turn on Zojirushi kettle
                - "turn off kettle" - Turn off Zojirushi kettle
                - "status" - Get system status

            device_id (str | None): Device ID for plugs/appliances
            light_id (str | None): Light ID for light operations
            group_id (str | None): Group ID for group operations
            scene_id (str | None): Scene ID for scene operations
            brightness_percent (int | None): Brightness percentage (0-100)
            power_state (str | None): Power state ("on"/"off"/"toggle")
            effect (str | None): Lighting effect name (for Tapo lights)

        Returns:
            dict[str, Any]: Operation result
        """
        try:
            # Type conversion for parameters that may come as strings from JSON-RPC
            if brightness_percent is not None:
                if isinstance(brightness_percent, str):
                    brightness_percent = int(brightness_percent)
                elif not isinstance(brightness_percent, int):
                    return {
                        "success": False,
                        "message": f"brightness_percent must be an integer, got {type(brightness_percent).__name__}",
                        "error": f"brightness_percent must be an integer, got {type(brightness_percent).__name__}",
                    }

            # Normalize action (handle spaces and case)
            action_lower = action.lower().replace(" ", "_").strip()

            logger.info(f"Executing device action: {action} (normalized: {action_lower})")

            # Lighting actions
            if action_lower in ["list_lights", "list_light", "list lights", "list light"]:
                # Get both Hue and Tapo lights
                hue_lights = []
                tapo_lights = []

                if hue_manager._initialized or await hue_manager.initialize():
                    hue_lights = await hue_manager.get_all_lights()

                if tapo_lighting_manager._initialized or await tapo_lighting_manager.initialize():
                    tapo_lights_raw = await tapo_lighting_manager.get_all_lights()
                    tapo_lights = [_model_dump(light) for light in tapo_lights_raw]

                all_lights = []
                all_lights.extend([_model_dump(light) for light in hue_lights])
                all_lights.extend(tapo_lights)

                return {
                    "success": True,
                    "action": "list_lights",
                    "data": {
                        "lights": all_lights,
                        "count": len(all_lights),
                        "hue_count": len(hue_lights),
                        "tapo_count": len(tapo_lights),
                    },
                }

            if action_lower in ["list_hue_lights", "list hue lights"]:
                if not hue_manager._initialized:
                    await hue_manager.initialize()
                lights = await hue_manager.get_all_lights()
                return {
                    "success": True,
                    "action": "list_hue_lights",
                    "data": {
                        "lights": [_model_dump(light) for light in lights],
                        "count": len(lights),
                        "type": "hue",
                    },
                }

            if action_lower in ["list_tapo_lights", "list tapo lights"]:
                if not tapo_lighting_manager._initialized:
                    await tapo_lighting_manager.initialize()
                lights = await tapo_lighting_manager.get_all_lights()
                return {
                    "success": True,
                    "action": "list_tapo_lights",
                    "data": {
                        "lights": [_model_dump(light) for light in lights],
                        "count": len(lights),
                        "type": "tapo",
                    },
                }

            # Try Hue first, then Tapo for light operations
            async def _control_light(light_id: str, action: str, **kwargs):
                """Try to control light with both Hue and Tapo managers."""
                # First try Hue
                if hue_manager._initialized or await hue_manager.initialize():
                    try:
                        if action == "turn_on":
                            success = await hue_manager.set_light_state(light_id, on=True, **kwargs)
                        elif action == "turn_off":
                            success = await hue_manager.set_light_state(light_id, on=False, **kwargs)
                        elif action == "set_brightness":
                            success = await hue_manager.set_light_state(light_id, on=True, **kwargs)
                        elif action == "set_color":
                            # For Hue, convert RGB to XY
                            rgb = kwargs.get("rgb")
                            if rgb:
                                success = await hue_manager.set_light_rgb(light_id, rgb)
                            else:
                                success = False
                        elif action == "set_effect":
                            # Hue lights don't support effects
                            return {
                                "success": False,
                                "message": "Effects are not supported for Philips Hue lights",
                                "error": "Effects are not supported for Philips Hue lights",
                            }
                        else:
                            success = False

                        if success:
                            light = await hue_manager.get_light(light_id)
                            return {
                                "success": True,
                                "type": "hue",
                                "light": _model_dump(light) if light else None,
                            }
                    except Exception:
                        pass  # Continue to try Tapo

                # Then try Tapo
                if tapo_lighting_manager._initialized or await tapo_lighting_manager.initialize():
                    try:
                        if action == "turn_on":
                            success = await tapo_lighting_manager.set_light_state(light_id, on=True, **kwargs)
                        elif action == "turn_off":
                            success = await tapo_lighting_manager.set_light_state(light_id, on=False, **kwargs)
                        elif action == "set_brightness" or action == "set_color" or action == "set_effect":
                            success = await tapo_lighting_manager.set_light_state(light_id, **kwargs)
                        else:
                            success = False

                        if success:
                            light = await tapo_lighting_manager.get_light(light_id)
                            return {
                                "success": True,
                                "type": "tapo",
                                "light": _model_dump(light) if light else None,
                            }
                    except Exception:
                        pass  # Both failed

                return {
                    "success": False,
                    "message": f"Light {light_id} not found or failed to control",
                }

            if action_lower in ["turn_on_light", "turn on light", "on light"]:
                if not light_id:
                    return {
                        "success": False,
                        "message": "light_id is required to turn on a light",
                        "error": "light_id is required to turn on a light",
                    }
                result = await _control_light(light_id, "turn_on", brightness_percent=brightness_percent)
                if result["success"]:
                    return {
                        "success": True,
                        "action": "turn_on_light",
                        "type": result.get("type", "unknown"),
                        "data": {"light": result.get("light")},
                    }
                return {
                    "success": False,
                    "message": result.get("error"),
                    "error": result.get("error", "Failed to turn on light"),
                }

            if action_lower in ["turn_off_light", "turn off light", "off light"]:
                if not light_id:
                    return {
                        "success": False,
                        "message": "light_id is required to turn off a light",
                        "error": "light_id is required to turn off a light",
                    }
                result = await _control_light(light_id, "turn_off")
                if result["success"]:
                    return {
                        "success": True,
                        "action": "turn_off_light",
                        "type": result.get("type", "unknown"),
                        "data": {"light": result.get("light")},
                    }
                return {
                    "success": False,
                    "message": result.get("error"),
                    "error": result.get("error", "Failed to turn off light"),
                }

            if action_lower in ["set_brightness", "set brightness"]:
                if not light_id:
                    return {
                        "success": False,
                        "message": "light_id is required to set brightness",
                        "error": "light_id is required to set brightness",
                    }
                if brightness_percent is None:
                    return {
                        "success": False,
                        "message": "brightness_percent is required",
                        "error": "brightness_percent is required",
                    }
                result = await _control_light(light_id, "set_brightness", brightness_percent=brightness_percent)
                if result["success"]:
                    return {
                        "success": True,
                        "action": "set_brightness",
                        "type": result.get("type", "unknown"),
                        "data": {"light": result.get("light")},
                    }
                return {
                    "success": False,
                    "message": result.get("error"),
                    "error": result.get("error", "Failed to set brightness"),
                }

            if action_lower in ["set_color", "set color"]:
                if not light_id:
                    return {
                        "success": False,
                        "message": "light_id is required to set color",
                        "error": "light_id is required to set color",
                    }
                rgb_values = None
                if isinstance(brightness_percent, list) and len(brightness_percent) >= 3:
                    rgb_values = brightness_percent[:3]
                if not rgb_values:
                    return {
                        "success": False,
                        "message": "rgb parameter required for set_color (pass as brightness_percent=[r,g,b])",
                        "error": "rgb parameter required for set_color (pass as brightness_percent=[r,g,b])",
                    }

                result = await _control_light(light_id, "set_color", rgb=rgb_values)
                if result["success"]:
                    return {
                        "success": True,
                        "action": "set_color",
                        "type": result.get("type", "unknown"),
                        "data": {"light": result.get("light")},
                    }
                return {
                    "success": False,
                    "message": result.get("error"),
                    "error": result.get("error", "Failed to set color"),
                }

            if action_lower in ["set_effect", "set effect", "activate_effect"]:
                if not light_id:
                    return {
                        "success": False,
                        "message": "light_id is required to set effect",
                        "error": "light_id is required to set effect",
                    }
                if not effect:
                    return {
                        "success": False,
                        "message": "effect parameter is required",
                        "error": "effect parameter is required",
                    }

                result = await _control_light(light_id, "set_effect", effect=effect)
                if result["success"]:
                    return {
                        "success": True,
                        "action": "set_effect",
                        "type": result.get("type", "unknown"),
                        "data": {"light": result.get("light"), "effect": effect},
                    }
                return {
                    "success": False,
                    "message": result.get("error"),
                    "error": result.get("error", "Failed to set effect"),
                }

            if action_lower in ["list_groups", "list groups"]:
                if not hue_manager._initialized:
                    await hue_manager.initialize()
                groups = await hue_manager.get_all_groups()
                return {
                    "success": True,
                    "action": "list_groups",
                    "data": {
                        "groups": [_model_dump(group) for group in groups],
                        "count": len(groups),
                    },
                }

            if action_lower in ["list_scenes", "list scenes"]:
                if not hue_manager._initialized:
                    await hue_manager.initialize()
                scenes = await hue_manager.get_all_scenes()
                # Filter to unique predefined scenes
                predefined_scenes = {
                    "Arctic aurora",
                    "Bright",
                    "Concentrate",
                    "Dimmed",
                    "Energize",
                    "Nightlight",
                    "Read",
                    "Relax",
                    "Savanna sunset",
                    "Spring blossom",
                    "Tropical twilight",
                }
                seen_names = set()
                filtered_scenes = []
                for scene in scenes:
                    scene_name = scene.name
                    if scene_name in predefined_scenes:
                        if scene_name not in seen_names:
                            seen_names.add(scene_name)
                            filtered_scenes.append(scene)
                    elif scene_name not in seen_names and scene_name not in predefined_scenes:
                        seen_names.add(scene_name)
                        filtered_scenes.append(scene)
                return {
                    "success": True,
                    "action": "list_scenes",
                    "data": {
                        "scenes": [_model_dump(scene) for scene in filtered_scenes],
                        "count": len(filtered_scenes),
                    },
                }

            if action_lower in ["activate_scene", "activate scene"]:
                if not scene_id:
                    return {
                        "success": False,
                        "message": "scene_id is required to activate a scene",
                        "error": "scene_id is required to activate a scene",
                    }
                if not hue_manager._initialized:
                    await hue_manager.initialize()
                success = await hue_manager.activate_scene(scene_id, group_id)
                return {
                    "success": success,
                    "action": "activate_scene",
                    "data": {"scene_id": scene_id},
                }

            # Energy/Plug actions
            if action_lower in ["list_plugs", "list_plug", "list plugs", "list plug"]:
                devices = await tapo_plug_manager.get_all_devices()
                return {
                    "success": True,
                    "action": "list_plugs",
                    "data": {
                        "devices": [
                            {
                                "device_id": device.device_id,
                                "name": device.name,
                                "power_state": device.power_state,
                                "power_watt": device.current_power,
                                "voltage": device.voltage,
                                "current": device.current,
                            }
                            for device in devices
                        ],
                        "count": len(devices),
                    },
                }

            if action_lower in ["turn_on_plug", "turn on plug", "on plug"]:
                if not device_id:
                    return {
                        "success": False,
                        "message": "device_id is required to turn on a plug",
                        "error": "device_id is required to turn on a plug",
                    }
                success = await tapo_plug_manager.toggle_device(device_id, True)
                if success:
                    device = await tapo_plug_manager.get_device_status(device_id)
                    return {
                        "success": True,
                        "action": "turn_on_plug",
                        "data": {
                            "device_id": device_id,
                            "power_state": device.power_state if device else True,
                        },
                    }
                return {"success": False, "message": "Failed to turn on plug", "error": "Failed to turn on plug"}

            if action_lower in ["turn_off_plug", "turn off plug", "off plug"]:
                if not device_id:
                    return {
                        "success": False,
                        "message": "device_id is required to turn off a plug",
                        "error": "device_id is required to turn off a plug",
                    }
                success = await tapo_plug_manager.toggle_device(device_id, False)
                if success:
                    device = await tapo_plug_manager.get_device_status(device_id)
                    return {
                        "success": True,
                        "action": "turn_off_plug",
                        "data": {
                            "device_id": device_id,
                            "power_state": device.power_state if device else False,
                        },
                    }
                return {"success": False, "message": "Failed to turn off plug", "error": "Failed to turn off plug"}

            # Kitchen actions
            if action_lower in ["list_kitchen", "list kitchen"]:
                all_devices = await tapo_plug_manager.get_all_devices()
                kitchen_keywords = ["kitchen", "zojirushi", "kettle", "optigrill", "grill"]
                kitchen_devices = [
                    device
                    for device in all_devices
                    if any(keyword.lower() in device.name.lower() for keyword in kitchen_keywords)
                ]
                return {
                    "success": True,
                    "action": "list_kitchen",
                    "data": {
                        "appliances": [
                            {
                                "device_id": device.device_id,
                                "name": device.name,
                                "power_state": device.power_state,
                                "power_watt": device.current_power,
                            }
                            for device in kitchen_devices
                        ],
                        "count": len(kitchen_devices),
                    },
                }

            if action_lower in ["turn_on_kettle", "turn on kettle", "on kettle"]:
                # Find Zojirushi kettle
                all_devices = await tapo_plug_manager.get_all_devices()
                kettle = next(
                    (d for d in all_devices if "zojirushi" in d.name.lower() or "kettle" in d.name.lower()),
                    None,
                )
                if not kettle:
                    return {
                        "success": False,
                        "message": "Zojirushi kettle not found",
                        "error": "Zojirushi kettle not found",
                    }
                success = await tapo_plug_manager.toggle_device(kettle.device_id, True)
                return {
                    "success": success,
                    "action": "turn_on_kettle",
                    "data": {"device_id": kettle.device_id, "name": kettle.name},
                }

            if action_lower in ["turn_off_kettle", "turn off kettle", "off kettle"]:
                # Find Zojirushi kettle
                all_devices = await tapo_plug_manager.get_all_devices()
                kettle = next(
                    (d for d in all_devices if "zojirushi" in d.name.lower() or "kettle" in d.name.lower()),
                    None,
                )
                if not kettle:
                    return {
                        "success": False,
                        "message": "Zojirushi kettle not found",
                        "error": "Zojirushi kettle not found",
                    }
                success = await tapo_plug_manager.toggle_device(kettle.device_id, False)
                return {
                    "success": success,
                    "action": "turn_off_kettle",
                    "data": {"device_id": kettle.device_id, "name": kettle.name},
                }

            # Status
            if action_lower == "status":
                lights_count = 0
                tapo_lights_count = 0
                plugs_count = 0

                if hue_manager._initialized:
                    lights_count = len(hue_manager.lights)

                if tapo_lighting_manager._initialized:
                    tapo_lights_count = len(tapo_lighting_manager.devices)

                devices = await tapo_plug_manager.get_all_devices()
                plugs_count = len(devices)

                return {
                    "success": True,
                    "action": "status",
                    "data": {
                        "lights": lights_count + tapo_lights_count,
                        "hue_lights": lights_count,
                        "tapo_lights": tapo_lights_count,
                        "smart_plugs": plugs_count,
                        "hue_connected": hue_manager._initialized,
                        "tapo_lighting_connected": tapo_lighting_manager._initialized,
                    },
                }

            # Provide helpful suggestions for unknown actions
            action_lower_normalized = action_lower.replace("_", " ")
            similar_actions = [
                key
                for key in DEVICE_ACTIONS
                if action_lower_normalized in key.replace("_", " ") or key.replace("_", " ") in action_lower_normalized
            ]

            error_msg = f"Unknown action '{action}'."
            if similar_actions:
                error_msg += f" Did you mean: {', '.join(similar_actions[:3])}?"
            else:
                error_msg += f" Available actions: {', '.join(sorted(DEVICE_ACTIONS.keys())[:10])}"
                if len(DEVICE_ACTIONS) > 10:
                    error_msg += f" (and {len(DEVICE_ACTIONS) - 10} more)"

            return {
                "success": False,
                "message": error_msg,
                "error": error_msg,
                "available_actions": list(DEVICE_ACTIONS.keys()),
            }

        except Exception as e:
            logger.exception("Error in device action '{action}':")
            error_msg = f"Failed to execute action '{action}': {e!s}"

            # Provide helpful context for common errors
            error_str = str(e).lower()
            if "connection" in error_str or "timeout" in error_str:
                error_msg += " Check device connectivity and network settings."
            elif "authentication" in error_str or "unauthorized" in error_str:
                error_msg += " Verify device credentials in configuration."
            elif "not found" in error_str:
                error_msg += " Ensure the device exists and is properly configured."

            return {
                "success": False,
                "message": error_msg,
                "error": error_msg,
                "action": action,
                "exception_type": type(e).__name__,
            }

    @mcp.tool()
    async def tapo(
        action: str,
        device_id: str | None = None,
        light_id: str | None = None,
        group_id: str | None = None,
        scene_id: str | None = None,
        brightness_percent: int | str | None = None,
        power_state: str | None = None,
        effect: str | None = None,
    ) -> dict[str, Any]:
        """
        Backward compatibility alias for device_control.
        """
        return await device_control(
            action=action,
            device_id=device_id,
            light_id=light_id,
            group_id=group_id,
            scene_id=scene_id,
            brightness_percent=brightness_percent,
            power_state=power_state,
            effect=effect,
        )


# Alias for portmanteau __init__.py
register_tapo_control_tool = register_device_control_tool
