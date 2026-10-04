# Netatmo smoke + CO alarms (planned)

**Status**: extension scaffolded (`src/devices_mcp/integrations/netatmo_safety.py`),
unverified against real devices. Goes live on pairing day.

## Shopping list (confirmed 2026-10-04)

- Smoke: kitchen, living room, bedroom (Netatmo Smart Smoke Alarm).
- CO: 1x Netatmo Smart Carbon Monoxide Alarm near the suspect flue
  (downstairs boiler backdraft risk). If that alarm ever sounds: out of the
  flat, call 122 — the dashboard is visibility, not rescue.

## Why Netatmo, not Nest Protect

Protect smoke/CO is in no stable API (unofficial cookie flow dead since Google
killed OOB 2022; official SDM API excludes Protect). Netatmo alarms join the
existing Stroheckgasse home + the OAuth we already run: same app, no new
accounts, no hacks. Protects stay as screaming backup.

## Extension design

- pyatmo 8.1 models weather only, so the extension calls the raw API
  (`homesdata` modules + `getevents`) with our existing tokens (private httpx
  client, never the shared aiohttp session).
- Defensive parsing by rule: module/event type strings are NOT allow-listed.
  Known weather types are skipped; smoke/CO keywords upgrade the label;
  everything else lands in an `other` bucket and is logged with its raw shape,
  so new firmware/models never silently disappear.
- Alarm state is "alarm" only on positive event evidence, "quiet" only when a
  reachable module has no alarming events, else "unknown". Absence of evidence
  is never reported as "clear".
- Exposed as `fetch_safety_overview(access_token, home_id)` returning
  `{smoke, co, other, recent_events}`; routes + supervisor sync + Weather-page
  cards to be wired on pairing day (devices needed to confirm exact shapes).

## Pairing-day checklist

1. Pair alarms in the Netatmo app to the Stroheckgasse home.
2. Check backend logs for "non-weather module" lines - confirms shapes seen.
3. Wire routes (`/api/weather/safety`), supervisor poll, UI cards.
4. Verify: battery levels, reachable flags, test alarm propagation timing.
