---
name: devices-mcp-home
description: >-
  Live inventory and control guide for this devices-mcp smart home (Vienna,
  192.168.0.x): 18 Hue lights on 5 rooms via CLIP v2, 3 Tapo P115 plugs,
  2 Tapo C200 PTZ cameras + USB C922, Netatmo station with 3 modules, Ring
  doorbell, Nest (unconnected), 2 offline robots. Use when the user asks what
  devices they have, what's online, or wants status/control of home hardware.
  Includes MCP tool actions, dashboard pages, API endpoints, safety rules and
  the known-issue list (Ollama reinstall, kitchen plug, crash watch).
---

# Devices MCP — Home Inventory & Control

You have access to a **live device snapshot** injected as the system message in Chat.
Treat it as ground truth for "what do I have?" unless the user says it is stale.
This file is the static map: which devices exist, how each is driven, and where
the bodies are buried. Snapshot (live) beats this file (surveyed 2026-10-03) on
any disagreement.

## House facts

- LAN `192.168.0.x`, site name "Stroheckgasse". DHCP moves devices — never trust
  a cached IP for plugs/cameras; re-sweep instead of editing config.
- Backend: NSSM service `devices-mcp`, FastAPI on `http://127.0.0.1:10717`
  (+ SPA at `/app/`). Exactly ONE backend on 10717 — NSSM or Tauri, never both.
- Frontend dev `:10716` (Vite, often not running); production UI is `:10717/app/`.
- Secrets live in `config.yaml` + `*.cache` (gitignored). Never print them.
- Logs: `%USERPROFILE%\.local\share\devices-mcp\`.

## Lighting — Philips Hue (works, via CLIP v2)

- Bridge: Hue Bridge Pro (BSB003) at `192.168.0.236`, HTTPS-only, paired.
  The old phue v1 API is dead on this bridge; enumeration + on/brightness go
  through CLIP v2 (fast, ~1 s for a full rescan).
- 18 lights, all reachable: Bathroom Lightstrip, Bathroom light, Kitchen lamp 1–2,
  Bedroom side light 1–2, Bedroom ceiling lamp 1–3, Living room ceiling lamp 1–5,
  Hallway color lamp, Hue go 1, Hue ambiance candle 1, Puzzle Lamp.
- 5 rooms (Bathroom, Kitchen, Hallway, Living room, Bedroom), 53 scenes.
- Color control (hue/sat/rgb) is NOT yet on the v2 path — on/off + brightness only.
- Drive: `lighting_management` action `control` (device_id = v2 UUID from status),
  Lighting page, `POST /api/lighting/control`, `GET /api/lighting/status|groups|scenes`.

## Energy — Tapo plugs (sweep works since 2026-10-04)

- `tapo_p115_aircon` @ `.17` — live.
- `tapo_p115_server` @ `.38` — live (~200+ W).
- Kitchen Zojirushi — DHCP wanderer. Static config may point at a stale IP (was
  `.138` dead while the plug itself answered as "Kitchen 1" @ `.137` @ 46W).
  If a kitchen entry shows 0W while another "Kitchen 1" entry is live, the
  static host is stale — update it or delete it and let the sweep own the plug.
- `Tapo P115#4` @ `.66` — the 4th household plug, found by sweep (4W, on).
- Sweeping ALWAYS merges static hosts + subnet broadcast now (defaults work with
  zero discovery config; the old code needed exact config keys that no live
  config set). `POST /api/sensors/tapo-p115/refresh`, MCP `discover` action.
- DURABLE FIX for wandering plugs: DHCP reservations in the router, then static
  config hosts match permanently.
- Sweep only matches energy-monitoring plugs (P110/P115). A P100/P105 answers
  broadcast but is filtered by design.

## Cameras (video works)

- `tapo_kitchen` @ `.164` and `tapo_living_room` @ `.206` — Tapo C200,
  fw 1.9.1, 1280x720, PTZ-capable. ONVIF creds are configured; handshake + stream
  URI + first frame verified. If video dies: check the camera still has its
  **camera account** (Tapo app → camera settings, not the cloud login).
- PTZ: `POST /api/ptz/up|down|left|right|stop|zoom-in|zoom-out/{camera}`, Cameras page.
- `usb_camera_c922` — Logitech C922, device 0. The NSSM service runs as LocalSystem
  (session 0, no desktop) and CANNOT open it in-process. USB video needs the
  `:10715` camera helper running in the user session, which the backend then proxies.
  If the helper isn't running, the USB tile stays dark — that is expected, not a bug.
- Drive: `camera_management` (list|info|status|snapshot…), Cameras page,
  `GET /api/cameras`, `GET /api/cameras/{id}/mjpeg`.

## Weather — Netatmo (works, hands off)

- Station `70:ee:50:3a:0e:dc` (indoor main) + `Bathroom` indoor_extra
  (**battery 5 — nearly dead, replace**) + `Living room` outdoor (battery 79).
- 10-minute background loop, OAuth token auto-refreshes. No manual connect needed.
  (A past supervisor bug closed the shared session every poll — fixed; if a
  disconnect/reconnect dance ever returns, check `connection_supervisor.py` first.)
- Drive: `weather_management` (current|stations|alerts…), Weather page,
  `GET /api/weather/current|stations`.

## Ring (doorbell video works, alarm fetch broken)

- Doorbell camera streams. Local client needs init from the UI when it shows
  "not initialized".
- `locations` endpoint 404s at Ring's side (vendor API drift) — alarm arm/status
  via API is broken independently of creds.
- Drive: `ring_management` (status|doorbells|events|live_view|snapshot…), Doorbell page.

## Nest Protect (not connected)

- No OAuth token. Connect via the Nest page flow (Google OAuth), then devices appear.
- Drive: Nest page, `GET /api/nest/status`, `home_assistant_management` for HA-backed entities.

## Shelly (disabled)

- Discovery off, 0 devices. Enable in config + `POST /api/shelly/init` to adopt.
- Drive: `shelly_management`, Sensors page.

## Robots (registry only — all offline)

- `dreame_d20` (Dreame D20 Pro, `.144`) needs `dreame-mcp` on `:10894` — not running.
- `yahboom_car` (Yahboom ROS 2, `.100`) needs `yahboom-mcp` on `:10892` — not running.
- Nori entry points at `norirobotics-mcp` `:11970`, which does not exist in the fleet.
- Command buttons are disabled while a robot reports offline (red dot). Do not
  promise movement — offer to start the backing MCP service instead.
- Drive (when online): `robotics_management`, Robots page, `GET /api/robots/`.

## Local LLM (works)

- Ollama `:11434` (NSSM service `ollama-serve`, models on `N:\AI\ollama\models`).
  FIXED 2026-10-03: every generate 500'd with "llama-server binary not found"
  because `lib\ollama\` was empty. Root cause was reinstalling while the service
  + tray app held the install dir locked, so no reinstall ever completed. Fix was
  stop-everything-first (`sc stop ollama-serve`, kill tray/server), then run the
  installer. Verified: `llama3.2:3b` generates, backend chat returns it.
  If inference ever 500s again: check `lib\ollama\llama-server.exe` exists first.
- LM Studio `:1234` registered and working (chat verified via `nemotron-3-nano`).
  Chat UI persists provider+model, so a working choice survives reloads.

## Service control

- Restart: `POST /api/shutdown` (exits ~500 ms later; NSSM auto-restarts) or
  `sc.exe stop/start devices-mcp`. Never kill the child PID.
- Boot takes ~2 min (imports + hardware init). Health: `GET /api/health`.
- KNOWN FIXED 2026-10-03: the backend died every few minutes with native heap
  corruption (`0xc0000374`). faulthandler caught concurrent threads inside
  `webcam._probe_resolution` — every USB status call opened a DirectShow capture,
  and concurrent graph builds corrupted the heap (worse in session 0, where no
  desktop exists). Fix: probes are skipped in session 0, cached per process, and
  all cv2 opens serialized (`camera/_native_locks.py`); zeep/SOAP likewise
  serialized (not thread-safe). 16+ min stable with zero crash events after the
  fix (was: several per 10 min). If restarts ever return, check Event Viewer
  Application Error 1000 first, then the faulthandler trace in service-stderr.log.

## Answer patterns

- "What lights do we have?" — the 18 names above (or live status), grouped by room.
- "What's offline?" — kitchen plug, Nest, Shelly (disabled), both robots, USB cam
  (helper-dependent), Ollama inference. Say WHY for each, from this file.
- "Summarize my home" — one line per domain: lights 18/18, plugs 2/3, cams 2(+1 USB),
  weather fresh, Ring video ok/alarm broken, robots parked, LLM down pending reinstall.
- "Reset a plug" — breaker-reset endpoint (backoff), power-cycle (unreachable),
  config removal + refresh (retire), DHCP reservation (wandering IP).
- Control requests (turn on, move, arm): name the MCP tool action + dashboard page;
  for physical actions (toggle a plug, move PTZ, drive nowhere while offline),
  confirm which device first — UUIDs all look alike.

## If snapshot is missing

Say the webapp may still be starting (2-min boot) and suggest Chat after restart,
or check Dashboard + MCP Capabilities. Never invent devices not listed here.
