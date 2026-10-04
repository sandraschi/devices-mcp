# Personal health devices (Withings-first plan)

**Status**: manual entry + trends live. Withings OAuth scaffolded (client +
routes + supervisor hook written, awaiting first real authorization).
FTMS BLE later (needs user-session helper, same pattern as USB camera).

## Device picks (integration-first, all Amazon.at/idealo.at)

- **Scale: Withings Body Smart (~EUR 90)** — WiFi auto-sync, open OAuth2 API.
- **BP: Withings BPM Connect (from ~EUR 100)** — same API/account: one
  integration covers scale + BP. Upper arm, validated.
- **Glucose pinprick: Accu-Chek Guide (~EUR 20 + strips ~EUR 37/100).**
  No pinprick meter on the market has an open API — this one integrates via
  manual entry (mySugr/Apple Health on the phone as backup). If full automation
  becomes mandatory, the honest alternative is a CGM (FreeStyle Libre) +
  Nightscout-style bridge, not a pinprick meter.
- **Cardio: FTMS Bluetooth only.** Zwift-/Kinomap-compatible label = FTMS.
  Kingsmith walking pads (Z1 ~EUR 300, A1 Pro ~EUR 379, KS Fit app) or a smart
  minibike (YOSUDA/Sunny BT) work via app + manual entry; true live metrics
  need FTMS. A dumb magnetic minibike (~EUR 40-60) + manual entries beats a
  fake-smart one.

## What's live now

- `health_metrics` table (`TimeSeriesDB`): weight_kg, sys/dia_mmhg, pulse_bpm,
  glucose_mgdl (mmol/L accepted, converted), workout_* (min/km/kcal/avgbpm),
  with source (manual/withings/ftms) + notes.
- MCP `health_management`: log_weight/log_bp/log_glucose/log_workout/trends/list/delete.
- REST `/api/wellness/*` (log, bp, workout, trends, list, delete).
- Human Health page: latest-values hero, 4 entry cards, recent list + delete.

## Withings OAuth (next)

1. Free dev app at developer.withings.com -> `health.withings` client_id/secret
   (+ redirect `http://127.0.0.1:10717/api/wellness/withings/callback`).
2. Human Health Withings card: Connect -> approve -> callback exchanges tokens
   (`~/.config/devices-mcp/withings_token.json`, gitignored).
3. `POST /api/wellness/withings/sync` pulls weight + BP (source='withings');
   supervisor re-syncs every 15 min automatically.
4. Scopes used: `userinfo,user.metrics`. Measure types: 1 weight, 9/10/11 BP/pulse.

## FTMS later

`bleak` BLE central + FTMS (0x1826) parser for live bike/belt metrics during
workouts. Caveat: Windows BLE from the LocalSystem service is restricted, so
live capture runs through the `:10715` user-session helper. Post-workout totals
stay available as manual entries regardless.
