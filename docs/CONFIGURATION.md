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

## Logging (important for dashboard Logs page)

Use an **absolute** path for installed/service use:

```yaml
logging:
  file: "C:/Users/YOU/.local/share/devices-mcp/devices-mcp.log"
```

Relative `tapo_mcp.log` resolves against the **dev repo** when the API runs from source — wrong for NSSM/Tauri.

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
