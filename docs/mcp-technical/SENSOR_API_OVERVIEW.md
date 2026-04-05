# Sensor API Overview (2025-11-12)

The sensor API surfaces real device telemetry collected via the new ingestion
pipeline. Initial coverage focuses on TP-Link Tapo P115 smart plugs with
real-time power readings provided by `python-kasa`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/sensors/tapo-p115` | List all configured/available Tapo P115 plugs with the latest realtime metrics. |
| `GET`  | `/api/sensors/tapo-p115/{device_id}/history?hours=24` | Retrieve energy usage history (up to 7 days) for a specific plug. |

### Response Example (`GET /api/sensors/tapo-p115`)

```json
{
  "devices": [
    {
      "device_id": "tapo_p115_living_room_tv",
      "name": "Living Room TV Plug",
      "location": "Living Room",
      "device_model": "Tapo P115",
      "power_state": true,
      "current_power": 45.5,
      "voltage": 120.0,
      "current": 0.38,
      "daily_energy": 0.85,
      "monthly_energy": 25.5,
      "daily_cost": 0.102,
      "monthly_cost": 3.06,
      "last_seen": "2025-11-12T13:50:00Z",
      "host": "192.168.1.120"
    }
  ],
  "count": 1
}
```

> Values reflect real-time readings when available. Costs are computed using
> `energy.tapo_p115.electricity_rate` from `config.yaml`.

### Configuration

- Configure devices and credentials under `energy.tapo_p115` in `config.yaml`.
- Optional environment overrides: `TAPO_ACCOUNT_EMAIL`, `TAPO_ACCOUNT_PASSWORD`,
  `TAPO_P115_HOSTS`.
- The ingestion adapter relies on the `python-kasa` package. Install with
  `pip install python-kasa` on the node hosting `devices-mcp`.
