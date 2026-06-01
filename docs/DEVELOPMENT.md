# Development

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ (web-sota frontend, Tauri)
- Rust toolchain (Tauri only)
- Windows x64 for desktop release builds

## Clone and run (legs 1 + 2)

```powershell
git clone https://github.com/sandraschi/devices-mcp
cd devices-mcp
uv sync
copy config.example.yaml config.yaml
# edit config.yaml

.\web-sota\start.ps1
```

- Dashboard: http://127.0.0.1:10717/app/
- Vite dev (optional): http://127.0.0.1:10716

## MCP server only

```powershell
uv run python -m devices_mcp.server_v2
```

## Tauri + sidecars (leg 3)

```powershell
cd native
pwsh -File build.ps1
```

Produces `dist/Devices-MCP-<version>-x64-setup.exe`. PyInstaller step takes several minutes.

**Do not** run `npm install` in `native/` after sidecars are built without re-running `build-sidecar.ps1` (prepare script can restore stubs).

## MCPB pack

```powershell
npx @anthropic-ai/mcpb validate manifest.json
npx @anthropic-ai/mcpb pack . dist/devices-mcp.mcpb
```

## Tests

```powershell
uv run pytest tests/ -q --ignore=tests/hardware
```

Hardware tests require LAN devices; see `tests/README.md`.

## Lint

```powershell
uv run ruff check src web-sota/backend
```

## CI note

GitHub Actions may be disabled on the account; releases are often cut locally with `gh release create`.
