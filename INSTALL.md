# Installation

**Status:** Beta · **Version:** see [Releases](https://github.com/sandraschi/devices-mcp/releases)

Choose **one primary path**. All paths share the same `config.yaml` model.

---

## Option A — Windows desktop (leg 3)

For operators who want a double-click install with bundled Python sidecars.

1. Download **`Devices-MCP-1.21.5-x64-setup.exe`** from [Releases](https://github.com/sandraschi/devices-mcp/releases).
2. Run installer (admin if prompted for WebView2/runtime).
3. Copy `config.example.yaml` → `%USERPROFILE%\.config\devices-mcp\config.yaml`.
4. Edit LAN IPs and credentials.
5. Launch **Devices MCP** from Start menu.

Portable: use `Devices-MCP-1.21.5-windows-x64.zip` — keep `config.yaml` beside `Devices-MCP.exe`.

Details: [docs/DESKTOP.md](docs/DESKTOP.md)

**Do not** use the small `tauri.exe` alone (~12 MB) — it does not include sidecars.

---

## Option B — MCPB (leg 1, Claude Desktop)

1. Download **`devices-mcp.mcpb`** from [Releases](https://github.com/sandraschi/devices-mcp/releases).
2. Drag into Claude Desktop (or install per Anthropic MCPB docs).
3. Add `config.yaml` on the machine where the server runs (stdio uses your clone or pack extract path).

MCPB does **not** install the web dashboard or Tauri shell.

---

## Option C — Clone + uv (legs 1 + 2, developers)

```powershell
git clone https://github.com/sandraschi/devices-mcp
cd devices-mcp
uv sync
copy config.example.yaml config.yaml
```

**Dashboard:**

```powershell
.\web-sota\start.ps1
```

Open http://127.0.0.1:10717/app/

**MCP stdio (Cursor / Claude config):**

```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "uv",
      "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "python", "-m", "devices_mcp.server_v2"]
    }
  }
}
```

Replace `--directory` with your absolute clone path.

Optional: `just bootstrap` then `just serve` if you use [just](https://github.com/casey/just).

---

## Option D — Windows service (NSSM / always-on backend)

For a machine that already runs the backend as a service on **10717**:

- Use the **browser** at http://127.0.0.1:10717/app/
- Or install Tauri **v1.21.5+** — it reuses an existing listener instead of failing

Do **not** start a second backend from the desktop installer.

Point `logging.file` to an absolute path (see [docs/CONFIGURATION.md](docs/CONFIGURATION.md)).

---

## Prerequisites

| Component | Desktop (A) | MCPB (B) | Clone (C) |
|-----------|---------------|----------|-----------|
| Windows 10/11 x64 | Yes | No (host OS for MCP host) | Optional |
| WebView2 | Yes (Tauri) | — | — |
| Python 3.12+ | Bundled in sidecars | User install via MCPB runtime | uv |
| config.yaml | Required | Required | Required |
| LAN devices | As configured | As configured | As configured |

---

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

| Issue | Pointer |
|-------|---------|
| Splash timeout | CORS / NSSM / [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) |
| Log file not found | [CONFIGURATION](docs/CONFIGURATION.md) |
| Port 10717 busy | Stop duplicate backend |

---

## Documentation

| Doc | Contents |
|-----|----------|
| [README.md](README.md) | Overview, three legs, TOC |
| [docs/README.md](docs/README.md) | Doc index |
