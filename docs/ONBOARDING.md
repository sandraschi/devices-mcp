# Onboarding — devices-mcp

First-timer path from zero to a live home dashboard. Assumes Windows 10/11 x64,
your LAN devices, and `config.yaml` (never committed — gitignored).

## What you need (wrappee + accounts)

| Need | Cost | Where |
|------|------|-------|
| Windows 10/11 PC on the same LAN as your devices | — | — |
| TP-Link Tapo account (cameras/plugs/bulbs) | free | Tapo app |
| Philips Hue bridge on LAN + bridge username (press link button, then pair) | free/local | Hue app |
| Ring account (doorbell/alarm, optional) | free account; devices extra | Ring app |
| Google/Nest via Home Assistant (Nest Protect, optional) | free | HA + Google Cloud OAuth consent |
| Netatmo dev app (weather, optional) | free | dev.netatmo.com |
| LLM (optional): Ollama `:11434` or LM Studio `:1234` local, or an OpenAI key for cloud | local free / cloud pay-per-use | Settings page |

No paid fleet service. No cloud hosting. Everything runs on your box.

## Setup (10 minutes)

1. Clone + deps: `git clone https://github.com/sandraschi/devices-mcp`, `cd devices-mcp`, `uv sync`.
2. Copy `config.example.yaml` to `config.yaml`. Pick `home_preset: vienna` (192.168.0.x
   template) or `generic` (192.168.1.x placeholders), then replace `YOUR_*` values.
   Keep `discovery.enabled: true` for the first run — static hosts can come later.
3. Start: `.\web-sota\start.ps1` (full stack) or `.\start.ps1` from repo root.
   Open http://127.0.0.1:10717/app/ (backend API on :10717, Vite dev on :10716).
4. Sanity check: `GET http://127.0.0.1:10717/api/health` returns 200, and the
   dashboard device table fills in. From an agent: `sensor_health` MCP tool.

## Pitfalls that bite first-timers

- **One backend on :10717.** The NSSM service and the Tauri desktop app must not both
  bind the port. If a service owns it, launchers skip startup and the desktop app
  reuses the listener (see docs/DESKTOP.md).
- **config.yaml + *.cache are secrets.** Tokens land in `ring_token.cache`,
  `hue_bridge.cache`, `netatmo_token.cache`. All are gitignored — never force-add them.
- **Windows-only hardware.** USB webcams, DirectShow enumeration, and the NSIS
  installer assume Windows. The Python backend imports elsewhere with reduced support.
- **Cold starts are slow.** Full PyInstaller sidecars take ~2 min the first time.

## Mock-until-onboarded

Until the checks above pass, dashboard KPIs may show sample/placeholder values.
After a successful backend health check + device discovery, live data replaces them.
If numbers look static, re-run the sanity check before trusting the UI.
