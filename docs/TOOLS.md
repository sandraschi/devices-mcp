# MCP tools (summary)

Portmanteau tools group related operations. Full signatures live in `src/devices_mcp/tools/` and MCPB manifest.

| Tool family | Typical domains |
|-------------|-----------------|
| `camera_management` | Tapo/ONVIF/USB streams, PTZ, status |
| `energy_management` | Tapo P115 plugs, power readouts |
| `lighting_management` | Hue, Tapo lights, scenes |
| `ring_management` | Ring doorbells (when enabled) |
| `home_assistant_management` / Nest routes | Nest Protect via HA |
| `weather_management` | Netatmo, Open-Meteo |
| `messages_management` | Alerts, supervisor messages |
| `system_management` | Health, init, hardware |
| `onboarding` | Discovery helpers (partial LAN) |

**HTTP (dashboard):** same backend exposes `/api/*` — see `web-sota/backend/routes/`.

**Capabilities endpoint:** `GET /api/capabilities` when HTTP MCP bridge is enabled.

For Claude/Cursor, install [devices-mcp.mcpb](https://github.com/sandraschi/devices-mcp/releases) or stdio:

```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "uv",
      "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "python", "-m", "devices_mcp.server_v2"],
      "env": {}
    }
  }
}
```

Adjust `--directory` to your clone path.
