"""Midea PortaSplit tests: mock physics, scenarios, the msmart-ng adapter, REST and the MCP tool.

The real-backend tests use a fake ``AirConditioner`` that mirrors msmart-ng's API. They prove the
field mapping and error handling. ``test_adapter_only_touches_real_msmart_api`` checks the fake
against the real library when it is installed, so the fake cannot drift from msmart-ng silently.
They do not prove the wire protocol works against a physical PortaSplit.
"""

import time
from enum import IntEnum

import pytest
from backend.routes import climate as climate_route
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastmcp import Client, FastMCP

from devices_mcp.integrations import midea_client as mc
from devices_mcp.tools.portmanteau.climate_management import register_climate_management_tool

# --- mock physics --------------------------------------------------------------------------


def _unit(**kw) -> mc.MideaACUnit:
    return mc.MideaACUnit(device_id="t", name="T", mock=True, **kw)


async def test_cooling_stops_at_setpoint_and_never_overshoots():
    u = _unit(room_temp_c=24.0)
    await u.set_setpoint(22.0)
    await u.set_power(True)
    u._tick_mock(3600.0)  # an hour is far more than the 2 C gap needs
    assert u._state.room_temp_c == 22.0
    assert u._state.power_w == 50.0, "compressor idles once the room is at setpoint"


async def test_cool_mode_does_not_keep_cooling_a_room_already_below_setpoint():
    # Regression: the old physics drove a 20 C room to 18 C with setpoint 22 in cool mode.
    u = _unit(room_temp_c=20.0, outdoor_temp_c=20.0)
    await u.set_setpoint(22.0)
    await u.set_power(True)
    u._tick_mock(600.0)
    assert u._state.room_temp_c >= 20.0


async def test_heat_mode_warms_only_when_below_setpoint():
    u = _unit(room_temp_c=15.0)
    await u.set_mode("heat")
    await u.set_setpoint(20.0)
    u._tick_mock(300.0)
    assert 15.0 < u._state.room_temp_c <= 20.0
    assert u._state.power_w == 1000.0


async def test_room_drifts_toward_outdoor_temperature_when_off():
    u = _unit(room_temp_c=24.0, outdoor_temp_c=34.0)
    u._tick_mock(1200.0)  # 20 min at 0.05 C/min
    assert u._state.room_temp_c == pytest.approx(25.0, abs=0.01)
    assert u._state.power_w == 1.0


async def test_turbo_cools_faster_and_draws_more_eco_the_opposite():
    async def run(flag=None):
        u = _unit(room_temp_c=30.0)
        await u.set_setpoint(20.0)
        await u.set_power(True)
        if flag:
            await u.set_flag(flag, True)
        u._tick_mock(300.0)
        return u._state

    base, turbo, eco = await run(), await run("turbo"), await run("eco")
    assert turbo.room_temp_c < base.room_temp_c < eco.room_temp_c
    assert turbo.power_w > base.power_w > eco.power_w


async def test_turbo_and_eco_are_exclusive():
    u = _unit()
    await u.set_flag("turbo", True)
    await u.set_flag("eco", True)
    assert (u._state.turbo, u._state.eco) == (False, True)


async def test_energy_accumulates_from_power_and_time():
    u = _unit(room_temp_c=30.0)
    await u.set_setpoint(16.0)
    await u.set_power(True)
    u._tick_mock(300.0)  # 2.5 C of a 14 C gap: conditioning for the whole five minutes
    assert u._state.energy_kwh == pytest.approx(0.075, rel=0.01)  # 900 W for 5 min


async def test_energy_counts_only_the_time_spent_conditioning():
    u = _unit(room_temp_c=23.0)
    await u.set_setpoint(22.0)
    await u.set_power(True)
    u._tick_mock(3600.0)  # needs 2 min of cooling for the 1 C gap, then idles for 58 min
    expected = (900 * 120 + 50 * 3480) / 3_600_000
    assert u._state.energy_kwh == pytest.approx(expected, rel=0.01)


async def test_status_advances_with_the_wall_clock_not_a_fixed_second():
    u = _unit(room_temp_c=30.0)
    await u.set_setpoint(16.0)
    await u.set_power(True)
    u._state.last_update = time.time() - 600  # pretend ten minutes passed
    await u.status()
    assert u._state.room_temp_c == pytest.approx(25.0, abs=0.05)


async def test_filter_alert_after_enough_runtime():
    u = _unit(room_temp_c=40.0)
    await u.set_setpoint(16.0)
    await u.set_power(True)
    u._runtime_h = mc._MOCK_FILTER_ALERT_HOURS - 0.01
    u._tick_mock(120.0)
    assert u._state.filter_alert is True


# --- scenarios -----------------------------------------------------------------------------


async def test_offline_scenario_blocks_control_like_a_real_unit_and_recovers():
    u = _unit()
    await u.apply_scenario("offline")
    assert u.to_dict()["online"] is False
    with pytest.raises(mc.MideaError) as exc:
        await u.set_power(True)
    assert exc.value.error_type == "device_offline"
    await u.apply_scenario("online")
    await u.set_power(True)
    assert u._state.power is True


async def test_fault_heatwave_and_reset_scenarios():
    u = _unit()
    await u.apply_scenario("fault")
    assert u._state.error_code != 0
    await u.apply_scenario("heatwave")
    assert u._state.room_temp_c == 31.0 and u._state.outdoor_temp_c == 35.0
    await u.set_power(True)
    await u.apply_scenario("reset")
    assert (u._state.power, u._state.error_code, u._state.room_temp_c) == (False, 0, 24.0)


async def test_unknown_scenario_and_scenarios_on_real_units_are_refused():
    with pytest.raises(ValueError):
        await _unit().apply_scenario("meteor")
    real = mc.MideaACUnit("r", "R", host="10.0.0.9", mock=False, backend=mc.MsmartBackend("10.0.0.9"))
    with pytest.raises(mc.MideaError) as exc:
        await real.apply_scenario("heatwave")
    assert exc.value.error_type == "not_mock"


# --- msmart-ng adapter ---------------------------------------------------------------------


class FakeAC:
    """Mirrors the slice of msmart-ng's AirConditioner the adapter uses."""

    class OperationalMode(IntEnum):
        AUTO = 1
        COOL = 2
        DRY = 3
        HEAT = 4
        FAN_ONLY = 5
        SMART_DRY = 6

    class FanSpeed(IntEnum):
        AUTO = 102
        MAX = 100
        HIGH = 80
        MEDIUM = 60
        LOW = 40
        SILENT = 20

    class SwingMode(IntEnum):
        OFF = 0
        VERTICAL = 0xC
        HORIZONTAL = 0x3
        BOTH = 0xF

    def __init__(self, *, swing=("OFF", "VERTICAL"), online=True, fail_apply=False):
        self.online = online
        self.fail_apply = fail_apply
        self.power_state = False
        self.operational_mode = self.OperationalMode.AUTO
        self.target_temperature = 22.0
        self.indoor_temperature = 26.5
        self.outdoor_temperature = 31.0
        self.fan_speed = self.FanSpeed.AUTO
        self.swing_mode = self.SwingMode.OFF
        self.eco = self.turbo = self.sleep = False
        self.supports_eco = True
        self.supports_turbo = False
        self.error_code = 0
        self.filter_alert = False
        self.indoor_humidity = 48
        self.min_target_temperature, self.max_target_temperature = 17.0, 30.0
        self.supported_operation_modes = [self.OperationalMode[n] for n in ("AUTO", "COOL", "DRY", "HEAT", "FAN_ONLY")]
        self.supported_swing_modes = [self.SwingMode[n] for n in swing]
        self.enable_energy_usage_requests = False
        self.applied = 0

    def get_real_time_power_usage(self):
        return 640.0 if self.power_state else 1.0

    def get_total_energy_usage(self):
        return 12.5

    async def refresh(self):
        return None

    async def apply(self):
        if self.fail_apply:
            raise OSError("socket closed")
        self.applied += 1


def _real_unit(ac: FakeAC | None) -> mc.MideaACUnit:
    async def factory():
        return ac

    backend = mc.MsmartBackend("10.0.0.9", device_factory=factory)
    return mc.MideaACUnit("r", "PortaSplit", host="10.0.0.9", mock=False, backend=backend)


async def test_real_status_maps_msmart_fields():
    ac = FakeAC()
    ac.power_state, ac.operational_mode, ac.fan_speed = True, ac.OperationalMode.HEAT, ac.FanSpeed.MAX
    st = await _real_unit(ac).status()
    assert (st.power, st.mode, st.fan_speed) == (True, "heat", "turbo")
    assert (st.room_temp_c, st.outdoor_temp_c, st.setpoint_c) == (26.5, 31.0, 22.0)
    assert (st.power_w, st.energy_kwh, st.humidity_pct, st.online, st.mock) == (640.0, 12.5, 48.0, True, False)
    assert ac.enable_energy_usage_requests is True


async def test_real_power_off_reports_mode_off():
    ac = FakeAC()
    ac.operational_mode = ac.OperationalMode.COOL
    st = await _real_unit(ac).status()
    assert (st.power, st.mode) == (False, "off")


async def test_real_control_sets_device_state_and_applies():
    ac = FakeAC()
    unit = _real_unit(ac)
    await unit.set_mode("cool")
    await unit.set_setpoint(21.5)
    await unit.set_fan("low")
    await unit.set_swing(True)
    await unit.set_flag("eco", True)
    assert (ac.power_state, ac.operational_mode, ac.target_temperature) == (True, ac.OperationalMode.COOL, 21.5)
    assert (ac.fan_speed, ac.swing_mode, ac.eco) == (ac.FanSpeed.LOW, ac.SwingMode.VERTICAL, True)
    assert ac.applied == 5
    await unit.set_power(False)
    assert ac.power_state is False


async def test_real_setpoint_outside_the_units_own_range_is_rejected():
    unit = _real_unit(FakeAC())  # this fake accepts 17-30; the global range allows 16
    with pytest.raises(mc.MideaError) as exc:
        await unit.set_setpoint(16.5)
    assert exc.value.error_type == "invalid_setpoint"


async def test_real_unsupported_features_fail_instead_of_silently_doing_nothing():
    unit = _real_unit(FakeAC(swing=("OFF",)))
    with pytest.raises(mc.MideaError) as swing_exc:
        await unit.set_swing(True)
    assert swing_exc.value.error_type == "unsupported"
    with pytest.raises(mc.MideaError) as turbo_exc:
        await unit.set_flag("turbo", True)  # fake: supports_turbo is False
    assert turbo_exc.value.error_type == "unsupported"


async def test_real_command_failure_marks_offline_with_reason_and_raises():
    unit = _real_unit(FakeAC(fail_apply=True))
    with pytest.raises(mc.MideaError) as exc:
        await unit.set_power(True)
    assert exc.value.error_type == "command_failed"
    assert unit.to_dict()["online"] is False and "socket closed" in unit.to_dict()["last_error"]


async def test_real_unit_not_found_reports_offline_not_mock_values():
    unit = _real_unit(None)
    st = await unit.status()
    assert st.online is False and "no Midea device answered" in st.last_error
    assert st.mock is False and st.power_w is None


async def test_real_unit_without_msmart_installed_says_so():
    try:
        import msmart  # noqa: F401
    except ImportError:
        unit = mc.MideaACUnit("r", "R", host="10.0.0.9", mock=False)
        with pytest.raises(mc.MideaError) as exc:
            await unit.connect()
        assert exc.value.error_type == "dependency_missing"
        assert "climate" in " ".join(exc.value.suggestions)
    else:
        pytest.skip("msmart-ng installed; connect would try the network")


def test_adapter_only_touches_real_msmart_api():
    msmart_device = pytest.importorskip("msmart.device")
    real = msmart_device.AirConditioner
    attrs = [
        "power_state", "operational_mode", "target_temperature", "indoor_temperature", "outdoor_temperature",
        "fan_speed", "swing_mode", "get_real_time_power_usage", "get_total_energy_usage", "indoor_humidity",
        "eco", "turbo", "sleep", "error_code", "filter_alert", "enable_energy_usage_requests", "online",
        "min_target_temperature", "max_target_temperature", "supported_operation_modes", "supported_swing_modes",
        "supports_eco", "supports_turbo", "refresh", "apply", "FanSpeed", "OperationalMode", "SwingMode",
    ]  # fmt: skip
    missing = [a for a in attrs if not hasattr(real, a)]
    assert not missing, f"adapter uses names msmart-ng does not have: {missing}"
    for enum, names in (
        (real.OperationalMode, ("AUTO", "COOL", "DRY", "HEAT", "FAN_ONLY", "SMART_DRY")),
        (real.FanSpeed, ("AUTO", "LOW", "MEDIUM", "HIGH", "MAX", "SILENT")),
        (real.SwingMode, ("OFF", "VERTICAL", "HORIZONTAL", "BOTH")),
    ):
        assert all(n in enum.__members__ for n in names)
    assert set(mc._MODE_TO_MSMART.values()) <= set(real.OperationalMode.__members__)
    assert set(mc._FAN_TO_MSMART.values()) <= set(real.FanSpeed.__members__)


# --- manager -------------------------------------------------------------------------------


async def test_manager_does_not_seed_a_demo_when_mock_is_off(monkeypatch):
    mgr = mc.MideaManager()
    monkeypatch.setattr(mgr, "_conf", lambda: {"mock": False})
    assert await mgr.list_units() == []


async def test_manager_builds_a_real_unit_from_config_and_ignores_placeholder_credentials(monkeypatch):
    mgr = mc.MideaManager()
    conf = {
        "mock": False,
        "region": "DE",
        "account": {"username": "YOUR_MSMARTHOME_EMAIL", "password": "secret"},
        "devices": [{"host": "10.0.0.9", "device_id": "ps1", "name": "PortaSplit"}],
    }
    monkeypatch.setattr(mgr, "_conf", lambda: conf)
    (unit,) = await mgr.list_units()
    assert unit.mock is False and unit._backend._account is None and unit._backend._password == "secret"


# --- REST ----------------------------------------------------------------------------------


@pytest.fixture
def api(monkeypatch):
    mgr = mc.MideaManager()
    monkeypatch.setattr(mgr, "_conf", lambda: {"mock": True})
    monkeypatch.setattr(climate_route, "midea_manager", mgr)
    app = FastAPI()
    app.include_router(climate_route.router)
    return TestClient(app)


def test_rest_list_control_and_scenario_roundtrip(api):
    listing = api.get("/api/climate").json()
    assert listing["mock"] is True and "heatwave" in listing["scenarios"]
    dev = listing["devices"][0]["device_id"]

    r = api.post(f"/api/climate/{dev}/control", json={"power": True, "setpoint": 21, "turbo": True, "sleep": True})
    body = r.json()
    assert r.status_code == 200 and (body["power"], body["turbo"], body["sleep"], body["setpoint_c"]) == (
        True,
        True,
        True,
        21.0,
    )

    r = api.post(f"/api/climate/{dev}/mock", json={"scenario": "offline"})
    assert r.json()["online"] is False
    blocked = api.post(f"/api/climate/{dev}/control", json={"power": False})
    assert blocked.status_code == 503 and blocked.json()["detail"]["error_type"] == "device_offline"


def test_rest_validation_and_unknown_unit(api):
    dev = api.get("/api/climate").json()["devices"][0]["device_id"]
    assert api.post(f"/api/climate/{dev}/control", json={"setpoint": 99}).status_code == 400
    assert api.post(f"/api/climate/{dev}/control", json={"mode": "turbojet"}).status_code == 400
    assert api.post(f"/api/climate/{dev}/mock", json={"scenario": "meteor"}).status_code == 400
    assert api.get("/api/climate/nope").status_code == 404


def test_rest_discover_without_msmart_is_a_clear_503(api):
    try:
        import msmart  # noqa: F401
    except ImportError:
        r = api.get("/api/climate/discover")
        assert r.status_code == 503 and r.json()["detail"]["error_type"] == "dependency_missing"
    else:
        pytest.skip("msmart-ng installed; discovery would scan the network")


# --- MCP tool ------------------------------------------------------------------------------


async def _call(**args):
    mcp = FastMCP("climate-test")
    register_climate_management_tool(mcp)
    async with Client(mcp) as client:
        result = await client.call_tool("climate_management", args, raise_on_error=False)
        return result.structured_content or result.data


async def test_tool_control_and_status_on_the_demo_unit():
    out = await _call(action="control", device_id="midea_portasplit_demo", power=True, setpoint=20.0, eco=True)
    assert out["success"] is True and out["result"]["eco"] is True and out["result"]["mock"] is True
    status = await _call(action="status", device_id="midea_portasplit_demo")
    assert status["success"] is True and status["result"]["online"] is True
    await _call(action="scenario", device_id="midea_portasplit_demo", scenario="reset")


async def test_tool_errors_are_typed():
    out = await _call(action="control", device_id="midea_portasplit_demo", mode="turbojet")
    assert out["success"] is False and out["error_type"] == "invalid_request"
    assert (await _call(action="status", device_id="nope"))["error_type"] == "device_not_found"
    assert (await _call(action="control", device_id="midea_portasplit_demo"))["success"] is False
