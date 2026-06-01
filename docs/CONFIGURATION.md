# Configuration

## Config file locations (search order)

1. Path you pass explicitly
2. Repo root `config.yaml` (dev)
3. `%USERPROFILE%\.config\devices-mcp\config.yaml` (installed desktop / service)
4. Current directory `config.yaml`
5. First-run template from `config.example.yaml` (Vienna preset)

## Home preset and discovery

```yaml
home_preset: vienna   # vienna | generic | off

discovery:
  enabled: true
  tapo_p115: true
  tapo_p115_broadcast: "192.168.0.255"
  usb_cameras: true
  philips_hue: true
  ring: false
  shelly: false
```

- **vienna** — Stroheckgasse-style `192.168.0.x` template in `config.example.yaml` (placeholders only).
- **LAN discovery** — Tapo P115 and USB cameras can augment static `devices[]` lists when enabled.
- Disable per-flag to use **static IPs only**.

## Logging

**Default (no config edit):** `%USERPROFILE%\.local\share\devices-mcp\devices-mcp.log` — created on first backend start.

**Change path:** web app **Settings → Logging**, or:

```yaml
logging:
  file: "D:/other/path/devices-mcp.log"
```

## Local LLM

**Settings → Local LLM** in the web app (Ollama `11434`, LM Studio `1234`). Optional `config.yaml`:

```yaml
llm:
  ollama_url: "http://127.0.0.1:11434"
  lm_studio_url: "http://127.0.0.1:1234"
  preferred_provider: "ollama"
```

## Environment (optional)

| Variable | Effect |
|----------|--------|
| `TAPO_MCP_SKIP_HARDWARE_INIT` | Faster backend start (desktop default) |
| `TAPO_MCP_LAZY_INIT` | Defer hardware init to first use |
| `DEVICES_MCP_PACKAGED` | Relaxed CORS for Tauri splash (set by sidecar) |
| `TAPO_P115_BROADCAST` | Override Tapo LAN discovery broadcast |

## Security

Do not commit real `config.yaml`. Ring/Netatmo tokens belong in cache files named in config, not in git.

See also [MCP_Server_Status_Authentication_Configuration.md](MCP_Server_Status_Authentication_Configuration.md) (may reference older ports).
