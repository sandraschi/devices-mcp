# Midea PortaSplit (mock-first, hardware in winter)

**Status**: family built, serving demo mock unit. Flip to real in winter.

## Why mock-first

The unit arrives in winter when prices drop. The whole surface (MCP tool,
REST, UI, tests) is done and green against simulation, so winter work is only
the LAN handshake + verification, not new architecture.

## What's live now

- `src/devices_mcp/integrations/midea_client.py` — `MideaACUnit` (mock physics:
  room temp drifts ~0.5 C/min toward setpoint when on; power by mode:
  cool 900 W / heat 1000 W / dry 300 W / fan 50 W / standby 1 W) + `MideaManager`
  (config units, else always-on demo unit `midea_portasplit_demo`).
- MCP `climate_management`: `status | control | list`
  (power/mode/setpoint 16-30/fan/swing, validated).
- REST `/api/climate` (list), `/api/climate/{id}` (status),
  `/api/climate/{id}/control`.
- Climate page (sidebar) with MOCK banner + badges until real hardware.
- Tests: `tests/unit/test_midea_mock.py` (physics, validation, demo seed,
  real-backend refusal).

## Winter flip checklist

1. `pip install midea-beautiful-air` (new dependency, deliberately not yet added).
2. MSmartHome account in `climate.midea.account` (config + example already
   scaffolded) for the one-time V3 token/key handshake.
3. Implement the real backend in `MideaACUnit.connect()` (currently raises a
   clear `NotImplementedError` telling exactly this) + status/control mapping.
4. Set `mock: false` on the real unit; keep or remove the demo.
5. Verify against live: status fields, control round-trip, supervisor health entry.
