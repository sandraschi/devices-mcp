# Desktop app (Tauri)

## Download

[GitHub Releases](https://github.com/sandraschi/devices-mcp/releases):

| Asset | Use |
|-------|-----|
| `Devices-MCP-1.21.5-x64-setup.exe` | **Recommended** — NSIS installer with sidecars |
| `Devices-MCP-1.21.5-windows-x64.zip` | Portable: `Devices-MCP.exe` + sidecars + `config.example.yaml` |
| `tauri.exe` | Launcher only — **not** a full install |

## First run

1. Install from setup.exe.
2. Copy `config.example.yaml` to `%USERPROFILE%\.config\devices-mcp\config.yaml` (or next to portable `Devices-MCP.exe`).
3. Edit credentials and LAN IPs.
4. Launch **Devices MCP** — splash screen polls `http://127.0.0.1:10717/api/health`, then opens `/app/`.

If splash says "did not start in time" but the browser works at the same URL, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) (usually CORS or NSSM already on 10717).

## Coexistence with NSSM / dev backend

If a service already runs the backend on **10717**, the desktop app **reuses** it (v1.21.5+) instead of failing spawn. Prefer **one** backend:

- **NSSM + browser:** `http://127.0.0.1:10717/app/`
- **Desktop installer only:** stop NSSM first, or accept reuse mode

## Build from source

```powershell
cd native
pwsh -File build.ps1
# dist\Devices-MCP-1.21.5-x64-setup.exe
```

Order: `npm install` → PyInstaller sidecars → `tauri build`. See [DEVELOPMENT.md](DEVELOPMENT.md).

## Splash and navigation

- Initial URL: `splash.html` (bundled in Tauri assets)
- Success: redirect to `http://127.0.0.1:10717/app/`
- Rust also navigates when sidecar logs show Uvicorn ready
