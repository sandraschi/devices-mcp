# Midea PortaSplit (mock device now, real backend ready for the unit)

**Status**: the whole surface (MCP tool, REST, UI, tests) runs against a simulated unit. The real
LAN backend is written against [msmart-ng](https://github.com/mill1000/midea-msmart) but has **never
talked to a physical PortaSplit**.

## Verification status

| Piece | Status |
|---|---|
| Mock physics, scenarios, REST, MCP tool, Climate page | Tested; UI checked in a browser (scenarios, offline lockout, fault, filter alert, reset). |
| msmart-ng adapter (`MsmartBackend`) | Field mapping and error handling tested against a fake `AirConditioner`. A test checks every msmart-ng name the adapter touches exists in the real library (msmart-ng 2026.9.0). Wire protocol, V3 authentication and PortaSplit-specific behaviour are untested. |
| `discover` | Written, untested. |
| Power (W) and energy (kWh) from the real unit | Assumed units, unverified. They are only reported when the unit offers them; otherwise `null`. |

## What the mock does

- Wall-clock physics: room temperature moves toward the setpoint only while the unit is actually
  conditioning (cooling stops at or below the setpoint, heating at or above); otherwise it drifts toward the
  outdoor temperature at 0.05 C/min. Conditioning runs at 0.5 C/min, x1.6 turbo, x0.7 eco, x0.5 sleep.
- Power: cool 900 W, heat 1000 W, dry 300 W, fan 50 W, compressor idle 50 W, off 1 W (turbo x1.3, eco x0.8,
  sleep x0.7). Energy integrates the time actually spent conditioning.
- Humidity, outdoor temperature, filter-alert after 250 run-hours, eco/turbo exclusive.
- Scenarios (mock units only): `heatwave`, `cold_snap`, `offline`, `online`, `fault`, `clear_fault`,
  `filter_alert`, `reset`. An offline mock refuses control with `device_offline`, like a real unit.
- Every unit dict carries `mock: true/false`.

## Interfaces

- MCP `climate_management`: `list | status | control | discover | scenario`.
- REST: `GET /api/climate`, `GET /api/climate/discover`, `GET /api/climate/{id}`,
  `POST /api/climate/{id}/control`, `POST /api/climate/{id}/mock`. Errors are
  `detail = {error, error_type, suggestions}` (503 offline/dependency, 502 connect/command, 422 unsupported).
- UI: Climate page (sidebar), polls every 5 s, shows offline/fault/filter badges and a mock scenario panel.

## Flipping to the real unit (when it arrives)

1. `uv pip install -e ".[climate]"` (installs `msmart-ng`).
2. Put the unit on the LAN (not a guest VLAN), then `climate_management action=discover` to get `host` and
   `device_id`.
3. In `config.yaml`: `climate.midea.mock: false`, the unit under `devices`, a SmartHome or NetHome Plus
   `account` and `region` (V3 devices fetch their token and key from the cloud once).
4. `climate_management action=status` should show `mock: false`, `online: true`. If it shows
   `last_error`, that is the real reason.
5. Verify against the live unit: mode/setpoint/fan round trips, whether swing, eco, turbo and the power and
   energy readings are real, and what `error_code` values the unit emits. Tell us what differs so the
   mapping in `MsmartBackend.snapshot()` can be corrected.

With `mock: false` and no devices configured the demo unit is **not** seeded: the list is empty and the log
says why, so a misconfigured real setup cannot look like it works.
