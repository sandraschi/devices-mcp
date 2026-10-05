"""Climate Management Portmanteau Tool (Midea PortaSplit: mock device now, LAN backend for the real unit)."""

import logging
import time
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.integrations.midea_client import (
    MIDEA_FAN_SPEEDS,
    MIDEA_MODES,
    MOCK_SCENARIOS,
    MideaError,
    midea_manager,
)
from devices_mcp.utils.response_builders import build_success_response

_MUTATING: dict[str, bool] = {}

logger = logging.getLogger(__name__)

CLIMATE_ACTIONS = {
    "status": "Get AC status (temp, mode, setpoint, power draw, energy, faults)",
    "control": "Control AC (power/mode/setpoint/fan/swing/eco/turbo/sleep)",
    "list": "List all climate units",
    "discover": "Find Midea units on the LAN (real units; needs the 'climate' extra)",
    "scenario": "Put a MOCK unit into a situation (heatwave, offline, fault, ...)",
}


def _err(message: str, error_type: str = "invalid_request", suggestions: list[str] | None = None) -> dict[str, Any]:
    logger.warning("climate_management: %s", message)
    return {
        "success": False,
        "message": message,
        "error": message,
        "error_type": error_type,
        "suggestions": suggestions or [],
        "timestamp": time.time(),
    }


def register_climate_management_tool(mcp: FastMCP) -> None:
    """Register the climate management portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def climate_management(
        action: Literal["status", "control", "list", "discover", "scenario"],
        device_id: str | None = None,
        power: bool | None = None,
        mode: str | None = None,
        setpoint: float | None = None,
        fan_speed: str | None = None,
        swing: bool | None = None,
        eco: bool | None = None,
        turbo: bool | None = None,
        sleep: bool | None = None,
        scenario: str | None = None,
        timeout_s: int = 5,
    ) -> dict[str, Any]:
        """
        Control and monitor Midea PortaSplit air conditioning (mock device until the real unit is bought).

        [RATIONALE] One portmanteau for list/status/control/discovery/mock scenarios: they share the unit
        lookup and the error contract.

        Verification status: the mock unit (device_id "midea_portasplit_demo") is fully exercised. The real
        LAN backend (msmart-ng) is UNVERIFIED against a physical PortaSplit; it is tested only against a fake
        that follows msmart-ng's API. Every unit dict says mock true/false.

        Args:
            action (Literal, required): One of:
                - "list": All units.
                - "status": One unit (requires: device_id).
                - "control": Change settings (requires: device_id and at least one setting).
                - "discover": Broadcast-scan the LAN for real units (optional: timeout_s).
                - "scenario": Mock units only (requires: device_id, scenario).
            device_id (str | None): e.g. "midea_portasplit_demo". Required for: status, control, scenario.
            power (bool | None): True on, False off.
            mode (str | None): off, cool, heat, dry, fan or auto.
            setpoint (float | None): Target in C, 16-30.
            fan_speed (str | None): auto, low, medium, high or turbo.
            swing (bool | None): Louver swing on/off.
            eco (bool | None): Eco mode (exclusive with turbo on the mock).
            turbo (bool | None): Turbo mode.
            sleep (bool | None): Sleep mode.
            scenario (str | None): heatwave, cold_snap, offline, online, fault, clear_fault, filter_alert, reset.
            timeout_s (int): Discovery wait in seconds, 1-30. Default 5.

        ## Return Format
            Success: {"success": True, "operation": str, "summary": str, "result": {...}} where result is the unit
            dict: device_id, name, mock, online, power, mode, setpoint_c, room_temp_c, outdoor_temp_c, humidity_pct,
            fan_speed, swing, eco, turbo, sleep, power_w, energy_kwh, error_code, filter_alert, scenario, last_error.
            Failure: {"success": False, "error": str, "error_type": str, "suggestions": [str]} with error_type one of
            invalid_request, device_offline, connect_failed, device_not_found, dependency_missing, unsupported,
            invalid_setpoint, not_mock, command_failed.

        ## Examples
            await climate_management(action="control", device_id="midea_portasplit_demo", power=True, setpoint=21)
            await climate_management(action="scenario", device_id="midea_portasplit_demo", scenario="heatwave")
        """
        try:
            if action == "list":
                units = await midea_manager.list_units()
                for unit in units:
                    await unit.status()
                return build_success_response(
                    operation="climate_list",
                    summary=f"{len(units)} climate unit(s)",
                    result={"devices": [u.to_dict() for u in units]},
                )

            if action == "discover":
                found = await midea_manager.discover(max(1, min(timeout_s, 30)))
                return build_success_response(
                    operation="climate_discover",
                    summary=f"{len(found)} Midea unit(s) found on the LAN",
                    result={"devices": found},
                    next_steps=["Put host and device_id into climate.midea.devices and set mock: false"]
                    if found
                    else [],
                )

            if not device_id:
                return _err(f"{action} needs device_id (see list)")
            unit = await midea_manager.get_unit(device_id)
            if unit is None:
                return _err(f"Unknown climate device '{device_id}' (see list)", "device_not_found")

            if action == "status":
                state = await unit.status()
                d = unit.to_dict()
                online = "online" if state.online else f"OFFLINE ({state.last_error or 'no answer'})"
                return build_success_response(
                    operation="climate_status",
                    summary=f"{unit.name}: {d['room_temp_c']} C room, mode {d['mode']}, {online}, mock={unit.mock}",
                    result=d,
                )

            if action == "scenario":
                if not scenario:
                    return _err(f"scenario needs one of {list(MOCK_SCENARIOS)}")
                await unit.apply_scenario(scenario)
                return build_success_response(
                    operation="climate_scenario", summary=f"{unit.name}: scenario '{scenario}'", result=unit.to_dict()
                )

            if action == "control":
                applied: list[str] = []
                if mode is not None and mode not in MIDEA_MODES:
                    return _err(f"Unknown mode '{mode}'. Use: {list(MIDEA_MODES)}")
                if fan_speed is not None and fan_speed not in MIDEA_FAN_SPEEDS:
                    return _err(f"Unknown fan '{fan_speed}'. Use: {list(MIDEA_FAN_SPEEDS)}")
                if power is not None:
                    await unit.set_power(power)
                    applied.append(f"power={power}")
                if mode is not None:
                    await unit.set_mode(mode)
                    applied.append(f"mode={mode}")
                if setpoint is not None:
                    await unit.set_setpoint(setpoint)
                    applied.append(f"setpoint={setpoint}")
                if fan_speed is not None:
                    await unit.set_fan(fan_speed)
                    applied.append(f"fan={fan_speed}")
                if swing is not None:
                    await unit.set_swing(swing)
                    applied.append(f"swing={swing}")
                for name, value in (("eco", eco), ("turbo", turbo), ("sleep", sleep)):
                    if value is not None:
                        await unit.set_flag(name, value)
                        applied.append(f"{name}={value}")
                if not applied:
                    return _err("control needs at least one of power/mode/setpoint/fan_speed/swing/eco/turbo/sleep")
                return build_success_response(
                    operation="climate_control",
                    summary=f"{unit.name}: applied {', '.join(applied)}",
                    result=unit.to_dict(),
                )

            return _err(f"Unknown action '{action}'")

        except MideaError as e:
            return _err(str(e), e.error_type, e.suggestions)
        except ValueError as e:
            return _err(str(e))
        except Exception as e:
            logger.exception("climate_management failed:")
            return _err(f"climate_management failed: {e}", "unexpected")
