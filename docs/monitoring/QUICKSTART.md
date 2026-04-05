# Monitoring Stack Quickstart

**Date:** 2025-12-10
**Status:** ✅ Fully Operational

## Overview
Complete monitoring stack for Devices MCP:
- **Grafana**: Visualization dashboards
- **Prometheus**: Metrics collection
- **Loki**: Log aggregation
- **Promtail**: Log shipping

## Prerequisites
- Docker Desktop installed
- `myhomecontrol` network created
- `myhomecontrol_app_logs` volume created
- Devices MCP running locally on port `7777` (default from `config.yaml`)

## Quick Setup

### 1. Create Network and Volume

```powershell
# Create Docker network (if not exists)
docker network create myhomecontrol

# Create log volume (if not exists)
docker volume create myhomecontrol_app_logs
```

### 2. Start the Stack

```powershell
# From the repository root
cd deploy\monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

## Services

- **Grafana**: `http://localhost:3001` (admin/admin)
- **Prometheus**: `http://localhost:9095`
- **Loki**: `http://localhost:3101`
- **Promtail**: Internal only (no web UI)

**Note**: Non-standard ports used to avoid conflicts with `myai-*` containers.

## Prometheus Scraping
Prometheus is preconfigured to scrape the MCP server metrics at `http://host.docker.internal:7777/metrics` using the consolidated config at `deploy\prometheus\prometheus.yaml` (mounted by the compose file).

Ensure the MCP web server is running and exposes `/metrics`. This repo's `src\devices_mcp\web\server.py` provides the endpoint.

## Grafana
Grafana is pre-provisioned with:
- Prometheus datasource
- Loki datasource
- Tapo P115 dashboard
- Alert rules for CO2 and power spikes

**Login**: http://localhost:3001 (admin/admin)

**Navigate to**:
- Dashboards → Manage → `Tapo P115 Overview`
- Explore → Loki → Query: `{job="devices-mcp"}`

## Log Shipping
Promtail automatically ships logs from:
- Docker container logs (`/var/log/devices-mcp/*.log`)
- Native Windows logs (`/var/log/devices-mcp-host/tapo_mcp.log`)

Logs are available in Grafana Explore → Loki.

## Stop the Stack

```powershell
cd deploy\monitoring
docker compose -f docker-compose.monitoring.yml down
```

## Verify Status

```powershell
# Check all containers
docker ps --filter "name=monitoring" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health checks
curl http://localhost:3101/ready  # Loki
curl http://localhost:9095/-/healthy  # Prometheus
curl http://localhost:3001/api/health  # Grafana
```

## Troubleshooting

See `docs/monitoring/SETUP.md` for detailed troubleshooting guide.

## Notes
- If running MCP on a different host/port, update `deploy\prometheus\prometheus.yaml` target.
- Windows users: `host.docker.internal` resolves the host from inside containers.
- Port conflicts resolved: Grafana (3001), Prometheus (9095), Loki (3101)
- All deprecated configs have been updated for latest versions
