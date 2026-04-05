# Logging Dashboard Notes (2025-11-12)

- Dashboard: `grafana/provisioning/dashboards/logging-overview.json`
- Datasource: `Loki` (`grafana/provisioning/datasources/loki.yaml`)
- Panels:
  - Camera MCP log stream (live feed).
  - Edge agent log stream.
  - Log volume by severity (`count_over_time` aggregation).
- Extend by adding filters for `service`, `site`, and Alertmanager linkouts.

Prerequisites:

- Promtail must label logs with `app` and optional `site`.
- Loki accessible at `http://10.0.0.10:3100`.
- Ensure Grafana has permission to query Loki.
