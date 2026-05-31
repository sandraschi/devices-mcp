# Devices MCP — Tauri desktop

Native Windows shell for the **web-sota** dashboard (ports **10715** camera, **10717** API/SPA, **10716** Vite in dev).

## Prerequisites

- [Rust](https://rustup.rs/) + MSVC build tools
- [Node.js](https://nodejs.org/) 20+
- [uv](https://docs.astral.sh/uv/) with project deps synced (`uv sync`)
- WebView2 (usually preinstalled on Windows 11)

## Dev (no PyInstaller)

`npm install` runs `setup-stub-sidecars.ps1` (placeholder exes so Tauri can compile). Dev mode starts real backends via **uv**, not the stubs.

```powershell
cd D:\Dev\repos\devices-mcp\native
npm install
npm run dev
```

Place `config.yaml` in the repo root (or `%USERPROFILE%`) so hardware integrations load.

## Release build

```powershell
cd D:\Dev\repos\devices-mcp\native
.\build.ps1
```

Steps: icon → PyInstaller sidecars → `tauri build`. Installer under `native\target\release\bundle\nsis\`.

Sidecars only:

```powershell
.\build-sidecar.ps1
```

## Notes

- Production UI loads `http://127.0.0.1:10717/app/` (FastAPI serves the built SPA + `/api`).
- Dev UI uses Vite `http://127.0.0.1:10716` with API proxy to **10717**.
- First backend boot can take 30–90s while integrations initialize.
