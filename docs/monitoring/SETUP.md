# Monitoring Stack Setup Guide

**Date:** 2025-12-10
**Status:** ✅ Fully Operational

## Overview

Complete monitoring stack integration for Devices MCP:
- **Grafana**: Visualization and dashboards
- **Prometheus**: Metrics collection
- **Loki**: Log aggregation
- **Promtail**: Log shipping

## Prerequisites

1. Docker and Docker Compose installed
2. `myhomecontrol` network exists
3. `myhomecontrol_app_logs` volume exists

## Quick Start

### 1. Create Network and Volume

```powershell
# Create Docker network (if not exists)
docker network create myhomecontrol

# Create log volume (if not exists)
docker volume create myhomecontrol_app_logs
```

### 2. Start Monitoring Stack

```powershell
cd deploy\monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

### 3. Verify Status

```powershell
# Check all containers
docker ps --filter "name=monitoring" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected output:
# NAMES                   STATUS          PORTS
# monitoring-loki         Up X minutes    0.0.0.0:3101->3100/tcp
# monitoring-grafana     Up X minutes    0.0.0.0:3001->3000/tcp
# monitoring-promtail     Up X minutes
# monitoring-prometheus   Up X minutes    0.0.0.0:9095->9090/tcp
```

### 4. Access Services

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9095
- **Loki**: http://localhost:3101

## Configuration Details

### Port Assignments

| Service | Port | URL |
|---------|------|-----|
| Grafana | 3001 | http://localhost:3001 |
| Prometheus | 9095 | http://localhost:9095 |
| Loki | 3101 | http://localhost:3101 |
| Promtail | 9080 | Internal only |

**Note**: Non-standard ports used to avoid conflicts with `myai-*` containers.

### Volume Mounts

- **Promtail** mounts:
  - `myhomecontrol_app_logs:/var/log/devices-mcp:ro` (Docker logs)
  - `D:\Dev\repos\devices-mcp:/var/log/devices-mcp-host:ro` (Native logs)

### Network Configuration

- **Monitoring network**: `monitoring` (internal)
- **App network**: `myhomecontrol` (shared with app containers)
- **Promtail** connected to both networks for log access

## Troubleshooting

### Containers Not Starting

1. **Check network exists**:
   ```powershell
   docker network ls | Select-String "myhomecontrol"
   ```

2. **Check volume exists**:
   ```powershell
   docker volume ls | Select-String "myhomecontrol_app_logs"
   ```

3. **Check logs**:
   ```powershell
   docker logs monitoring-loki
   docker logs monitoring-prometheus
   docker logs monitoring-grafana
   docker logs monitoring-promtail
   ```

### Loki Not Ready

Loki may take 15-30 seconds to become ready after startup. Check:
```powershell
curl http://localhost:3101/ready
```

Expected: `Ingester not ready: waiting for 15s after being ready` (then becomes ready)

### Promtail Not Shipping Logs

1. **Check Promtail is watching directories**:
   ```powershell
   docker logs monitoring-promtail | Select-String "Adding target|watching"
   ```

2. **Check volume mount**:
   ```powershell
   docker exec monitoring-promtail ls -la /var/log/devices-mcp/
   ```

3. **Check Loki connectivity**:
   ```powershell
   docker logs monitoring-promtail | Select-String "error|Error|ERROR"
   ```

### Grafana Not Starting

Check alert rule configuration:
```powershell
docker logs monitoring-grafana | Select-String "invalid|error|Error"
```

Common issues:
- Invalid `relativeTimeRange` in alert rules (should have `from: 300, to: 0`)
- Missing datasource configuration

### Prometheus Config Errors

Check for deprecated config:
```powershell
docker logs monitoring-prometheus | Select-String "federation|error|Error"
```

**Fix**: Remove or comment out `federation` section (not supported in Prometheus 2.x)

## Health Checks

### Manual Health Verification

```powershell
# Loki
curl http://localhost:3101/ready

# Prometheus
curl http://localhost:9095/-/healthy

# Grafana
curl http://localhost:3001/api/health
```

### Container Health

```powershell
# All containers
docker ps --filter "name=monitoring" --format "table {{.Names}}\t{{.Status}}"

# Individual container logs
docker logs monitoring-loki --tail 20
docker logs monitoring-promtail --tail 20
docker logs monitoring-prometheus --tail 20
docker logs monitoring-grafana --tail 20
```

## Log Queries

### Grafana Explore (Loki)

```logql
# All logs
{job="devices-mcp"}

# Docker deployment only
{job="devices-mcp", deployment="docker"}

# Errors only
{job="devices-mcp"} | json | level="ERROR"

# Server startup
{job="devices-mcp"} | json | message=~".*Starting.*"
```

### Prometheus Queries

```promql
# Server uptime
up{job="tapo_home"}

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

## Maintenance

### Restart All Services

```powershell
cd deploy\monitoring
docker compose -f docker-compose.monitoring.yml restart
```

### Stop All Services

```powershell
cd deploy\monitoring
docker compose -f docker-compose.monitoring.yml down
```

### Update Configuration

1. Edit config files in `deploy/` directories
2. Restart affected service:
   ```powershell
   docker compose -f docker-compose.monitoring.yml restart <service-name>
   ```

### Clean Up

```powershell
# Stop and remove containers
docker compose -f docker-compose.monitoring.yml down

# Remove volumes (WARNING: deletes all data)
docker volume rm monitoring_grafana_data monitoring_prometheus_data monitoring_loki_data monitoring_alertmanager_data
```

## Summary

✅ **Network**: `myhomecontrol` network created
✅ **Volume**: `myhomecontrol_app_logs` volume created
✅ **Ports**: Non-conflicting ports configured (3001, 9095, 3101)
✅ **Configs**: All deprecated configs fixed
✅ **Alert Rules**: Valid time ranges configured
✅ **Log Shipping**: Promtail watching both Docker and native logs

The monitoring stack is ready for production use! 🎉
