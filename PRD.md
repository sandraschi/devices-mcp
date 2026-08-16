# Devices MCP - Product Requirements Document

**Version**: 2.4.1 (2026-08-16) - Beta
**Repo**: https://github.com/sandraschi/devices-mcp

## Purpose

Devices MCP is a home-IoT control plane for the Vienna flat: cameras, smart
plugs, Philips Hue lighting, Netatmo weather, Ring doorbell, Nest Protect
(via Home Assistant), and safety alarms - exposed as MCP tools for agents,
a browser dashboard, and a Tauri desktop app.

## Delivery Legs

| Leg | Path | Role |
|-----|------|------|
| MCP | `src/devices_mcp/` | FastMCP 3.4.4 stdio/HTTP server, portmanteau tools |
| Webapp | `web-sota/` | FastAPI `:10717` (REST + MCP `/mcp`) + React SPA `:10716` |
| Desktop | `native/` | Tauri 2.0 + NSIS installer, embedded PyInstaller backend |

## Architecture

```
Cameras / Tapo plugs / Hue bridge / Netatmo / Ring / Nest(HA)
        |        |            |          |        |
        +--------+------------+----------+--------+
                    devices_mcp (FastMCP + FastAPI)
                              |
              +---------------+----------------+
              |               |                |
        MCP clients      Webapp :10717     Desktop (Tauri)
        (Claude,       (REST /api, /mcp,      reuses :10717
         Cursor,        SPA :10716)
         opencode)
```

## Service Model (canonical)

- **NSSM service `devices-mcp`** runs the always-on backend on `:10717`
  (AUTO_START, LocalSystem). Control it ONLY via the service manager:
  `sc.exe stop/start devices-mcp` or `nssm restart devices-mcp`.
- **`Fleet-devices-mcp` scheduled task** (every 20 min) health-checks
  `http://127.0.0.1:10717/api/health` and restarts the service via
  `Restart-Service` - it never kills child processes.
- **Dev mode**: `start.bat` / `start.ps1` (backend + Vite + browser).
- One backend on 10717 at a time. Never `taskkill` the service's child -
  NSSM respawns it and the port races.

## Key APIs

- `GET /api/health`, `GET /health` - liveness
- `GET /api/v1/models`, `GET /api/v1/settings` - fleet-standard aliases
- `POST /api/system/reconnect` - reconnect Hue + Netatmo in one round trip
- `GET /api/lighting/hue/status` - bridge state incl. real `lights_count`
- `GET /api/netatmo/status` - station state incl. `reconnect_url`
- `GET /api/sensors/tapo-p115` - per-plug power/energy
- `GET /api/v1/diagnostics` - CUA smoke test surface

## Dashboard (v2.4.1)

Hero section, KPI grid (cameras, per-plug energy, lighting, weather, ring,
nest, alarms, MCP capabilities), backend status dot, reconnect-services
button. Dark theme (Slate/Amber), `data-testid` on KPIs.

## Quality Gates

- `just e2e` - Playwright audit (backend health, frontend loads, no console
  errors, /health + v1 probe shapes)
- `just cua-webapp-test` - browser walk: stack start, connected badge,
  sidebar nav click-through with per-page screenshots
- `just cua-nsis-test` - installed-app smoke (release gate)
- `just lint` / `just typecheck` - ruff + pyright
