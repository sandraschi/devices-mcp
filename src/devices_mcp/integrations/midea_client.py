"""Midea PortaSplit integration: mock device now, real LAN backend ready for the unit.

Architecture mirrors the Tapo family: a unit class with a backend seam, a manager for
discovery/config, and a portmanteau + REST + UI on top.

Backends:

* **Mock** (default, ``climate.midea.mock: true``): simulated physics on the wall clock.
  Room temperature moves toward the setpoint only while the unit is actually conditioning
  (cooling stops once the room is at or below the setpoint, heating at or above), drifts
  toward the outdoor temperature otherwise, energy accumulates, and humidity follows the
  mode. Mock-only *scenarios* (heatwave, cold snap, offline, fault, filter alert) exist so
  every UI state can be exercised without hardware. Every mock response says ``mock: true``.
* **Real** (``mock: false``): the Midea LAN protocol through ``msmart-ng`` (optional extra:
  ``uv pip install -e ".[climate]"``). V3 devices need one cloud login (SmartHome / NetHome
  Plus account) to fetch the token and key; control is then local. **UNVERIFIED against a
  physical PortaSplit**: the adapter is tested against a fake ``AirConditioner`` that follows
  msmart-ng's API, which proves the field mapping and error handling, not the wire protocol.

Anything the real backend cannot do fails with a typed :class:`MideaError`; it never falls
back to simulated values.

PortaSplit specifics: portable split unit, cool/heat/dry/fan/auto modes, setpoint 16-30 C.
Mock power envelope: cool ~900 W, heat ~1000 W, dry ~300 W, fan ~50 W, standby ~1 W.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MIDEA_MODES = ("off", "cool", "heat", "dry", "fan", "auto")
MIDEA_FAN_SPEEDS = ("auto", "low", "medium", "high", "turbo")
MIDEA_SETPOINT_MIN = 16.0
MIDEA_SETPOINT_MAX = 30.0
MOCK_SCENARIOS = ("heatwave", "cold_snap", "offline", "online", "fault", "clear_fault", "filter_alert", "reset")

_MOCK_POWER_W = {"cool": 900.0, "heat": 1000.0, "dry": 300.0, "fan": 50.0, "auto": 700.0}
_MOCK_IDLE_W = 50.0  # indoor fan only: compressor idle because the room is at setpoint
_MOCK_RATE_C_PER_MIN = 0.5
_MOCK_DRIFT_C_PER_MIN = 0.05
_MOCK_FILTER_ALERT_HOURS = 250.0
_MOCK_FAULT_CODE = 3  # arbitrary: Midea error-code meanings are model specific
_MAX_ADVANCE_S = 6 * 3600.0  # never integrate more than 6 h in one step (e.g. after a long idle)


class MideaError(RuntimeError):
    """A climate operation failed. ``error_type`` is stable and machine-readable."""

    def __init__(self, message: str, error_type: str = "device_error", suggestions: list[str] | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.suggestions = suggestions or []


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
    power_w: float | None = 1.0
    mock: bool = True
    last_update: float = field(default_factory=time.time)
    online: bool = True
    outdoor_temp_c: float | None = None
    humidity_pct: float | None = None
    eco: bool = False
    turbo: bool = False
    sleep: bool = False
    error_code: int = 0
    filter_alert: bool = False
    energy_kwh: float | None = 0.0
    scenario: str = ""
    last_error: str = ""


# --- real backend (msmart-ng) -------------------------------------------------------------

_MODE_TO_MSMART = {"auto": "AUTO", "cool": "COOL", "dry": "DRY", "heat": "HEAT", "fan": "FAN_ONLY"}
_MSMART_TO_MODE = {"AUTO": "auto", "COOL": "cool", "DRY": "dry", "HEAT": "heat", "FAN_ONLY": "fan", "SMART_DRY": "dry"}
_FAN_TO_MSMART = {"auto": "AUTO", "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "turbo": "MAX"}
_MSMART_TO_FAN = {"AUTO": "auto", "SILENT": "low", "LOW": "low", "MEDIUM": "medium", "HIGH": "high", "MAX": "turbo"}
_SWING_PREFERENCE = ("VERTICAL", "HORIZONTAL", "BOTH")

DeviceFactory = Callable[[], Awaitable[Any]]


def _enum_name(value: Any) -> str:
    return str(getattr(value, "name", value))


def _fan_from_msmart(value: Any) -> str:
    name = _enum_name(value)
    if name in _MSMART_TO_FAN:
        return _MSMART_TO_FAN[name]
    try:  # a custom numeric speed: bucket it
        n = int(value)
    except (TypeError, ValueError):
        return "auto"
    return "low" if n <= 50 else "medium" if n <= 70 else "high" if n <= 90 else "turbo"


class MsmartBackend:
    """Adapter from msmart-ng's ``AirConditioner`` to :class:`MideaACState` fields.

    UNVERIFIED against hardware. ``device_factory`` is the test seam: it returns an object with
    msmart-ng's ``AirConditioner`` surface; by default it discovers the device on the LAN.
    """

    def __init__(
        self,
        host: str,
        *,
        account: str | None = None,
        password: str | None = None,
        region: str = "DE",
        device_factory: DeviceFactory | None = None,
    ) -> None:
        self.host = host
        self._account = account
        self._password = password
        self._region = region
        self._factory = device_factory or self._discover
        self._ac: Any = None

    async def _discover(self) -> Any:
        try:
            from msmart.discover import Discover  # type: ignore[import-not-found]
        except ImportError as exc:
            raise MideaError(
                "msmart-ng is not installed",
                "dependency_missing",
                ['uv pip install -e ".[climate]"', "or set climate.midea.mock: true"],
            ) from exc
        if not self.host:
            raise MideaError("no host configured for this unit", "invalid_config", ["Set climate.midea.devices[].host"])
        try:
            return await Discover.discover_single(
                self.host,
                account=self._account,
                password=self._password,
                region=self._region,
                auto_connect=True,
            )
        except Exception as exc:  # CloudError, DiscoverError, OSError ...
            raise MideaError(
                f"could not reach the unit at {self.host}: {exc}",
                "connect_failed",
                [
                    "Is the unit powered and on the same network (not a guest VLAN)?",
                    "V3 devices need a SmartHome/NetHome Plus account for the one-time token fetch",
                ],
            ) from exc

    async def connect(self) -> None:
        if self._ac is not None:
            return
        ac = await self._factory()
        if ac is None:
            raise MideaError(
                f"no Midea device answered at {self.host}",
                "device_not_found",
                ["Check the IP address", "Run climate_management action=discover"],
            )
        if hasattr(ac, "enable_energy_usage_requests"):
            ac.enable_energy_usage_requests = True
        self._ac = ac
        if not getattr(ac, "online", True):
            self._ac = None
            raise MideaError(
                f"unit at {self.host} was found but did not authenticate or answer",
                "connect_failed",
                ["Check the SmartHome/NetHome Plus account and region", "Power-cycle the unit and retry"],
            )

    def drop(self) -> None:
        """Forget the connection so the next call re-discovers (after a network error)."""
        self._ac = None

    async def refresh(self) -> None:
        await self.connect()
        try:
            await self._ac.refresh()
        except Exception as exc:
            self.drop()
            raise MideaError(f"refresh failed: {exc}", "connect_failed") from exc

    @property
    def online(self) -> bool:
        return self._ac is not None and bool(getattr(self._ac, "online", True))

    def snapshot(self) -> dict[str, Any]:
        ac = self._ac
        power = bool(ac.power_state)
        mode = _MSMART_TO_MODE.get(_enum_name(ac.operational_mode), "auto") if power else "off"
        power_w = ac.get_real_time_power_usage() if hasattr(ac, "get_real_time_power_usage") else None
        total = ac.get_total_energy_usage() if hasattr(ac, "get_total_energy_usage") else None
        swing_off = _enum_name(getattr(ac, "swing_mode", "OFF")) == "OFF"
        return {
            "power": power,
            "mode": mode,
            "setpoint_c": float(ac.target_temperature) if ac.target_temperature is not None else None,
            "room_temp_c": float(ac.indoor_temperature) if ac.indoor_temperature is not None else None,
            "outdoor_temp_c": float(ac.outdoor_temperature) if ac.outdoor_temperature is not None else None,
            "fan_speed": _fan_from_msmart(ac.fan_speed),
            "swing": not swing_off,
            "power_w": float(power_w) if power_w is not None else None,
            "energy_kwh": float(total) if total is not None else None,
            "humidity_pct": float(ac.indoor_humidity) if getattr(ac, "indoor_humidity", None) is not None else None,
            "eco": bool(getattr(ac, "eco", False)),
            "turbo": bool(getattr(ac, "turbo", False)),
            "sleep": bool(getattr(ac, "sleep", False)),
            "error_code": int(getattr(ac, "error_code", 0) or 0),
            "filter_alert": bool(getattr(ac, "filter_alert", False)),
        }

    async def apply(self, **changes: Any) -> None:
        """Apply a subset of ``power/mode/setpoint_c/fan_speed/swing/eco/turbo/sleep`` and re-read state."""
        await self.connect()
        ac = self._ac
        try:
            if "mode" in changes:
                self._set_mode(ac, changes["mode"])
            if "power" in changes:
                ac.power_state = bool(changes["power"])
            if "setpoint_c" in changes:
                lo, hi = float(ac.min_target_temperature), float(ac.max_target_temperature)
                if not lo <= changes["setpoint_c"] <= hi:
                    raise MideaError(f"this unit accepts {lo}-{hi} C, not {changes['setpoint_c']}", "invalid_setpoint")
                ac.target_temperature = float(changes["setpoint_c"])
            if "fan_speed" in changes:
                ac.fan_speed = getattr(ac.FanSpeed, _FAN_TO_MSMART[changes["fan_speed"]])
            if "swing" in changes:
                self._set_swing(ac, bool(changes["swing"]))
            for flag in ("eco", "turbo"):
                if flag in changes:
                    if changes[flag] and not getattr(ac, f"supports_{flag}", True):
                        raise MideaError(f"this unit does not support {flag}", "unsupported")
                    setattr(ac, flag, bool(changes[flag]))
            if "sleep" in changes:
                ac.sleep = bool(changes["sleep"])
            await ac.apply()
        except MideaError:
            raise
        except Exception as exc:
            self.drop()
            raise MideaError(f"the unit rejected the command: {exc}", "command_failed") from exc
        await self.refresh()

    @staticmethod
    def _set_mode(ac: Any, mode: str) -> None:
        if mode == "off":
            ac.power_state = False
            return
        target = getattr(ac.OperationalMode, _MODE_TO_MSMART[mode])
        if target not in ac.supported_operation_modes:
            raise MideaError(f"this unit does not support mode '{mode}'", "unsupported")
        ac.operational_mode = target
        ac.power_state = True

    @staticmethod
    def _set_swing(ac: Any, on: bool) -> None:
        if not on:
            ac.swing_mode = ac.SwingMode.OFF
            return
        supported = {_enum_name(m) for m in ac.supported_swing_modes}
        for name in _SWING_PREFERENCE:
            if name in supported:
                ac.swing_mode = getattr(ac.SwingMode, name)
                return
        raise MideaError("this unit reports no swing mode", "unsupported")


async def discover_units(
    timeout_s: int = 5, account: str | None = None, password: str | None = None, region: str = "DE"
) -> list[dict[str, Any]]:
    """Broadcast-discover Midea air conditioners on the LAN. UNVERIFIED against hardware.

    Token and key are deliberately not returned: the backend fetches them itself when it connects.
    """
    try:
        from msmart.const import DeviceType  # type: ignore[import-not-found]
        from msmart.discover import Discover  # type: ignore[import-not-found]
    except ImportError as exc:
        raise MideaError(
            "msmart-ng is not installed", "dependency_missing", ['uv pip install -e ".[climate]"']
        ) from exc
    try:
        devices = await Discover.discover(
            timeout=timeout_s, account=account, password=password, region=region, auto_connect=False
        )
    except Exception as exc:
        raise MideaError(f"discovery failed: {exc}", "discovery_failed") from exc
    return [
        {"host": d.ip, "device_id": str(d.id), "name": d.name, "sn": d.sn, "protocol_version": d.version}
        for d in devices
        if d.type == DeviceType.AIR_CONDITIONER
    ]


# --- unit -----------------------------------------------------------------------------------


class MideaACUnit:
    """One PortaSplit unit: simulated physics (mock) or msmart-ng LAN control (real)."""

    def __init__(
        self,
        device_id: str,
        name: str,
        host: str = "",
        mock: bool = True,
        room_temp_c: float = 24.0,
        *,
        outdoor_temp_c: float = 28.0,
        account: str | None = None,
        password: str | None = None,
        region: str = "DE",
        backend: MsmartBackend | None = None,
    ) -> None:
        self.device_id = device_id
        self.name = name
        self.host = host
        self.mock = mock
        self._ambient_c = outdoor_temp_c
        self._runtime_h = 0.0
        self._state = MideaACState(
            device_id=device_id,
            name=name,
            host=host,
            room_temp_c=room_temp_c,
            mock=mock,
            outdoor_temp_c=outdoor_temp_c if mock else None,
            humidity_pct=55.0 if mock else None,
            power_w=1.0 if mock else None,
            energy_kwh=0.0 if mock else None,
        )
        self._backend = backend or (
            None if mock else MsmartBackend(host, account=account, password=password, region=region)
        )

    # -- connection ----------------------------------------------------------------------
    async def connect(self) -> bool:
        """Mock: always true. Real: LAN handshake via msmart-ng; raises :class:`MideaError`."""
        if self.mock:
            return True
        assert self._backend is not None
        await self._backend.connect()
        return True

    # -- mock physics --------------------------------------------------------------------
    @staticmethod
    def _direction(st: MideaACState) -> float:
        """+1 heating, -1 cooling, 0 idle: a unit only conditions while the room is on the wrong side of setpoint."""
        if not st.power:
            return 0.0
        gap = st.setpoint_c - st.room_temp_c
        if st.mode in ("cool", "dry") and gap < 0:
            return -1.0
        if st.mode == "heat" and gap > 0:
            return 1.0
        if st.mode == "auto" and gap != 0:
            return 1.0 if gap > 0 else -1.0
        return 0.0

    @staticmethod
    def _power_for(st: MideaACState, conditioning: bool) -> float:
        if not st.power:
            return 1.0
        if st.mode == "fan":
            return _MOCK_POWER_W["fan"]
        if not conditioning:
            return _MOCK_IDLE_W
        factor = (1.3 if st.turbo else 1.0) * (0.8 if st.eco else 1.0) * (0.7 if st.sleep else 1.0)
        return round(_MOCK_POWER_W.get(st.mode, 700.0) * factor, 1)

    def _tick_mock(self, dt_s: float) -> None:
        """Advance the simulation by ``dt_s`` seconds (mock only)."""
        st = self._state
        now = time.time()
        if dt_s <= 0 or not st.online:
            if dt_s <= 0:
                st.power_w = self._power_for(st, bool(self._direction(st)))
            st.last_update = now
            return

        direction = self._direction(st)
        active_s = 0.0
        if direction:
            speed = (1.6 if st.turbo else 1.0) * (0.7 if st.eco else 1.0) * (0.5 if st.sleep else 1.0)
            full_step = _MOCK_RATE_C_PER_MIN * speed * dt_s / 60.0
            gap = abs(st.setpoint_c - st.room_temp_c)
            active_s = dt_s * min(1.0, gap / full_step)  # seconds actually spent conditioning
            st.room_temp_c = round(st.room_temp_c + direction * min(full_step, gap), 2)
        else:
            toward = self._ambient_c - st.room_temp_c
            drift = min(_MOCK_DRIFT_C_PER_MIN * dt_s / 60.0, abs(toward))
            st.room_temp_c = round(st.room_temp_c + (drift if toward > 0 else -drift), 2)

        active_w = self._power_for(st, True) if direction else 0.0
        idle_w = self._power_for(st, False)
        joules = active_w * active_s + idle_w * (dt_s - active_s)
        st.energy_kwh = round((st.energy_kwh or 0.0) + joules / 3_600_000.0, 5)
        st.power_w = self._power_for(st, bool(self._direction(st)))  # reading at the end of the step
        if st.power:
            self._runtime_h += dt_s / 3600.0
        st.filter_alert = st.filter_alert or self._runtime_h >= _MOCK_FILTER_ALERT_HOURS
        target_rh = 40.0 if st.mode == "dry" and st.power else 50.0 if st.mode == "cool" and st.power else 55.0
        rh = st.humidity_pct if st.humidity_pct is not None else 55.0
        max_step = 0.5 * dt_s / 60.0
        st.humidity_pct = round(rh + max(-max_step, min(max_step, target_rh - rh)), 1)
        st.last_update = now

    def _advance(self) -> None:
        """Bring the simulation up to the wall clock before reading or changing state."""
        if self.mock:
            self._tick_mock(min(time.time() - self._state.last_update, _MAX_ADVANCE_S))

    def _require_online(self) -> None:
        if self.mock and not self._state.online:
            raise MideaError(
                f"{self.name} is offline",
                "device_offline",
                ["Check the unit's power and Wi-Fi", "Mock units: apply scenario 'online'"],
            )

    # -- real-state sync -----------------------------------------------------------------
    def _adopt(self, snap: dict[str, Any]) -> None:
        st = self._state
        for key, value in snap.items():
            if value is not None or key in ("power_w", "energy_kwh", "humidity_pct", "outdoor_temp_c"):
                setattr(st, key, value)
        st.online = True
        st.last_error = ""
        st.last_update = time.time()

    async def _apply(self, **changes: Any) -> MideaACState:
        assert self._backend is not None
        try:
            await self._backend.apply(**changes)
        except MideaError as exc:
            if exc.error_type in ("connect_failed", "device_not_found", "command_failed"):
                self._state.online = False
                self._state.last_error = str(exc)
            raise
        self._adopt(self._backend.snapshot())
        return self._state

    # -- control -------------------------------------------------------------------------
    async def set_power(self, on: bool) -> MideaACState:
        if not self.mock:
            return await self._apply(power=on)
        self._advance()
        self._require_online()
        st = self._state
        st.power = on
        if on and st.mode == "off":
            st.mode = "cool"
        if not on:
            st.mode = "off"
        self._tick_mock(0.0)
        logger.info("Midea %s power -> %s (mock)", self.device_id, on)
        return st

    async def set_mode(self, mode: str) -> MideaACState:
        if mode not in MIDEA_MODES:
            raise ValueError(f"Unknown mode '{mode}'. Use: {MIDEA_MODES}")
        if not self.mock:
            return await self._apply(mode=mode)
        self._advance()
        self._require_online()
        st = self._state
        st.mode = mode
        st.power = mode != "off"
        self._tick_mock(0.0)
        return st

    async def set_setpoint(self, temp_c: float) -> MideaACState:
        if not (MIDEA_SETPOINT_MIN <= temp_c <= MIDEA_SETPOINT_MAX):
            raise ValueError(f"Setpoint {temp_c} outside {MIDEA_SETPOINT_MIN}-{MIDEA_SETPOINT_MAX} C")
        if not self.mock:
            return await self._apply(setpoint_c=temp_c)
        self._advance()
        self._require_online()
        self._state.setpoint_c = temp_c
        self._tick_mock(0.0)
        return self._state

    async def set_fan(self, speed: str) -> MideaACState:
        if speed not in MIDEA_FAN_SPEEDS:
            raise ValueError(f"Unknown fan speed '{speed}'. Use: {MIDEA_FAN_SPEEDS}")
        if not self.mock:
            return await self._apply(fan_speed=speed)
        self._advance()
        self._require_online()
        self._state.fan_speed = speed
        return self._state

    async def set_swing(self, on: bool) -> MideaACState:
        if not self.mock:
            return await self._apply(swing=on)
        self._advance()
        self._require_online()
        self._state.swing = on
        return self._state

    async def set_flag(self, name: str, on: bool) -> MideaACState:
        """Toggle ``eco``, ``turbo`` or ``sleep``."""
        if name not in ("eco", "turbo", "sleep"):
            raise ValueError(f"Unknown flag '{name}'. Use: eco, turbo, sleep")
        if not self.mock:
            return await self._apply(**{name: on})
        self._advance()
        self._require_online()
        st = self._state
        setattr(st, name, on)
        if on and name == "turbo":
            st.eco = False  # the unit treats eco and turbo as exclusive
        if on and name == "eco":
            st.turbo = False
        self._tick_mock(0.0)
        return st

    async def status(self) -> MideaACState:
        if not self.mock:
            assert self._backend is not None
            try:
                await self._backend.refresh()
            except MideaError as exc:
                logger.warning("Midea %s status failed: %s", self.device_id, exc)
                self._state.online = False
                self._state.last_error = str(exc)
                self._state.last_update = time.time()
                return self._state
            self._adopt(self._backend.snapshot())
            return self._state
        self._advance()
        return self._state

    # -- mock scenarios ------------------------------------------------------------------
    async def apply_scenario(self, name: str) -> MideaACState:
        """Put the mock into a named situation so UI states can be exercised. Mock only."""
        if not self.mock:
            raise MideaError("scenarios exist only on mock units", "not_mock", ["Real units report real state"])
        if name not in MOCK_SCENARIOS:
            raise ValueError(f"Unknown scenario '{name}'. Use: {MOCK_SCENARIOS}")
        self._advance()
        st = self._state
        if name == "heatwave":
            self._ambient_c, st.room_temp_c, st.outdoor_temp_c = 35.0, 31.0, 35.0
        elif name == "cold_snap":
            self._ambient_c, st.room_temp_c, st.outdoor_temp_c = 3.0, 14.0, 3.0
        elif name == "offline":
            st.online = False
        elif name == "online":
            st.online = True
        elif name == "fault":
            st.error_code = _MOCK_FAULT_CODE
        elif name == "clear_fault":
            st.error_code = 0
        elif name == "filter_alert":
            self._runtime_h, st.filter_alert = _MOCK_FILTER_ALERT_HOURS, True
        elif name == "reset":
            st.power, st.mode, st.setpoint_c, st.room_temp_c = False, "off", 22.0, 24.0
            st.fan_speed, st.swing, st.eco, st.turbo, st.sleep = "auto", False, False, False, False
            st.error_code, st.filter_alert, st.online, st.energy_kwh = 0, False, True, 0.0
            self._ambient_c, st.outdoor_temp_c, self._runtime_h = 28.0, 28.0, 0.0
        st.scenario = name if name not in ("online", "clear_fault", "reset") else ""
        self._tick_mock(0.0)
        return st

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
            "online": st.online,
            "outdoor_temp_c": st.outdoor_temp_c,
            "humidity_pct": st.humidity_pct,
            "eco": st.eco,
            "turbo": st.turbo,
            "sleep": st.sleep,
            "error_code": st.error_code,
            "filter_alert": st.filter_alert,
            "energy_kwh": st.energy_kwh,
            "scenario": st.scenario,
            "last_error": st.last_error,
        }


def _real_credential(value: Any) -> str | None:
    """Config value, or None when empty or still the ``YOUR_...`` placeholder from the example file."""
    text = str(value or "").strip()
    return None if not text or text.startswith("YOUR_") else text


class MideaManager:
    """Owns configured Midea units (a demo mock unit is seeded only when mock mode is on)."""

    def __init__(self) -> None:
        self.units: dict[str, MideaACUnit] = {}
        self._initialized = False

    def _conf(self) -> dict[str, Any]:
        try:
            from devices_mcp.config import get_config

            return (get_config() or {}).get("climate", {}).get("midea", {}) or {}
        except Exception:
            logger.warning("Midea: could not read climate config", exc_info=True)
            return {}

    async def initialize(self) -> "MideaManager":
        if self._initialized:
            return self
        conf = self._conf()
        mock_default = bool(conf.get("mock", True))
        account = conf.get("account") or {}
        creds = {
            "account": _real_credential(account.get("username")),
            "password": _real_credential(account.get("password")),
            "region": str(conf.get("region", "DE")),
        }
        for dev in conf.get("devices", []) or []:
            unit = MideaACUnit(
                device_id=str(dev.get("device_id", dev.get("host", "midea_ac_1"))),
                name=str(dev.get("name", "PortaSplit")),
                host=str(dev.get("host", "")),
                mock=bool(dev.get("mock", mock_default)),
                room_temp_c=float(dev.get("room_temp_c", 24.0)),
                **creds,
            )
            self.units[unit.device_id] = unit
        if not self.units and mock_default:
            demo = MideaACUnit(device_id="midea_portasplit_demo", name="PortaSplit (demo)", host="", mock=True)
            self.units[demo.device_id] = demo
            logger.info("Midea: no units configured - serving demo mock unit")
        elif not self.units:
            logger.warning("Midea: mock is off but no devices are configured (climate.midea.devices)")
        self._initialized = True
        return self

    async def list_units(self) -> list[MideaACUnit]:
        await self.initialize()
        return list(self.units.values())

    async def get_unit(self, device_id: str) -> MideaACUnit | None:
        await self.initialize()
        return self.units.get(device_id)

    async def discover(self, timeout_s: int = 5) -> list[dict[str, Any]]:
        conf = self._conf()
        account = conf.get("account") or {}
        return await discover_units(
            timeout_s,
            account=_real_credential(account.get("username")),
            password=_real_credential(account.get("password")),
            region=str(conf.get("region", "DE")),
        )


midea_manager = MideaManager()
