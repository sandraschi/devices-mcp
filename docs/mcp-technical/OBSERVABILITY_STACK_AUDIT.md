# Observability Stack Audit (2025-11-12)

This document maps the current state of monitoring and logging services for the
home control / surveillance deployment. It identifies which components are
running, where they live, and the immediate gaps that must be closed for the
end-to-end observability plan.

## 1. Summary

- **Central Application Host:** `devices-mcp` (FastAPI + MCP server) on the
  home lab hub. Provides REST endpoints, live dashboard, and preliminary metrics.
- **Active Observability Components:** Application exposes `/api/status` and
  camera metrics stubs; structured logging is limited to local log files /
  console. Grafana dashboards rely on static JSON exports; no live Prometheus /
  Loki backend is wired.
- **Missing Core Services:** Prometheus (scrape targets), Loki (central log
  store), Promtail (agent), Alertmanager, and configuration management for
  distributed nodes are not yet deployed.

## 2. Service Inventory

| Service / Role             | Host / Node        | Status          | Notes |
|----------------------------|--------------------|-----------------|-------|
| `devices-mcp` web/API  | Central hub        | Running         | FastAPI app reachable on `http://localhost:7777`; emits JSON status and camera data. |
| Metrics endpoint (`/metrics` via `metrics_service`) | Central hub | Prototype | Module available but not registered with Prometheus; needs adapter to expose OpenMetrics format. |
| Grafana (local workstation)| Developer machine  | Available (manual) | Dashboards exist as JSON exports in `grafana/`; no automated provisioning or live datasource binding. |
| Prometheus                 | _Not deployed_     | Missing         | Scrape targets and federation plan pending (`prometheus-setup` task). |
| LOki                       | _Not deployed_     | Missing         | No centralized log retention; local logs remain on application host. |
| Promtail agents            | _Not deployed_     | Missing         | Required on each edge node once Loki is provisioned. |
| Alertmanager               | _Not deployed_     | Missing         | Alert routing depends on Prometheus metrics and Loki log rules. |
| Node Exporter / Edge metrics | _Not deployed_   | Missing         | Will accompany `edge-agents` design. |
| Log shipping (Ring/Nest MCPs) | Individual MCP nodes | TBD | Each MCP server currently handles local logging only. Consolidation pending. |

## 3. Node Responsibilities

- **Central Hub (Primary server):**
  - Runs the unified dashboard and will host Prometheus, Alertmanager, and Loki.
  - Stores Grafana provisioning manifests and dashboard JSON.
  - Must expose scrape targets for internal metrics and downstream MCP services.

- **Edge Nodes (per camera / sensor cluster):**
  - Future home for Promtail + Node Exporter + custom `edge-agent`.
  - Responsible for forwarding device telemetry and system logs upstream.

- **Cloud Integrations (Ring, Nest, Petcube APIs):**
  - Produce event streams via respective MCP connectors.
  - Need webhook/poll adapters to convert into Prometheus metrics and Loki log events.

## 4. Gaps & Immediate Actions

1. **Prometheus Bootstrapping**
   - Define scrape configs for:
     - `devices-mcp` internal metrics (`/metrics` once exposed).
     - Edge exporters (placeholders until agents exist).
     - External MCP services (Ring, Nest) via push gateway or exporters.
   - Provision Prometheus on the central hub with persistent storage.

2. **Logging Pipeline**
   - Package structured logs (JSON) from `devices_mcp` using Python logging
     handlers; feed into Promtail.
   - Deploy Loki (single instance acceptable initially) and point Promtail agents.
   - Ensure log labels cover `device`, `site`, `severity`, and `service`.

3. **Grafana Datasource Wiring**
   - Automate datasource configuration for Prometheus and Loki once available.
   - Convert existing JSON dashboards (`grafana/tapo-camera-dashboard.json`) into
     provisioned dashboards referencing real datasources.

4. **Alerting & Notifications**
   - Prepare Alertmanager route map (critical alerts → mobile push / SMS,
     warnings → email/Teams).
   - Define initial alert rules (camera offline, sensor stale metrics, log
     critical errors).

5. **Configuration Management**
   - Decide on IaC tooling (Ansible, Terraform, or just GitOps manifests) to keep
     Prometheus/Loki/Promtail configs synchronized across nodes.

## 5. Dependencies for Upcoming Tasks

- Outputs here feed directly into:
  - `gap-review`: use the inventory above to check Grafana coverage vs. desired dashboards.
  - `unify-ingest`: ensures real sensor feeds align with metrics/log pipelines.
  - `edge-agents`: build collectors consistent with Prometheus/Loki expectations.
  - `config-mgmt`: incorporate service configs into automation repo.

## 6. Next Steps

- Finalize Prometheus deployment design (`prometheus-setup`).
- Draft Loki/Promtail topology and select log retention policy (`logging-stack`).
- Generate Grafana provisioning bundles targeting the new datasources (`camera-dash`, `sensor-dash`, `logging-dash`).
- Iterate on alert scenarios and integrate with Alertmanager (`alerting`).

_Prepared by the observability working group (automated assistant) on 2025-11-12._
