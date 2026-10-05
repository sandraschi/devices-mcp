"""Tests for the Midea mock unit (physics + validation, no hardware)."""

import pytest

from devices_mcp.integrations.midea_client import MideaACUnit, MideaManager


@pytest.fixture()
def unit():
    return MideaACUnit(device_id="test_ac", name="Test", host="", mock=True, room_temp_c=28.0)


@pytest.mark.asyncio()
async def test_mock_power_and_physics(unit):
    await unit.set_power(True)
    assert unit._state.power is True
    assert unit._state.mode == "cool"
    before = unit._state.room_temp_c
    unit._tick_mock(600.0)  # 10 simulated minutes
    assert unit._state.room_temp_c < before  # cooling drives temp down
    assert unit._state.power_w == 900.0


@pytest.mark.asyncio()
async def test_mock_setpoint_validation(unit):
    with pytest.raises(ValueError):
        await unit.set_setpoint(35.0)
    with pytest.raises(ValueError):
        await unit.set_mode("turbojet")
    await unit.set_setpoint(21.5)
    assert unit._state.setpoint_c == 21.5


@pytest.mark.asyncio()
async def test_mock_to_dict_shape(unit):
    d = unit.to_dict()
    assert d["mock"] is True
    for key in ("device_id", "power", "mode", "setpoint_c", "room_temp_c", "power_w"):
        assert key in d


@pytest.mark.asyncio()
async def test_manager_seeds_demo():
    mgr = MideaManager()
    units = await mgr.list_units()
    assert len(units) >= 1
    assert all(u.mock for u in units)


# The real-backend refusal test moved to test_midea_portasplit.py: a real unit now raises a typed
# MideaError (dependency_missing / connect_failed) instead of NotImplementedError.
