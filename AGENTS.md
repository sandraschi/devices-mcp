# devices-mcp — Per-Repo Agent Instructions

**Last updated**: 2026-06-02  
**Fleet standard**: `D:\Dev\repos\mcp-central-docs\standards\AGENTS.md`  
**Version**: v1.21.5 (beta)  
**Default git branch**: `main` — ignore `master` (legacy mirror; may be deleted)

---

## What this repo is

**Beta** home IoT stack — three **delivery legs**, one Python package:

| Leg | Path / artifact | Role |
|-----|-----------------|------|
| **1 — MCP** | `src/devices_mcp/server_v2.py`, `devices-mcp.mcpb` | FastMCP stdio/HTTP, portmanteau tools |
| **2 — Webapp** | `web-sota/` | FastAPI `:10717` + React SPA `/app/` |
| **3 — Desktop** | `native/` → NSIS installer | Tauri + PyInstaller sidecars |

**Rule:** Only **one** backend on **10717**. NSSM service and Tauri must not both bind the port.

Docs hub: [docs/README.md](docs/README.md) · architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Git branches

- **`main`** — sole development and release branch; GitHub default.
- **`master`** — leftover from pre-rename / old CI; was ahead of nothing useful. Do not branch from it. If it diverges again, fast-forward or delete on GitHub.

Clone: `git clone https://github.com/sandraschi/devices-mcp` then `git checkout main` if needed.

---

## Startup

```powershell
# Backend only (FastAPI, port 10717)
Set-Location D:\Dev\repos\devices-mcp\web-sota
$env:PYTHONPATH = "D:\Dev\repos\devices-mcp\src;D:\Dev\repos\devices-mcp\web-sota"
uv run python -m backend.server --host 127.0.0.1 --port 10717

# Full webapp (backend + Vite HMR on 10716)
D:\Dev\repos\devices-mcp\web-sota\start.ps1
# http://127.0.0.1:10717/app/

# MCP stdio
Set-Location D:\Dev\repos\devices-mcp
uv run python -m devices_mcp.server_v2

# Regenerate LLM index files
uv run python -m devices_mcp.utils.llms_txt
```

Packaged backend: `run_webapp_backend.py` (PyInstaller sidecar).

---

## Ports

| Port | Service |
|------|---------|
| 10717 | FastAPI backend + static SPA |
| 10716 | Vite dev frontend only |
| 10715 | USB / camera helper sidecar (optional) |

---

## Layout

- **MCP tools**: `src/devices_mcp/tools/portmanteau/`
- **Web routes**: `web-sota/backend/routes/` — registered in `web-sota/backend/server.py` `_setup_routes()`
- **Web UI**: `web-sota/frontend/src/pages/` — Settings has **Logging** and **Local LLM** sections
- **Config**: `config.yaml` (not committed); template `config.example.yaml`; user path `%USERPROFILE%\.config\devices-mcp\config.yaml`
- **Default logs**: `%USERPROFILE%\.local\share\devices-mcp\devices-mcp.log` (no config edit required)
- **LLM**: Ollama + LM Studio always in provider catalog; URLs in config `llm:` or Settings UI

---

## Webapp notes (regression watchlist)

1. **Logs page** — `Logs.tsx`: avoid unstable `useEffect` deps that refetch in a loop.
2. **Lighting** — `lighting.py` list responses may nest under `result["result"]`.
3. **Health / Status** — device table + autodiscover: `web-sota/backend/routes/devices.py`, `Health.tsx`.
4. **Tauri splash** — reuses existing `:10717` listener when NSSM already runs; CORS for `tauri://` origins.
5. **Chat / LLM** — providers from `GET /api/llm/providers` (catalog always includes `ollama`, `lm_studio`).

Run backend as module: `python -m backend.server`, not `python backend/server.py`.

---

## Build (desktop leg 3)

```powershell
Set-Location D:\Dev\repos\devices-mcp\native
.\build.ps1
# Output: dist\Devices-MCP-*-x64-setup.exe
```

Order: `npm install` → PyInstaller sidecars → `tauri build`. See [docs/DESKTOP.md](docs/DESKTOP.md).

---

## Quality

- `just lint` / `just fix` / `just typecheck` when Justfile present
- Pre-commit: ruff
- Releases: local `native/build.ps1` + `gh release create` (GitHub Actions often disabled on fleet)

---

## LLM documentation files

| File | Purpose |
|------|---------|
| `llms.txt` | Short navigation index for agents |
| `llms-full.txt` | Stitched README + INSTALL + `docs/*.md` + this file |

Regenerate after doc changes: `uv run python -m devices_mcp.utils.llms_txt`
