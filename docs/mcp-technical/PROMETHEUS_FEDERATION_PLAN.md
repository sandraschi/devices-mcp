# Prometheus Federation Plan (2025-11-12)

## Objectives

- Stand up a central Prometheus instance on the home lab hub.
- Federate metrics from edge nodes (mini PCs, camera hubs) and satellite MCP
  deployments.
- Feed Grafana dashboards and Alertmanager rules with consistent labels.

## Deployment Layout

| Role              | Location              | Notes |
|-------------------|-----------------------|-------|
| Prometheus Core   | Home lab hub (`10.0.0.10`) | Runs configuration in `deploy/prometheus/prometheus.yaml`. |
| Federation Targets| Remote Prometheus nodes (`10.0.0.11`, `10.0.0.12`) | Aggregated via `federation.targets` list. |
| Edge Agents       | Per camera cluster     | Expose `/metrics` on port `9400` (through new edge collectors). |
| Node Exporter     | Each edge node         | Standard port `9100`; discovered via file-based service discovery. |

## Configuration Artifacts

- **Prometheus config**: `deploy/prometheus/prometheus.yaml`
  - Defines scrape jobs for control plane, edge agents, and node exporters.
  - Pulls in alert rules from `deploy/prometheus/alerts/tapo_camera_rules.yml`.
  - Supports file-based service discovery for dynamic edge agent scaling.
- **Targets**:  `deploy/prometheus/targets/*/example.yaml`
  - Provide templates for listing edge agents and node exporters.

## Action Items

1. Install Prometheus (>= 2.52) on the hub (systemd or container).
2. Populate `targets/edge-agents/` and `targets/node-exporter/` with actual node
   addresses.
3. Build the edge agent exporter to expose aggregated metrics on port `9400`.
4. Wire Alertmanager (next task) to consume alerts from the new rule file.
5. Update Grafana datasources to point at the new Prometheus endpoint.
6. Add CI validation (linting + `promtool check config`) once the config is
   finalized (`ci-cd` task).
