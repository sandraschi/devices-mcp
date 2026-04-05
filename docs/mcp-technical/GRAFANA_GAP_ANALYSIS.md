# Grafana Coverage Gap Analysis (2025-11-12)

## Objective

Evaluate current Grafana assets (`grafana/` directory and documentation) versus
the target experience: unified real-time monitoring for cameras, sensors, logs,
and infrastructure health. This feeds the `gap-review` task and informs upcoming
dashboard & observability work.

## Current Assets

- **Dashboards**
  - `tapo-camera-dashboard.json`: focuses on camera health, stream preview
    placeholders, and PTZ controls pulling from mock metrics/datasources.
  - `tapo-ptz-dashboard.json` (plus plugin-specific `dashboards/*.json`):
    showcases PTZ operations and stream embedding via the custom panel.
- **Custom Plugin**
  - `grafana/plugins/tapo-camera-stream`: custom panel for embedding camera
    streams (WebRTC/MJPEG) with PTZ controls.
- **Documentation**
  - `docs/GRAFANA_INTEGRATION_OVERVIEW.md`: high-level goals (camera status,
    motion alerts, live feeds).
  - `docs/GRAFANA_INTEGRATION_DETAILED.md`: architecture for HTTP metrics
    endpoint and JSON datasource.
  - `docs/WINDSURF_GRAFANA_IMPLEMENTATION.md`: environment-specific setup notes.

## Requirements Snapshot

From roadmap and user directives:

1. **Replace mock data** with real sensor/camera metrics.
2. **Live camera dashboard** with health metrics and quick controls.
3. **Sensor status dashboard** (energy, environmental, alarm systems).
4. **Logging dashboard** built on Loki/Promtail with full-text search and alert
   drill-down.
5. **Unified monitoring** (Prometheus + Grafana) with distributed nodes.
6. **Mobile/desktop usability** for critical dashboards (`user-flows` task).

## Gap Assessment

| Area                     | Current State                                   | Gap Description | Blocking Dependencies |
|--------------------------|-------------------------------------------------|-----------------|-----------------------|
| Datasource wiring        | Dashboards reference JSON/mock datasources.     | No Prometheus/Loki endpoints; manual editing required. | `prometheus-setup`, `logging-stack` |
| Camera health metrics    | Panels use stub metrics; no live scrape.        | Need real-time data from `metrics_service` exposed via Prometheus. | `unify-ingest`, `sensor-api` |
| Sensor coverage          | No dashboards for Nest Protect, Ring, Tapo P115, Netatmo. | Build new panels once ingestion delivers metrics. | `unify-ingest`, `sensor-api` |
| Logging visibility       | No Loki datasource or log panels.               | Deploy Loki/Promtail and author log exploration dashboards. | `logging-stack` |
| Alert visibility         | Alert widgets absent.                           | Add alert list panels and integrate Alertmanager. | `alerting` |
| Mobile UX                | Layout optimized for desktop (grid units).      | Need responsive rows / viewport rules per dashboard. | `user-flows` |
| Provisioning automation  | Dashboards stored as JSON snapshots only.       | Create Grafana provisioning files (`provisioning/dashboards/*.yaml`). | `config-mgmt`, `ci-cd` |
| Secrets & auth           | Datasource credentials handled manually.        | Integrate with secrets management (e.g., environment vars, Vault). | `secrets-hardening` |

## Recommended Actions

1. **Datasource Strategy**
   - Define Prometheus & Loki datasource IDs; update dashboard JSON or create
     provisioning definitions referencing the IDs.
   - Include health checks for datasource connectivity.

2. **Dashboard Workstreams**
   - `camera-dash`: Revise `tapo-camera-dashboard.json` to bind to Prometheus metrics (uptime, motion, stream bitrate) and embed live video via plugin.
   - `sensor-dash`: New dashboard aggregating Nest Protect, Tapo P115, Netatmo telemetry with threshold panels.
   - `logging-dash`: New dashboard referencing Loki queries for error counts, recent alerts, and drill-down views.

3. **Observability Integration**
   - Update `metrics_service` to expose OpenMetrics endpoint; document scrape path.
   - Instrument MCP services to emit structured logs (JSON) consumable by Promtail.

4. **UX Enhancements**
   - Apply Grafana grid breakpoints and collapsible panels for small screens.
   - Provide navigation insights (home dashboard with links to specialized views).

5. **Operationalizing Dashboards**
   - Store dashboards and datasources in `grafana/provisioning/` with IaC-friendly YAML.
   - Add CI checks ensuring JSON dashboards load (e.g., `grafana-toolkit validate`).

## Next Steps for `gap-review`

- Confirm required metric names & labels with ingestion team so dashboard queries can be drafted.
- Draft Prometheus recording rules for high-value KPIs (camera availability, sensor heartbeat).
- Outline data model expectations for each dashboard to inform `sensor-api` and `edge-agents`.

_Prepared on 2025-11-12 to support the ongoing observability rollout._
