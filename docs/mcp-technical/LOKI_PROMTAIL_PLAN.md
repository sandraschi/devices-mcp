# Loki + Promtail Deployment Plan (2025-11-12)

## Overview

- **Loki** centralizes structured logs from the Tapo camera control plane,
  edge agents, and system components.
- **Promtail** runs on each node, tailing local log files and forwarding them
  over HTTP to the hub-based Loki instance.

## Configuration Assets

| Path | Purpose |
|------|---------|
| `deploy/loki/loki-config.yaml` | Single-instance Loki configuration with filesystem storage. |
| `deploy/promtail/promtail-config.yaml` | Promtail setup for application, edge agent, and system logs. |

## Deployment Steps

1. **Loki on Hub**
   - Install Loki binary or container (>= 2.9).
   - Place `loki-config.yaml` under `/etc/loki/` (or mount into container).
   - Ensure storage directories `/var/lib/loki/{chunks,wal}` are writable.
   - Open port `3100/tcp` on the hub (internal network only).

2. **Promtail on Each Node**
   - Install Promtail (~same version as Loki).
   - Copy `promtail-config.yaml` and adjust log paths if required.
   - Set `clients[0].url` to the hub IP if different.
   - Run as systemd service or container; verify positions file path exists.

3. **Structured Logging in Code**
   - Python logging should emit JSON (follow-up change: add JSON formatter).
   - Edge agents must output JSON lines to `/var/log/edge-agent/edge-agent.log`.
   - Include `service`, `site`, and `device_id` labels inside log message for
     easier querying.

4. **Grafana Integration**
   - Add Loki datasource pointing to `http://10.0.0.10:3100`.
   - Build dashboards (`logging-dash` task) with log panels and saved queries.

## Next Actions

- Update application logging configuration to JSON format.
- Provide systemd unit files for Loki and Promtail.
- Harden transport with HTTPS/TLS (post-proof-of-concept).
- Automate deployment via Ansible/Flux once config is validated (`config-mgmt`).
