# Operations Runbook (2025-11-12)

## 1. Service Overview

- **devices-mcp**: FastAPI + MCP control plane (`systemctl status devices-mcp`).
- **Observability stack**: Prometheus (9090), Loki (3100), Alertmanager (9093), Promtail (9080).
- **Edge agents**: Collectors running per site, exposing metrics on 9400 and logs under `/var/log/edge-agent`.

## 2. Deployment Steps

1. Update repository and run Ansible playbook:
   ```bash
   ansible-playbook -i inventory/production.ini infrastructure/ansible/playbooks/observability.yaml
   ```
2. Restart core services:
   ```bash
   sudo systemctl restart devices-mcp prometheus loki promtail alertmanager
   ```
3. Verify health via CI observability checks or Grafana dashboards.

## 3. Incident Response

| Symptom | Checks | Remediation |
|---------|--------|-------------|
| Dashboard blank / metrics missing | `systemctl status prometheus`; `journalctl -u prometheus` | Restart Prometheus, ensure `promtool check config` passes. |
| Camera offline | Check network connectivity to camera IP; view `/api/cameras` | Power-cycle camera; ensure credentials valid. |
| Logs missing in Grafana | Inspect Promtail logs `/var/log/edge-agent/*.log`; Loki ingestion metrics | Restart Promtail; verify Loki config (`docker run grafana/loki ... -verify-config`). |
| Alert flood | Inspect Alertmanager UI (`http://hub:9093`); mute alerts if necessary | Adjust alert thresholds in `deploy/prometheus/alerts/`; run `promtool check rules`. |

## 4. Scaling Guidance

- For additional edge nodes:
  1. Deploy edge agent using Ansible role (future task).
  2. Add targets in `deploy/prometheus/targets/edge-agents/`.
  3. Configure Promtail on node with site label.
  4. Reload Prometheus (`/-/reload` endpoint) or restart service.

- For storage expansion (Loki/Prometheus):
  - Ensure new volumes mounted under `/var/lib/loki` / `/var/lib/prometheus`.
  - Update retention in configuration files.

## 5. Contact & Escalation

- Primary on-call: Home Security Ops team (`ops@example.com`, Slack `#home-security-ops`).
- Critical pager webhook triggered by `severity=critical` alerts.

## 6. References

- `docs/mcp-technical/LOKI_PROMTAIL_PLAN.md`
- `docs/mcp-technical/PROMETHEUS_FEDERATION_PLAN.md`
- `docs/mcp-technical/ALERTING_PLAN.md`
- `docs/mcp-technical/CHAOS_TEST_PLAN.md`
