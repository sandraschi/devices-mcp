# Architecture

## Three delivery legs

```
┌─────────────────────────────────────────────────────────────┐
│  Leg 1 — MCP server (devices_mcp)                           │
│  FastMCP · stdio for IDE · optional HTTP :10717/mcp         │
└───────────────────────────┬─────────────────────────────────┘
                            │ same Python package / tools
┌───────────────────────────▼─────────────────────────────────┐
│  Leg 2 — Webapp (web-sota/)                                 │
│  FastAPI backend :10717 · React SPA at /app/                │
│  Vite dev :10716 (proxies /api → 10717)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ bundled in release
┌───────────────────────────▼─────────────────────────────────┐
│  Leg 3 — Desktop (native/)                                  │
│  Tauri shell · spawns PyInstaller sidecars                    │
│  devices-mcp-backend.exe · devices-mcp-camera.exe           │
└─────────────────────────────────────────────────────────────┘
```

| Leg | Entry | Artifact |
|-----|--------|----------|
| MCP | `uv run python -m devices_mcp.server_v2` or MCPB | `devices-mcp.mcpb` |
| Webapp | `web-sota/start.ps1` or sidecar | Browser → `http://127.0.0.1:10717/app/` |
| Desktop | Start menu **Devices MCP** | `Devices-MCP-*-x64-setup.exe` |

## Single backend rule

Only **one process** should bind **127.0.0.1:10717** (or your configured host/port).

- **NSSM / Windows service** running the backend → use browser or Tauri as a **viewer**; desktop app detects an existing listener and reuses it (v1.21.5+).
- **Desktop-only** → installer starts sidecars; no separate NSSM needed.

## Sidecars (desktop only)

| Binary | Role |
|--------|------|
| `devices-mcp-backend.exe` | FastAPI + SPA static files (~123 MB) |
| `devices-mcp-camera.exe` | Camera MCP helper on :10715 (~123 MB) |
| `devices-mcp-native.exe` | Tauri WebView2 shell (~12 MB) |

NSIS installer embeds all three. The standalone `tauri.exe` on Releases is **not** sufficient alone.

## Config and data

- **Config:** `config.yaml` (see [CONFIGURATION.md](CONFIGURATION.md))
- **Logs:** prefer absolute path under `%USERPROFILE%\.local\share\devices-mcp\`
- **Supervisor:** connection health polling when backend lifespan starts

## Related

- [DESKTOP.md](DESKTOP.md) — install UX
- [DEVELOPMENT.md](DEVELOPMENT.md) — build pipeline

## Service control (canonical)

The always-on backend is the NSSM service devices-mcp (AUTO_START, LocalSystem, binary: nssm.exe, app: uv run python -m backend.server on 10717).

- Control it ONLY via the service manager: sc.exe stop/start devices-mcp or 
ssm restart devices-mcp.
- NEVER taskkill the service's child process - NSSM respawns it instantly and the port races (2026-08-16 incident).
- The Fleet-devices-mcp scheduled task (every 20 min) health-checks :10717/api/health and restarts via Restart-Service.
- Dev mode: start.bat/start.ps1 (backend + Vite + browser). One backend on 10717 at a time.
