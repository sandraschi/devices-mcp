<p align="center">
  <img src="https://img.shields.io/badge/status-beta-orange?style=flat-square" alt="Beta">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastMCP-3.4.4-purple" alt="FastMCP">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/release-v1.23.0-blue" alt="Version">
</p>

# devices-mcp

**Beta** home IoT stack for Sandra's fleet: **MCP tools** for agents, a **web dashboard** for humans, and an optional **Windows desktop installer** that bundles both. LAN devices (Tapo cameras/plugs, Philips Hue, Ring, Nest via Home Assistant, Shelly, USB cams, Netatmo, Vienna presets) are configured in `config.yaml` — not shipped as secrets.

> Not production-hardened. Expect rough edges, slow cold starts (~2 min for full PyInstaller sidecars), and API changes between releases.

---

## Table of contents

| Section | Link |
|--------|------|
| Three delivery legs | [Three legs](#three-delivery-legs) |
| Features (realistic) | [Features](#features) |
| Quick install | [Quick install](#quick-install) |
| Documentation | [Documentation](#documentation) |
| Ports | [Ports](#ports) |
| Requirements | [Requirements](#requirements) |
| License | [License](#license) |

---

## Three delivery legs

| Leg | What you get | Best for |
|-----|----------------|----------|
| **1 — MCP server** | FastMCP stdio/HTTP, 40+ portmanteau tools | Claude Desktop, Cursor, automation |
| **2 — Webapp** | Vite/React UI + FastAPI (`web-sota/`) | Browser dashboard, same APIs as desktop |
| **3 — Desktop (Tauri)** | `Devices-MCP-*-setup.exe` (~247 MB) | Double-click Windows install; spawns camera + backend sidecars |

Use **one backend on port 10717** at a time. If you already run the stack via **NSSM** or `just serve`, open the dashboard in a browser — do not start a second backend from the desktop app.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Desktop: [docs/DESKTOP.md](docs/DESKTOP.md)

---

## Features

- **Cameras:** Tapo/ONVIF, USB webcam/microscope (OpenCV), streaming hooks (quality varies by device/driver).
- **Energy:** Tapo P115 plugs; LAN discovery optional when cloud creds are set.
- **Lighting:** Philips Hue (incl. HomeAware on supported bridges, CLIP v2, group/scene management), Tapo lighting.
- **Security / sensors:** Ring (doorbell + alarm + WebRTC live view + two-way intercom), Nest Protect (via Home Assistant or direct OAuth2), Shelly, Netatmo, Open-Meteo (Vienna default).
- **Chat:** SOTA chat with localStorage persistence, 5 personalities, skill preprompt, NDJSON streaming, export/clear — LLM provider/model selector in Settings.
- **Dashboard:** Status table with device health, per-domain pages (cameras, energy, lighting, weather, robots …).
- **MCP:** 27 portmanteau tools (camera, energy, lighting, ring, nest, weather, security, …) on FastMCP 3.4 with tool annotations.
- **Fleet priority:** `GET /api/fleet/priority` — home-safety incidents for Fritz urgent dispatch (kitchen temp, CO, smoke, Ring).

**Not included:** guaranteed uptime SLA, cloud hosting, plug-and-play without `config.yaml`, or a single 12 MB exe (full desktop bundle is ~247 MB with embedded Python sidecars).

---

## Quick install

**Windows desktop (leg 3):** [GitHub Releases](https://github.com/sandraschi/devices-mcp/releases) → `Devices MCP_*_x64-setup.exe` (single NSIS installer — that's all you need).

**MCP bundle (leg 1):** Releases → `devices-mcp-*.mcpb` → Claude Desktop. Latest: `dist/devices-mcp-1.23.0.mcpb` (2.5 MB).

**Developers (leg 1+2):** see [INSTALL.md](INSTALL.md).

```powershell
git clone https://github.com/sandraschi/devices-mcp
cd devices-mcp
uv sync
.\web-sota\start.ps1
# http://127.0.0.1:10717/app/
```

## Build & Test (NSIS installer)

The desktop installer bundles TWO sidecars (backend + camera helper) into a single `Devices MCP_*_x64-setup.exe` (~247 MB).

```powershell
just build-native      # Full pipeline: frontend → PyInstaller → Rust → NSIS
just cua-nsis-test     # Install → CUA test → screenshot → uninstall
```

The **CUA smoke test** (`scripts/cua-smoke.py`) verifies:
1. Silent install succeeds
2. Backend health responds 200 on port 10717
3. Window renders at correct size
4. Diagnostics endpoint reports all systems
5. Clean uninstall

> See [CUA-NSIS Smoke Testing](https://github.com/sandraschi/mcp-central-docs/blob/main/standards/rules/cua_nsis_smoke_testing.md) — fleet standard.

Prerequisites: Rust toolchain, MSVC Build Tools, Tauri CLI 2.x.

---

## Documentation

| Doc | Contents |
|-----|----------|
| [INSTALL.md](INSTALL.md) | All install paths (Tauri, MCPB, clone, NSSM) |
| [docs/README.md](docs/README.md) | Full documentation index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | MCP + webapp + desktop, ports, sidecars |
| [docs/DESKTOP.md](docs/DESKTOP.md) | Tauri installer, splash, NSSM coexistence |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | `config.yaml`, Vienna preset, discovery flags |
| [docs/TOOLS.md](docs/TOOLS.md) | MCP tool families (summary) |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | `just`, build scripts, contributing |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | White screen, logs path, firewall |
| [docs/FLEET_INTEGRATION.md](docs/FLEET_INTEGRATION.md) | Fritz `/api/fleet/priority` consumer contract |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

LLM index: [llms.txt](llms.txt) · full: [llms-full.txt](llms-full.txt)

---

## Ports

| Port | Service |
|------|---------|
| 10717 | FastAPI backend (API + `/app/` SPA) |
| 10716 | Vite dev frontend only |
| 10715 | USB camera helper (optional) |

---

## Requirements

- **OS:** Windows 10/11 x64 for desktop installer; dev backend also runs on Linux/macOS with reduced hardware support.
- **Config:** `config.yaml` with your LAN IPs and credentials (see `config.example.yaml`, `home_preset: vienna` template).
- **Network:** Devices on reachable LAN; mDNS/LAN broadcast for Tapo discovery optional.

---

## License

MIT — see [LICENSE](LICENSE).
