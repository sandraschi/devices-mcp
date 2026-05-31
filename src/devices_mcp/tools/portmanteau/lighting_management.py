"""
Lighting Management Portmanteau Tool

Consolidates all lighting-related operations into a single tool with action-based interface.
Supports Tapo smart lights with color control, brightness, effects, and animations.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from devices_mcp.tools.lighting.hue_tools import get_hue_manager
from devices_mcp.tools.lighting.tapo_lighting_tools import tapo_lighting_manager
from devices_mcp.utils.response_builders import (
    build_hardware_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)

LIGHTING_ACTIONS = {
    "status": "Get smart light status",
    "control": "Control smart light (on/off/brightness/color/effects)",
    "list": "List all available smart lights",
    "effects": "Get available light effects/animations",
}


def register_lighting_management_tool(mcp: FastMCP) -> None:
    """Register the lighting management portmanteau tool."""

    @mcp.tool()
    async def lighting_management(
        action: str,  # "status", "control", "list", "effects"
        device_id: str | None = None,
        power_state: str | None = None,  # "on", "off", "toggle"
        brightness_percent: int | None = None,  # 0-100
        hue: int | None = None,  # 0-360
        saturation: int | None = None,  # 0-100
        rgb: list[int] | None = None,  # [r, g, b] 0-255
        effect: str | None = None,  # effect name
        animation_speed: int | None = None,  # 1-100
    ) -> dict[str, Any]:
        """
        Comprehensive smart lighting management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 4+ separate tools (one per operation), this tool consolidates related
        lighting operations into a single interface. Prevents tool explosion (4+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.

        Args:
            action (str, required): The operation to perform. Must be one of: "status", "control", "list", "effects".
                - "status": Get smart light status (requires: device_id)
                - "control": Control smart light (requires: device_id, at least one control parameter)
                - "list": List all available smart lights (no additional parameters)
                - "effects": Get available light effects/animations (no additional parameters)

            device_id (str, optional): Target device ID for status/control operations
            power_state (str, optional): Power control: "on", "off", "toggle"
            brightness_percent (int, optional): Brightness level (0-100)
            hue (int, optional): Color hue (0-360 degrees)
            saturation (int, optional): Color saturation (0-100)
            rgb (List[int], optional): RGB color values [r, g, b] (0-255 each)
            effect (str, optional): Light effect/animation name
            animation_speed (int, optional): Animation speed (1-100)

        Returns:
            dict[str, Any]: Dictionary containing the lighting operation result.

        Examples:
            # List all lights
            result = await lighting_management(action="list")

            # Get status of specific light
            result = await lighting_management(action="status", device_id="tapo_l900_lightstrip")

            # Turn light on with full brightness
            result = await lighting_management(action="control", device_id="tapo_l900_lightstrip",
                                             power_state="on", brightness_percent=100)

            # Set red color
            result = await lighting_management(action="control", device_id="tapo_l900_lightstrip",
                                             rgb=[255, 0, 0])

            # Set warm white with 50% brightness
            result = await lighting_management(action="control", device_id="tapo_l900_lightstrip",
                                             hue=30, saturation=50, brightness_percent=50)

            # Apply breathing effect
            result = await lighting_management(action="control", device_id="tapo_l900_lightstrip",
                                             effect="breathing", animation_speed=50)
        """
        try:
            if action not in LIGHTING_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(LIGHTING_ACTIONS.keys())}",
                }

            logger.info(f"Executing lighting management action: {action}")

            # Initialize lighting manager if needed
            if not tapo_lighting_manager._initialized:
                success = await tapo_lighting_manager.initialize()
                if not success:
                    return build_hardware_error_response(
                        operation="lighting_management",
                        error="Failed to initialize Tapo lighting system",
                        message="Cannot connect to Tapo lighting devices. Check network connectivity and device power.",
                    )

            if action == "list":
                return await _list_lights()
            if action == "status":
                return await _get_light_status(device_id)
            if action == "control":
                return await _control_light(
                    device_id,
                    power_state,
                    brightness_percent,
                    hue,
                    saturation,
                    rgb,
                    effect,
                    animation_speed,
                )
            if action == "effects":
                return await _get_light_effects()
            return {
                "success": False,
                "error": f"Action '{action}' not implemented yet",
            }

        except Exception as e:
            logger.exception(f"Lighting management {action} operation failed")
            return build_hardware_error_response(
                operation="lighting_management",
                error=str(e),
                message=f"Lighting operation '{action}' failed. Check device connectivity and try again.",
            )


async def _list_lights() -> dict[str, Any]:
    """List all available smart lights (Hue + Tapo)."""
    try:
        all_lights = []

        # Get Tapo lights
        try:
            if not tapo_lighting_manager._initialized:
                success = await tapo_lighting_manager.initialize()
                if success:
                    tapo_lights = await tapo_lighting_manager.get_all_lights()
                    for light in tapo_lights:
                        all_lights.append(
                            {
                                "device_id": light.device_id,
                                "light_id": light.device_id,  # Unified ID for web interface
                                "name": light.name,
                                "location": light.location,
                                "model": light.model,
                                "on": light.on,
                                "brightness": light.brightness,
                                "brightness_percent": light.brightness,
                                "rgb": light.rgb,
                                "hue": light.hue,
                                "saturation": light.saturation,
                                "effect": light.effect,
                                "reachable": light.reachable,
                                "last_seen": light.last_seen,
                                "light_type": "tapo",
                                "manufacturer": "TP-Link",
                            }
                        )
        except Exception as e:
            logger.warning(f"Failed to get Tapo lights: {e}")

        # Get Hue lights
        try:
            hue_manager = get_hue_manager()
            if not hue_manager._initialized:
                await hue_manager.initialize()

            if hue_manager._initialized:
                hue_lights = await hue_manager.get_all_lights()
                for light in hue_lights:
                    all_lights.append(
                        {
                            "device_id": str(light.light_id),
                            "light_id": str(light.light_id),  # Unified ID for web interface
                            "name": light.name,
                            "location": light.room or "Unassigned",
                            "model": light.model,
                            "on": light.on,
                            "brightness": light.brightness,
                            "brightness_percent": light.brightness_percent,
                            "rgb": light.rgb,
                            "hue": light.hue,
                            "saturation": light.saturation,
                            "effect": None,  # Hue doesn't have effects like Tapo
                            "reachable": light.reachable,
                            "last_seen": light.last_seen,
                            "light_type": "hue",
                            "manufacturer": "Philips",
                            "color_mode": light.color_mode,
                            "xy": light.xy,
                            "color_temp": light.color_temp,
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to get Hue lights: {e}")

        online_count = len([light for light in all_lights if light.get("reachable", True)])
        hue_count = len([light for light in all_lights if light.get("light_type") == "hue"])
        tapo_count = len([light for light in all_lights if light.get("light_type") == "tapo"])

        summary = f"Found {len(all_lights)} smart light{'s' if len(all_lights) != 1 else ''}"
        if hue_count > 0 and tapo_count > 0:
            summary += f" ({hue_count} Hue, {tapo_count} Tapo)"
        elif hue_count > 0:
            summary += f" ({hue_count} Hue)"
        elif tapo_count > 0:
            summary += f" ({tapo_count} Tapo)"

        return build_success_response(
            operation="lighting_list",
            summary=summary,
            result={
                "lights": all_lights,
                "total_count": len(all_lights),
                "online_count": online_count,
                "hue_count": hue_count,
                "tapo_count": tapo_count,
            },
            recommendations=[
                "Use 'status' action to get detailed information about specific lights",
                "Use 'control' action to adjust brightness, colors, and effects",
                "Check 'effects' action for available light animations",
            ],
            next_steps=[
                "Try controlling a light with 'control' action",
                "Experiment with different colors and brightness levels",
                "Set up automated lighting scenes",
            ],
        )

    except Exception as e:
        return build_hardware_error_response(
            operation="lighting_list",
            error=str(e),
            message="Cannot retrieve lighting device list. Check network connectivity.",
        )


async def _get_light_status(device_id: str | None) -> dict[str, Any]:
    """Get detailed status of a specific light."""
    if not device_id:
        return {
            "success": False,
            "error": "device_id is required for status action",
        }

    try:
        light = await tapo_lighting_manager.get_light(device_id)

        if not light:
            return {
                "success": False,
                "error": f"Light '{device_id}' not found",
                "available_lights": await _get_light_ids(),
            }

        return build_success_response(
            operation="lighting_status",
            summary=f"Light '{light.name}' is {'on' if light.on else 'off'} with {light.brightness}% brightness",
            result={
                "light": {
                    "device_id": light.device_id,
                    "name": light.name,
                    "location": light.location,
                    "model": light.model,
                    "manufacturer": light.manufacturer,
                    "on": light.on,
                    "brightness": light.brightness,
                    "color_temp": light.color_temp,
                    "hue": light.hue,
                    "saturation": light.saturation,
                    "rgb": light.rgb,
                    "effect": light.effect,
                    "reachable": light.reachable,
                    "last_seen": light.last_seen,
                }
            },
            recommendations=[
                "Adjust brightness with 'control' action and brightness_percent parameter",
                "Change colors using rgb, hue, or saturation parameters",
                "Try different effects with the 'control' action",
                "Set up automation based on light state",
            ],
            next_steps=[
                "Try changing the brightness level",
                "Experiment with different colors",
                "Apply a light effect or animation",
            ],
        )

    except Exception as e:
        return build_hardware_error_response(
            operation="lighting_status",
            error=str(e),
            message=f"Cannot get status for light '{device_id}'. Check device connectivity.",
        )


async def _control_light(
    device_id: str | None,
    power_state: str | None,
    brightness_percent: int | None,
    hue: int | None,
    saturation: int | None,
    rgb: list[int] | None,
    effect: str | None,
    animation_speed: int | None,
) -> dict[str, Any]:
    """Control a smart light with various parameters."""
    if not device_id:
        return {
            "success": False,
            "error": "device_id is required for control action",
        }

    # Validate that at least one control parameter is provided
    control_params = [power_state, brightness_percent, hue, saturation, rgb, effect]
    if not any(control_params):
        return {
            "success": False,
            "error": "At least one control parameter must be provided (power_state, brightness_percent, hue, saturation, rgb, or effect)",
        }

    try:
        # Build control parameters
        control_kwargs = {}

        if power_state:
            if power_state.lower() == "toggle":
                success = await tapo_lighting_manager.toggle_light(device_id)
                action_desc = "toggled"
            else:
                control_kwargs["on"] = power_state.lower() == "on"
                action_desc = f"turned {power_state}"

        if brightness_percent is not None:
            control_kwargs["brightness_percent"] = brightness_percent

        if hue is not None:
            control_kwargs["hue"] = hue

        if saturation is not None:
            control_kwargs["saturation"] = saturation

        if rgb:
            if len(rgb) != 3:
                return {
                    "success": False,
                    "error": "RGB parameter must be a list of 3 integers [r, g, b]",
                }
            control_kwargs["rgb"] = rgb

        if effect:
            control_kwargs["effect"] = effect
            if animation_speed:
                control_kwargs["animation_speed"] = animation_speed

        # Determine light type and use appropriate manager
        # First try to find the light in our cached data to determine type
        light_type = None
        try:
            # Check if it's a Tapo light
            if tapo_lighting_manager._initialized:
                tapo_light = await tapo_lighting_manager.get_light(device_id)
                if tapo_light:
                    light_type = "tapo"
        except Exception:
            pass

        if light_type != "tapo":
            try:
                # Check if it's a Hue light
                hue_manager = get_hue_manager()
                if hue_manager._initialized:
                    hue_light = await hue_manager.get_light(device_id)
                    if hue_light:
                        light_type = "hue"
            except Exception:
                pass

        if not light_type:
            return {
                "success": False,
                "error": f"Light '{device_id}' not found or not reachable. Check device ID and ensure the device is powered on.",
            }

        # Apply control based on light type
        if light_type == "tapo":
            # Handle Tapo-specific features like effects
            if effect:
                control_kwargs["effect"] = effect
                if animation_speed:
                    control_kwargs["animation_speed"] = animation_speed

            if control_kwargs:
                success = await tapo_lighting_manager.set_light_state(device_id, **control_kwargs)
            elif power_state and power_state.lower() == "toggle":
                success = await tapo_lighting_manager.toggle_light(device_id)
            else:
                return {
                    "success": False,
                    "error": "No valid control parameters provided",
                }

            # Get updated light status
            light = await tapo_lighting_manager.get_light(device_id)

        elif light_type == "hue":
            # Convert parameters for Hue API
            hue_kwargs = {}

            if power_state:
                if power_state.lower() == "toggle":
                    # For Hue, we need to get current state and toggle
                    current_light = await hue_manager.get_light(device_id)
                    if current_light:
                        hue_kwargs["on"] = not current_light.on
                        action_desc = "toggled"
                    else:
                        return {
                            "success": False,
                            "error": f"Cannot toggle Hue light '{device_id}' - unable to read current state",
                        }
                else:
                    hue_kwargs["on"] = power_state.lower() == "on"
                    action_desc = f"turned {power_state}"

            if brightness_percent is not None:
                hue_kwargs["brightness_percent"] = brightness_percent

            if hue is not None:
                hue_kwargs["hue"] = hue

            if saturation is not None:
                hue_kwargs["saturation"] = saturation

            if rgb:
                hue_kwargs["rgb"] = rgb

            # Hue doesn't support effects like Tapo, ignore effect parameter for Hue lights

            success = await hue_manager.set_light_state(device_id, **hue_kwargs)

            # Get updated light status
            light = await hue_manager.get_light(device_id)

        else:
            return {
                "success": False,
                "error": f"Unsupported light type: {light_type}",
            }

        if success:
            # Get updated light status
            light = await tapo_lighting_manager.get_light(device_id)

            # Build description of changes
            changes = []
            if power_state:
                changes.append(f"power {action_desc}")
            if brightness_percent is not None:
                changes.append(f"brightness to {brightness_percent}%")
            if rgb:
                changes.append(f"color to RGB{rgb}")
            if hue is not None or saturation is not None:
                changes.append("color settings updated")
            if effect:
                changes.append(f"effect to '{effect}'")

            change_desc = ", ".join(changes) if changes else "settings updated"

            return build_success_response(
                operation="lighting_control",
                summary=f"Light '{light.name if light else device_id}' {change_desc}",
                result={
                    "device_id": device_id,
                    "success": True,
                    "changes_applied": changes,
                    "current_state": {
                        "on": light.on if light else None,
                        "brightness": light.brightness if light else None,
                        "rgb": light.rgb if light else None,
                        "hue": light.hue if light else None,
                        "saturation": light.saturation if light else None,
                        "effect": light.effect if light else None,
                    }
                    if light
                    else None,
                },
                recommendations=[
                    "Check the new light state with 'status' action",
                    "Try different color combinations",
                    "Experiment with various lighting effects",
                    "Set up lighting automation schedules",
                ],
                next_steps=[
                    "Verify the changes with 'status' action",
                    "Try adjusting other parameters",
                    "Save favorite lighting configurations",
                ],
            )
        return build_hardware_error_response(
            operation="lighting_control",
            error="Control command failed",
            message=f"Failed to apply lighting changes to '{device_id}'. Device may be unreachable.",
        )

    except Exception as e:
        return build_hardware_error_response(
            operation="lighting_control",
            error=str(e),
            message=f"Cannot control light '{device_id}'. Check device connectivity and parameters.",
        )


async def _get_light_effects() -> dict[str, Any]:
    """Get available light effects and animations."""
    try:
        # Get available effects from the lighting manager
        effects = await tapo_lighting_manager.get_available_effects()

        return build_success_response(
            operation="lighting_effects",
            summary=f"Found {len(effects)} available lighting effects",
            result={
                "effects": effects,
                "total_count": len(effects),
                "categories": list(set(effect.get("category", "general") for effect in effects)),
            },
            recommendations=[
                "Use 'control' action with 'effect' parameter to apply animations",
                "Try different animation speeds with 'animation_speed' parameter",
                "Combine effects with color and brightness settings",
            ],
            next_steps=[
                "Try applying different effects to your lights",
                "Experiment with animation speeds",
                "Create custom lighting scenes",
            ],
        )

    except Exception as e:
        return build_hardware_error_response(
            operation="lighting_effects",
            error=str(e),
            message="Cannot retrieve lighting effects list. Some devices may not support effects.",
        )


async def _get_light_ids() -> list[str]:
    """Helper function to get all light device IDs."""
    try:
        lights = await tapo_lighting_manager.get_all_lights()
        return [light.device_id for light in lights]
    except:
        return []
