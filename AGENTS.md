# devices-mcp — Per-Repo Agent Instructions

**Last updated**: 2026-05-25
**Fleet standard**: `D:\Dev\repos\mcp-central-docs\standards\AGENTS.md`
**Version**: v1.21.1

---

## Startup

```powershell
# Backend only (FastAPI + FastMCP, port 10717)
cd web-sota
$env:PYTHONPATH = "D:\Dev\repos\devices-mcp\src;D:\Dev\repos\devices-mcp\web-sota"
uv run python -m backend.server --host 127.0.0.1 --port 10717

# Full webapp (backend + Vite frontend HMR on 10716)
.\web-sota\start.ps1

# MCP server (stdio)
uv run python src/devices_mcp/server.py
```

## Ports

| Port | Service |
|------|---------|
| 10715 | USB Camera helper (Windows, optional) |
| 10716 | Frontend Vite dev |
| 10717 | Backend FastAPI + FastMCP |

## Architecture

- **Web frontend**: `web-sota/frontend/` — Vite + React 18 + shadcn/ui + Tailwind, routes under `/app/`
- **Backend routes**: `web-sota/backend/routes/` — 37 route modules, registered in `_setup_routes()` in `server.py`
- **MCP tools**: `src/devices_mcp/tools/` — portmanteau patterns in `tools/portmanteau/`
- **Config**: `config.yaml` at repo root (not committed; `config.yaml.example` is the template)

## Webapp Bug Context (v1.21.1)

The following bugs were fixed. If they reappear, check:

1. **Log page infinite loop**: `web-sota/frontend/src/pages/Logs.tsx` — `useEffect` must use `useCallback` wrapper, not `[load]` dependency
2. **Lighting page empty lights**: `web-sota/backend/routes/lighting.py:251` — `_list_lights()` returns via `build_success_response()` which nests under `result["result"]`, not `result`
3. **Lighting scenes/control broken**: Endpoints used non-existent `LightingManagementTool` class — use actual portmanteau functions (`_control_light`, `_get_light_status`, `HueManager.get_all_scenes()`) instead
4. **PC Health page hangs**: Fetches need `AbortController` timeout — `web-sota/frontend/src/pages/Health.tsx:67`

## Notes

- `backend/server.py` uses relative imports (`from .routes import ...`) — run as module: `python -m backend.server`, NOT `python backend/server.py`
- Hue bridge pairing requires pressing the link button on the bridge before calling `/api/lighting/hue/pair`
- Ring 2FA requires manual code entry in the Ring page
- Justfile recipes: `just lint`, `just fix`, `just typecheck`, `just dev`, `just build`
