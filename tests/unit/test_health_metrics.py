"""Tests for personal health metrics storage (TimeSeriesDB health_metrics)."""

import pytest

from devices_mcp.db.timeseries import TimeSeriesDB


@pytest.fixture()
def db(tmp_path):
    return TimeSeriesDB(db_path=tmp_path / "health_test.db")


def test_store_and_list_weight(db):
    rid = db.store_health_metric("weight_kg", 72.5, "kg", "manual", "")
    assert rid > 0
    rows = db.get_health_history(metric="weight_kg", days=7)
    assert len(rows) == 1
    assert rows[0]["value"] == 72.5
    assert rows[0]["unit"] == "kg"


def test_trends_math(db):
    db.store_health_metric("sys_mmhg", 120, "mmHg")
    db.store_health_metric("sys_mmhg", 130, "mmHg")
    rows = db.get_health_history(metric="sys_mmhg", days=7)
    vals = [r["value"] for r in rows]
    assert vals == [120, 130]
    assert min(vals) == 120
    assert max(vals) == 130


def test_delete_metric(db):
    rid = db.store_health_metric("glucose_mgdl", 95, "mg/dL")
    assert db.delete_health_metric(rid) is True
    assert db.get_health_history(metric="glucose_mgdl", days=7) == []
    assert db.delete_health_metric(999999) is False


def test_health_table_coexists_with_energy(db):
    db.store_health_metric("weight_kg", 70.0, "kg")
    db.store_health_metric("pulse_bpm", 62, "bpm")
    rows = db.get_health_history(days=7)
    assert {r["metric"] for r in rows} == {"weight_kg", "pulse_bpm"}
