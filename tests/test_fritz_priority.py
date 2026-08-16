"""Tests for Fritz priority incident aggregation."""

from devices_mcp.integrations.fritz_priority import (
    _nest_incidents,
    _ring_incidents,
    _shelly_incidents,
    _urgency_for_temp,
)


def test_kitchen_50c_high_urgency():
    u = _urgency_for_temp(
        {
            "name": "kitchen probe",
            "temperature_c": 50.0,
            "alert_active": True,
        }
    )
    assert u >= 9.0


def test_shelly_threshold_alert():
    incidents = _shelly_incidents(
        [
            {
                "id": "fridge",
                "name": "Freezer",
                "temperature_c": 12.0,
                "high_threshold_c": 8.0,
                "low_threshold_c": -5.0,
                "alert_active": True,
            }
        ]
    )
    assert len(incidents) == 1
    assert incidents[0]["kind"] == "temperature"
    assert incidents[0]["urgency"] >= 8.0


def test_nest_co_emergency():
    incidents = _nest_incidents(
        [
            {
                "entity_id": "binary_sensor.kitchen_co",
                "name": "Kitchen Nest",
                "location": "Kitchen",
                "co_status": "emergency",
                "smoke_status": "idle",
            }
        ]
    )
    assert len(incidents) == 1
    assert incidents[0]["kind"] == "co_alarm"
    assert incidents[0]["urgency"] == 10.0
    assert incidents[0]["critical"] is True


def test_ring_intrusion_event():
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    incidents = _ring_incidents(
        [
            {
                "id": "evt-1",
                "event_type": "motion",
                "device_name": "Back door",
                "timestamp": now,
            }
        ],
        minutes=60,
    )
    assert len(incidents) == 1
    assert incidents[0]["kind"] == "burglar_alarm"
