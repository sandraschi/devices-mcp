# Docker Logging Integration - Grafana, Prometheus, Loki, Promtail

**Date:** 2025-12-10
**Status:** ✅ Fully Operational
**Last Updated:** 2025-12-10

## Overview

The Devices MCP dashboard now properly integrates with the full Docker monitoring stack:
- **Grafana**: Visualization dashboards
- **Prometheus**: Metrics scraping
- **Loki**: Log aggregation
- **Promtail**: Log shipping

## Logging Architecture

### Native Windows Mode
- Logs to console (stdout) with standard format
- Logs to `tapo_mcp.log` file in project root
- Human-readable format for debugging

### Docker Mode
- **JSON format** for structured logging (Loki/Promtail compatible)
- Logs to **stdout/stderr** (Docker json-file driver)
- Logs to **mounted volume** `/app/logs/tapo_mcp.log` (Promtail file scraping)
- Automatic Docker detection via `CONTAINER=yes` env var or `/.dockerenv` file

## Docker Compose Configuration

### myhomecontrol/docker-compose.yml
```yaml
services:
  app:
    environment:
      - CONTAINER=yes  # Signals Docker mode to logging system
    volumes:
      - app_logs:/app/logs  # Logs accessible to Promtail
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service,app,location"
        tag: "{{.Name}}/{{.ID}}"
```

### monitoring/docker-compose.monitoring.yml
```yaml
services:
  promtail:
    volumes:
      # Mount Docker volume from myhomecontrol stack
      - myhomecontrol_app_logs:/var/log/devices-mcp:ro
      # Also mount host directory for native logs
      - D:\Dev\repos\devices-mcp:/var/log/devices-mcp-host:ro
    networks:
      - monitoring
      - myhomecontrol  # Access app_logs volume
```

## Promtail Configuration

### promtail-config.yaml
- **Docker logs**: Reads from `/var/log/devices-mcp/*.log` (Docker volume)
- **Native logs**: Reads from `/var/log/devices-mcp-host/tapo_mcp.log` (host mount)
- **JSON parsing**: Automatically parses structured JSON logs
- **Labels**: Adds `deployment`, `location`, `app`, `job` labels for filtering

## JSON Log Format (Docker)

```json
{
  "timestamp": "2025-12-10T12:00:00Z",
  "level": "INFO",
  "logger": "devices_mcp.web.server",
  "message": "Starting web server on http://0.0.0.0:7777",
  "module": "server",
  "function": "run",
  "line": 2666,
  "category": "system",
  "source": "web_server",
  "severity": "info",
  "details": {
    "host": "0.0.0.0",
    "port": 7777
  }
}
```

## Grafana Queries

### LogQL (Loki)
```logql
# All logs from Docker deployment
{job="devices-mcp", deployment="docker"}

# Errors only
{job="devices-mcp"} | json | level="ERROR"

# Server startup events
{job="devices-mcp"} | json | message=~".*Starting.*"

# Device connection issues
{job="devices-mcp"} | json | category="device_connection" | severity!="info"

# Specific device
{job="devices-mcp"} | json | source="camera_kitchen_cam"
```

### PromQL (Prometheus)
```promql
# Server uptime
up{job="tapo_home"}

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

## Startup Logging

Server now logs comprehensive startup information:
```
================================================================================
Devices MCP Web Server - Starting
Python: 3.11.x
Platform: linux (Docker) or win32 (Native)
Working directory: /app (Docker) or D:\Dev\repos\devices-mcp (Native)
Log file: /app/logs/tapo_mcp.log (Docker) or tapo_mcp.log (Native)
================================================================================
```

## Verification

### Check Docker Logs
```powershell
# View container logs (stdout/stderr)
docker logs myhomecontrol-app

# Follow logs
docker logs -f myhomecontrol-app

# Check log volume
docker volume inspect myhomecontrol_app_logs
```

### Check Promtail
```powershell
# View Promtail logs
docker logs monitoring-promtail

# Check if logs are being scraped
docker exec monitoring-promtail cat /tmp/positions.yaml
```

### Check Loki
```powershell
# Query Loki API
curl http://localhost:3100/ready

# Query logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="devices-mcp"}' \
  --data-urlencode 'limit=10'
```

### Check Grafana
1. Open http://localhost:3000
2. Go to Explore → Loki
3. Query: `{job="devices-mcp"}`
4. Should see structured JSON logs

## Troubleshooting

### Logs Not Appearing in Loki
1. **Check Promtail is running**: `docker ps | findstr promtail`
2. **Check volume mount**: `docker exec monitoring-promtail ls -la /var/log/devices-mcp/`
3. **Check Promtail config**: `docker exec monitoring-promtail cat /etc/promtail/config.yml`
4. **Check Promtail logs**: `docker logs monitoring-promtail`

### JSON Parsing Errors
- Ensure logs are in valid JSON format
- Check for unescaped characters in log messages
- Verify timestamp format is RFC3339

### Volume Access Issues
- Ensure `myhomecontrol_app_logs` volume exists
- Check network connectivity between Promtail and myhomecontrol stack
- Verify volume is mounted correctly in Promtail container

## Monitoring Stack Setup

### Prerequisites
1. **Docker Network**: `myhomecontrol` network must exist
   ```powershell
   docker network create myhomecontrol
   ```

2. **Log Volume**: `myhomecontrol_app_logs` volume must exist
   ```powershell
   docker volume create myhomecontrol_app_logs
   ```

### Starting the Monitoring Stack

```powershell
cd deploy\monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

### Port Configuration

The monitoring stack uses non-standard ports to avoid conflicts with existing services:

- **Grafana**: `3001` (instead of 3000) - http://localhost:3001
- **Prometheus**: `9095` (instead of 9090) - http://localhost:9095
- **Loki**: `3101` (instead of 3100) - http://localhost:3101
- **Promtail**: `9080` (internal only)

**Note**: Port conflicts with `myai-*` containers are automatically avoided.

### Configuration Fixes Applied

#### Loki Configuration (`deploy/loki/loki-config.yaml`)
- ✅ Fixed `path_prefix` to use `/loki` volume mount
- ✅ Fixed storage directory to `/loki/chunks`
- ✅ Removed deprecated `ingestion_burst_mb` (replaced with `ingestion_burst_size_mb`)
- ✅ Removed deprecated `max_look_back_period` from `chunk_store_config`

#### Prometheus Configuration (`deploy/prometheus/prometheus.yaml`)
- ✅ Removed deprecated `federation` section (not supported in Prometheus 2.x)
- ✅ Commented out federation config with explanation

#### Grafana Alert Rules
- ✅ Fixed `environment-co2-alerts.yaml`: Added `relativeTimeRange` (from: 300, to: 0)
- ✅ Fixed `p115-power-spike-alerts.yaml`: Added `relativeTimeRange` (from: 300, to: 0)
- ✅ All alert queries now have valid time ranges

#### Promtail Configuration (`deploy/promtail/promtail-config.yaml`)
- ✅ Updated Loki URL to `http://monitoring-loki:3100` (container name)
- ✅ Fixed positions file path to `/tmp/positions.yaml` (writable location)
- ✅ Configured to scrape both Docker volume and native host logs

### Container Status

Check all containers:
```powershell
docker ps --filter "name=monitoring" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:
```
NAMES                   STATUS          PORTS
monitoring-loki         Up X minutes    0.0.0.0:3101->3100/tcp
monitoring-grafana      Up X minutes    0.0.0.0:3001->3000/tcp
monitoring-promtail     Up X minutes
monitoring-prometheus   Up X minutes    0.0.0.0:9095->9090/tcp
```

### Health Checks

```powershell
# Loki readiness
curl http://localhost:3101/ready

# Prometheus health
curl http://localhost:9095/-/healthy

# Grafana health
curl http://localhost:3001/api/health
```

### Access URLs

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9095
- **Loki**: http://localhost:3101
- **Promtail**: Internal only (no web UI)

## Summary

✅ **Docker detection**: Automatic via `CONTAINER=yes` or `/.dockerenv`
✅ **JSON logging**: Structured logs for Loki/Promtail
✅ **Dual output**: stdout (Docker driver) + file (Promtail scraping)
✅ **Volume sharing**: `app_logs` volume accessible to Promtail
✅ **Network integration**: Promtail connected to `myhomecontrol` network
✅ **Startup logging**: Comprehensive server startup information
✅ **Native support**: Still works in native Windows mode
✅ **Port conflicts**: Resolved (Grafana: 3001, Prometheus: 9095, Loki: 3101)
✅ **Config fixes**: All deprecated configs updated for latest versions
✅ **Alert rules**: Fixed invalid time ranges in Grafana alerts

The monitoring stack is now fully operational! 🎉
