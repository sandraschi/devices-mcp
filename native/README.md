# Devices MCP — Tauri desktop (leg 3)

Windows shell that spawns PyInstaller **backend** and **camera** sidecars and opens the web dashboard.

**User docs:** [docs/DESKTOP.md](../docs/DESKTOP.md) · **Build:** `pwsh -File build.ps1` → `dist/Devices-MCP-*-x64-setup.exe`

**Dev:** `npm run tauri dev` uses `uv` for backends (not sidecar stubs).
