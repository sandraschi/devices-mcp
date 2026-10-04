"""Climate Management Portmanteau Tool (Midea PortaSplit, mock-first).

Actions: status, control (power/mode/setpoint/fan/swing), list.
Every response carries mock=true until winter hardware flips the backend.
"""

import logging
import time
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.integrations.midea_client import (
    MIDEA_FAN_SPEEDS,
    MIDEA_MODES,
    midea_manager,
)
from devices_mcp.utils.response_builders import build_success_response

logger = logging.getLogger(__name__)

CLIMATE_ACTIONS = {
    "status": "Get AC status (temp, mode, setpoint, power draw)",
    "control": "Control AC (power/mode/setpoint/fan/swing)",
    "list": "List all climate units",
}


def _err(message: str) -> dict[str, Any]:
    logger.warning("climate_management: %s", message)
    return {"success": False, "message": message, "timestamp": time.time()}


def register_climate_management_tool(mcp: FastMCP) -> None:
    """Register the climate management portmanteau tool."""

    @mcp.tool()
    async def climate_management(
        action: Literal["status", "control", "list"],
        device_id: str | None = None,
        power: bool | None = None,
        mode: str | None = None,
        setpoint: float | None = None,
        fan_speed: str | None = None,
        swing: bool | None = None,
    ) -> dict[str, Any]:
        """
        Control and monitor Midea PortaSplit air conditioning (mock until winter hardware).

        ## Return Format
        Dict with success, operation, summary, result (with mock flag), recommendations, next_steps.

        Args:
            action (Literal, required): "status", "control", or "list".
                - "status": requires device_id.
                - "control": requires device_id + at least one of power/mode/setpoint/fan_speed/swing.
                - "list": no args.
            device_id (str): e.g. "midea_portasplit_demo".
            power (bool): True on, False off.
            mode (str): one of off/cool/heat/dry/fan/auto.
            setpoint (float): target C (16-30).
            fan_speed (str): one of auto/low/medium/high/turbo.
            swing (bool): louver swing on/off.
        """
        try:
            if action == "list":
                units = await midea_manager.list_units()
                return build_success_response(
                    operation="climate_list",
                    summary=f"{len(units)} climate unit(s)",
                    result={"devices": [u.to_dict() for u in units]},
                )

            if not device_id:
                return _err(f"{action} needs device_id (see list)")
            unit = await midea_manager.get_unit(device_id)
            if unit is None:
                return _err(f"Unknown climate device '{device_id}' (see list)")

            if action == "status":
                return build_success_response(
                    operation="climate_status",
                    summary=f"{unit.name}: {unit.to_dict()['room_temp_c']} C room, "
                    f"mode {unit.to_dict()['mode']}, mock={unit.mock}",
                    result=unit.to_dict(),
                )

            if action == "control":
                applied: list[str] = []
                try:
                    if power is not None:
                        await unit.set_power(power)
                        applied.append(f"power={power}")
                    if mode is not None:
                        if mode not in MIDEA_MODES:
                            return _err(f"Unknown mode '{mode}'. Use: {list(MIDEA_MODES)}")
                        await unit.set_mode(mode)
                        applied.append(f"mode={mode}")
                    if setpoint is not None:
                        await unit.set_setpoint(setpoint)
                        applied.append(f"setpoint={setpoint}")
                    if fan_speed is not None:
                        if fan_speed not in MIDEA_FAN_SPEEDS:
                            return _err(f"Unknown fan '{fan_speed}'. Use: {list(MIDEA_FAN_SPEEDS)}")
                        await unit.set_fan(fan_speed)
                        applied.append(f"fan={fan_speed}")
                    if swing is not None:
                        await unit.set_swing(swing)
                        applied.append(f"swing={swing}")
                except (ValueError, NotImplementedError) as e:
                    return _err(str(e))
                if not applied:
                    return _err("control needs at least one of power/mode/setpoint/fan_speed/swing")
                return build_success_response(
                    operation="climate_control",
                    summary=f"{unit.name}: applied {', '.join(applied)}",
                    result=unit.to_dict(),
                )

            return _err(f"Unknown action '{action}'")

        except Exception as e:
            logger.exception("climate_management failed:")
            return _err(f"climate_management failed: {e}")
