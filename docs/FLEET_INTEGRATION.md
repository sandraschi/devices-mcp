# Fleet integration — Fritz priority API

devices-mcp exposes a **read-only priority endpoint** for Fritz (`fleet-agent-mcp`) to poll home-safety incidents and trigger urgent notifications + Intel Hub reports.

## Endpoint

```http
GET http://127.0.0.1:10717/api/fleet/priority?ring_window_minutes=30
```

| Query param | Default | Range | Purpose |
|-------------|---------|-------|---------|
| `ring_window_minutes` | `30` | 5–180 | Ring intrusion event lookback |

## Response

```json
{
  "success": true,
  "healthy": true,
  "incident_count": 2,
  "critical_count": 1,
  "incidents": [
    {
      "id": "shelly-kitchen-…",
      "kind": "temperature_high",
      "source": "shelly",
      "title": "Kitchen temperature high",
      "description": "45.2°C — threshold exceeded",
      "urgency": 8.7,
      "critical": true,
      "location": "kitchen"
    }
  ],
  "sources": {
    "shelly": true,
    "nest_protect": true,
    "ring": true,
    "messages": true
  }
}
```

On failure the endpoint returns `success: false` with empty `incidents` (Fritz treats as unhealthy scan).

## Incident sources

| Source | Signals |
|--------|---------|
| **Shelly** | Kitchen ≥45°C absolute; per-sensor high/low thresholds; `alert_active` |
| **Nest Protect** (via Home Assistant) | CO emergency/warning, smoke emergency/warning |
| **Ring** | Contact/motion/intrusion keywords in recent events |
| **Messages** | Unacknowledged in-app alarm messages |

Implementation: `src/devices_mcp/integrations/fritz_priority.py`  
Route: `web-sota/backend/routes/fleet_priority.py`

## Fritz consumer

Fritz `coworker_devices_watch` polls every **5 minutes** (configurable via `devices_watch_interval` in `~/.fleet-agent/settings.json`).

On **new critical** incidents (deduped in `~/.fleet-agent/devices_watch_state.json`):

1. Publish HTML report to Intel Reports Hub (`:11027`)
2. Urgent email + cursor inbox (if SMTP + `heartbeat_email` set)
3. `aiwatcher_push_event` with `urgency_hint`

MCP: `coworker_devices_watch()` on fleet-agent `:10996`  
Docs: [fleet-agent-mcp/docs/INTEL_REPORTS_HUB.md](https://github.com/sandraschi/fleet-agent-mcp/blob/main/docs/INTEL_REPORTS_HUB.md)

## Related docs

- [mcp-central-docs/patterns/intel-reports-hub.md](https://github.com/sandraschi/mcp-central-docs/blob/main/patterns/intel-reports-hub.md)
- [ARCHITECTURE.md](ARCHITECTURE.md) — ports 10715–10717
