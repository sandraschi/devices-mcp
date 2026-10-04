"""Midea PortaSplit integration (mock-first, real hardware in winter).

Architecture mirrors the Tapo family: a unit class with a backend seam, a
manager for discovery/config, and a portmanteau + REST + UI on top.

Backends:
- Mock (default, ``climate.midea.mock: true``): simulated physics - room temp
  drifts toward the setpoint when powered, power draw follows the mode. The
  whole UI/API surface is testable with zero hardware. Every mock response is
  labelled ``mock: true`` (fleet mock standard).
- Real (winter): Midea LAN protocol via the ``midea-beautiful-air`` package
  (pip install at that point; NOT a dependency yet on purpose). One-time cloud
  handshake for the V3 token/key from MSmartHome creds, then local control.
  Until then, ``connect()`` on a non-mock unit raises a clear error telling
  exactly what is missing - never a silent fake.

PortaSplit specifics: portable split unit (no outdoor mounting), cool/heat/dry/
fan/auto modes, setpoint 16-30 C. Power envelope (mock): cool ~900 W,
heat ~1000 W, dry ~300 W, fan ~50 W, standby ~1 W.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MIDEA_MODES = ("off", "cool", "heat", "dry", "fan", "auto")
MIDEA_FAN_SPEEDS = ("auto", "low", "medium", "high", "turbo")
MIDEA_SETPOINT_MIN = 16.0
MIDEA_SETPOINT_MAX = 30.0

_MOCK_POWER_W = {"cool": 900.0, "heat": 1000.0, "dry": 300.0, "fan": 50.0, "auto": 700.0}


@dataclass
class MideaACState:
    """Live state snapshot of one unit (mock or real)."""

    device_id: str
    name: str
    host: str
    power: bool = False
    mode: str = "off"
    setpoint_c: float = 22.0
    room_temp_c: float = 24.0
    fan_speed: str = "auto"
    swing: bool = False
    power_w: float = 1.0
    mock: bool = True
    last_update: float = field(default_factory=time.time)


class MideaACUnit:
    """One PortaSplit unit. Mock physics until winter hardware arrives."""

    def __init__(
        self,
        device_id: str,
        name: str,
        host: str = "",
        mock: bool = True,
        room_temp_c: float = 24.0,
    ) -> None:
        self.device_id = device_id
        self.name = name
        self.host = host
        self.mock = mock
        self._state = MideaACState(device_id=device_id, name=name, host=host, room_temp_c=room_temp_c, mock=mock)

    # -- connection -----------------------------------------------------
    async def connect(self) -> bool:
        """Connect (mock: always true; real: LAN handshake, see winter note)."""
        if self.mock:
            return True
        raise NotImplementedError(
            "Real Midea LAN backend not wired yet (winter): pip install "
            "midea-beautiful-air, set climate.midea.mock=false, provide MSmartHome "
            "account for the one-time V3 token/key handshake."
        )

    # -- mock physics ---------------------------------------------------
    def _tick_mock(self, dt_s: float) -> None:
        """Advance simulated room temperature toward the setpoint."""
        st = self._state
        if st.power and st.mode in ("cool", "heat", "dry", "auto"):
            direction = -1.0 if st.mode in ("cool", "dry") else 1.0
            if st.mode == "auto":
                direction = 1.0 if st.room_temp_c < st.setpoint_c else -1.0
            # ~0.5 C per minute toward setpoint, never overshooting.
            step = direction * min(0.5 * dt_s / 60.0, abs(st.setpoint_c - st.room_temp_c))
            st.room_temp_c = round(st.room_temp_c + step, 2)
            st.power_w = _MOCK_POWER_W.get(st.mode, 700.0)
        elif st.power and st.mode == "fan":
            st.power_w = _MOCK_POWER_W["fan"]
        else:
            st.power_w = 1.0
        st.last_update = time.time()

    # -- control --------------------------------------------------------
    async def set_power(self, on: bool) -> MideaACState:
        if not self.mock:
            await self.connect()
        st = self._state
        st.power = on
        if on and st.mode == "off":
            st.mode = "cool"
        if not on:
            st.mode = "off"
        self._tick_mock(0.0)
        logger.info("Midea %s power -> %s (mock=%s)", self.device_id, on, self.mock)
        return st

    async def set_mode(self, mode: str) -> MideaACState:
        if mode not in MIDEA_MODES:
            raise ValueError(f"Unknown mode '{mode}'. Use: {MIDEA_MODES}")
        if not self.mock:
            await self.connect()
        st = self._state
        st.mode = mode
        st.power = mode != "off"
        self._tick_mock(0.0)
        return st

    async def set_setpoint(self, temp_c: float) -> MideaACState:
        if not (MIDEA_SETPOINT_MIN <= temp_c <= MIDEA_SETPOINT_MAX):
            raise ValueError(f"Setpoint {temp_c} outside {MIDEA_SETPOINT_MIN}-{MIDEA_SETPOINT_MAX} C")
        if not self.mock:
            await self.connect()
        self._state.setpoint_c = temp_c
        self._tick_mock(0.0)
        return self._state

    async def set_fan(self, speed: str) -> MideaACState:
        if speed not in MIDEA_FAN_SPEEDS:
            raise ValueError(f"Unknown fan speed '{speed}'. Use: {MIDEA_FAN_SPEEDS}")
        if not self.mock:
            await self.connect()
        self._state.fan_speed = speed
        return self._state

    async def set_swing(self, on: bool) -> MideaACState:
        if not self.mock:
            await self.connect()
        self._state.swing = on
        return self._state

    async def status(self) -> MideaACState:
        if not self.mock:
            await self.connect()
        self._tick_mock(1.0)
        return self._state

    def to_dict(self) -> dict[str, Any]:
        st = self._state
        return {
            "device_id": st.device_id,
            "name": st.name,
            "host": st.host,
            "power": st.power,
            "mode": st.mode,
            "setpoint_c": st.setpoint_c,
            "room_temp_c": st.room_temp_c,
            "fan_speed": st.fan_speed,
            "swing": st.swing,
            "power_w": st.power_w,
            "mock": st.mock,
            "last_update": st.last_update,
        }


class MideaManager:
    """Owns configured + swept Midea units (mock unit seeded by default)."""

    def __init__(self) -> None:
        self.units: dict[str, MideaACUnit] = {}
        self._initialized = False

    def _conf(self) -> dict[str, Any]:
        try:
            from devices_mcp.config import get_config

            return (get_config() or {}).get("climate", {}).get("midea", {}) or {}
        except Exception:
            return {}

    async def initialize(self) -> "MideaManager":
        if self._initialized:
            return self
        conf = self._conf()
        mock_default = bool(conf.get("mock", True))
        for dev in conf.get("devices", []) or []:
            unit = MideaACUnit(
                device_id=str(dev.get("device_id", dev.get("host", "midea_ac_1"))),
                name=str(dev.get("name", "PortaSplit")),
                host=str(dev.get("host", "")),
                mock=bool(dev.get("mock", mock_default)),
                room_temp_c=float(dev.get("room_temp_c", 24.0)),
            )
            self.units[unit.device_id] = unit
        if not self.units:
            # Always-on mock so the UI/API surface is exercisable with no config.
            demo = MideaACUnit(
                device_id="midea_portasplit_demo",
                name="PortaSplit (demo)",
                host="",
                mock=True,
            )
            self.units[demo.device_id] = demo
            logger.info("Midea: no units configured - serving demo mock unit")
        self._initialized = True
        return self

    async def list_units(self) -> list[MideaACUnit]:
        await self.initialize()
        return list(self.units.values())

    async def get_unit(self, device_id: str) -> MideaACUnit | None:
        await self.initialize()
        return self.units.get(device_id)


midea_manager = MideaManager()
