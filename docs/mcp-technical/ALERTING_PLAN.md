# Alerting Plan (2025-11-12)

## Alertmanager Setup

- Configuration: `deploy/alertmanager/alertmanager.yaml`
- Default receiver: email notifications to ops mailbox.
- Escalations:
  - `severity=critical` → Pager webhook (e.g., OpsGenie/ntfy).
  - `severity=warning` → Slack channel `#home-security-ops`.
- Grouping keys: `alertname`, `service`, `site`.

## Key Alerts

- Camera offline detection (`CameraOffline` rule in Prometheus).
- Edge agent scrape delays (`EdgeAgentMissedScrape` rule).
- Additional rules to add:
  - Loki ingestion errors (from Promtail metrics).
  - Sensor heartbeat missing (Tapo P115 last_seen > 5m).
  - Dashboard datasource health (Grafana datasource status).

## Action Items

1. Provision Alertmanager on hub (systemd or container).
2. Configure secrets for email/Slack/webhook in environment variables or secret
   store (ties into `secrets-hardening` task).
3. Update Prometheus `prometheus.yaml` to reference Alertmanager endpoint.
4. Develop alert runbooks (`runbooks` task) detailing remediation steps.
5. Add synthetic alert tests (e.g., `promtool test rules`) and integrate into CI.
