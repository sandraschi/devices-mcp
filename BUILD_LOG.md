# BUILD_LOG.md — devices-mcp NSIS Build Records

## Build 2026-06-25 (Initial Build Log)

**Status:** Configuration fixes applied (pending next build for verification)

### Changes
- `.env` → `.env.example`: `tauri.conf.json` resources, `build.ps1` bundling fixed (no more dev API keys in installer)
- Duplicate `"resources/.env"` entry removed from `tauri.conf.json`
- `devices-mcp-backend.spec`: `console=True` → `console=False` (headless backend)
- `build.ps1`: Added step 0 port cleanup, Vite proxy port verification, project-venv PyInstaller, frozen binary smoke test, >= 5 MB size gate
- `pyproject.toml` + `mcpb/pyproject.toml`: `python_version = "3.8"` → `"3.10"`
- Camera sidecar verified: already using `bundle.resources` (not `externalBin`) — no migration needed
- `BUILD_LOG.md` created

### Known Issue: Port TIME_WAIT on install
The CUA smoke test may fail if the backend process from a previous run leaves port 10717 in TIME_WAIT (~240s on Windows). The `free_port` function in `backend.rs` currently only waits 300ms. Consider upgrading to the fleet `free_port` pattern (multilayer kill + 240s poll) from `mcp-central-docs`.

### Cert Pipeline Status
| Gate | Status |
|------|--------|
| TypeScript lint | PASS (assumed — `tsc --noEmit` in build.ps1) |
| Frontend build | PASS (assumed) |
| PyInstaller backend | PENDING (next build) |
| Frozen binary smoke test | PENDING (next build) |
| Size gate (>= 5 MB) | PENDING (next build) |
| NSIS build | PENDING (next build) |
| CUA-NSIS smoke test | NOT IMPLEMENTED |

## Build 2026-08-01 (v2.4.0 release)

**Status:** PASS - clean build, shipped

### Build
- `just build-native`: frontend (vite, 7.6s) -> PyInstaller sidecars -> Rust (2m02s) -> NSIS
- Artifacts: `Devices MCP_2.4.0_x64-setup.exe` (182.6 MB), `devices-mcp-2.4.0.mcpb` (3.2 MB, 1047 files)
- Rust warnings only: dead code (`SIDECAR_CAMERA`, `repo_root`, `spawn_sidecar`) - harmless

### Notable
- tauri.conf.json version aligned 1.22.1 -> 2.4.0 (was stale)
- Frontend dist built with new invert-hack theme (no dark: variants remain)
- Ruleset `main-protection` scoped from ~ALL to main (was blocking branch deletion API)
- Release: https://github.com/sandraschi/devices-mcp/releases/tag/v2.4.0
