# Sensor Dashboard Notes (2025-11-12)

- Dashboard: `grafana/provisioning/dashboards/sensor-overview.json`
- Metrics expected:
  - `tapo_p115_power_watts`
  - `tapo_p115_daily_cost`
  - `tapo_p115_energy_today_kwh`
- Variable supports filtering by `instance` (edge node).
- Refresh interval: 1 minute.

Action items:

1. Extend edge ingestion pipeline to publish Prometheus metrics with the above
   names.
2. Add Nest Protect and Netatmo panels once ingestion adapters are wired.
3. Surface Promtail/Loki log count panels for anomaly detection.
