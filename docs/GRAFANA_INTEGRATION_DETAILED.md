# Grafana Integration - Detailed Implementation Guide

**Project**: devices-mcp
**Target**: Grafana 10.x+ integration
**Timeline**: 2-3 days
**Created**: 2025-09-03

## Architecture Overview

### Data Flow Design
```
Tapo Cameras → devices-mcp → HTTP Metrics Endpoint → Grafana JSON Data Source → Dashboards → Alerts
```

### Core Components
1. **Metrics Collection Service** - Extends existing MCP server
2. **HTTP Metrics API** - RESTful endpoint for Grafana
3. **Grafana Configuration** - Data sources and dashboards
4. **Alert Management** - Notification system

## Phase 1: Metrics Collection Implementation

### 1.1 Add Metrics Service to MCP Server

**File**: `src/devices_mcp/metrics_service.py`

```python
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

@dataclass
class CameraMetrics:
    """Camera metrics data structure"""
    camera_id: str
    name: str
    ip_address: str
    model: str
    firmware: str
    status: str  # online, offline, error
    last_seen: datetime
    uptime_seconds: int
    temperature: Optional[float]
    motion_detected: bool
    motion_last_detected: Optional[datetime]
    motion_events_count: int
    network_latency_ms: float
    signal_strength: Optional[int]
    recording_status: str
    storage_used_mb: float
    storage_total_mb: float

class MetricsCollector:
    """Collect and aggregate camera metrics"""

    def __init__(self, tapo_client):
        self.tapo_client = tapo_client
        self.metrics_history: Dict[str, List[CameraMetrics]] = {}
        self.current_metrics: Dict[str, CameraMetrics] = {}
        self.collection_interval = 30  # seconds
        self.history_retention_hours = 24

    async def start_collection(self):
        """Start periodic metrics collection"""
        while True:
            await self.collect_all_cameras()
            await asyncio.sleep(self.collection_interval)

    async def collect_all_cameras(self):
        """Collect metrics from all configured cameras"""
        cameras = await self.tapo_client.get_all_cameras()

        for camera in cameras:
            try:
                metrics = await self.collect_camera_metrics(camera)
                self.current_metrics[camera.id] = metrics
                self.store_historical_metrics(camera.id, metrics)
            except Exception as e:
                print(f"Error collecting metrics for {camera.id}: {e}")

    async def collect_camera_metrics(self, camera) -> CameraMetrics:
        """Collect metrics for a single camera"""
        # Get device info
        device_info = await camera.get_device_info()

        # Get motion detection status
        motion_detection = await camera.get_motion_detection()

        # Network performance test
        start_time = datetime.now()
        await camera.get_device_info()  # Simple ping test
        latency = (datetime.now() - start_time).total_seconds() * 1000

        # Storage info (if available)
        try:
            storage_info = await camera.get_storage_info()
            storage_used = storage_info.get('used_mb', 0)
            storage_total = storage_info.get('total_mb', 0)
        except:
            storage_used = storage_total = 0

        return CameraMetrics(
            camera_id=camera.id,
            name=device_info.get('device_alias', 'Unknown'),
            ip_address=camera.host,
            model=device_info.get('device_model', 'Unknown'),
            firmware=device_info.get('sw_version', 'Unknown'),
            status='online' if device_info else 'offline',
            last_seen=datetime.now(),
            uptime_seconds=device_info.get('on_time', 0),
            temperature=device_info.get('device_temperature', None),
            motion_detected=motion_detection.get('enabled', False),
            motion_last_detected=self.get_last_motion_time(camera.id),
            motion_events_count=self.get_motion_events_count(camera.id),
            network_latency_ms=latency,
            signal_strength=device_info.get('rssi', None),
            recording_status=device_info.get('recording_mode', 'unknown'),
            storage_used_mb=storage_used,
            storage_total_mb=storage_total
        )

    def store_historical_metrics(self, camera_id: str, metrics: CameraMetrics):
        """Store metrics in history with retention"""
        if camera_id not in self.metrics_history:
            self.metrics_history[camera_id] = []

        self.metrics_history[camera_id].append(metrics)

        # Clean old data
        cutoff_time = datetime.now() - timedelta(hours=self.history_retention_hours)
        self.metrics_history[camera_id] = [
            m for m in self.metrics_history[camera_id]
            if m.last_seen > cutoff_time
        ]

    def get_grafana_metrics(self) -> Dict[str, Any]:
        """Format metrics for Grafana consumption"""
        timestamp = datetime.now().isoformat()

        metrics = {
            "timestamp": timestamp,
            "cameras": {}
        }

        for camera_id, camera_metrics in self.current_metrics.items():
            metrics["cameras"][camera_id] = {
                "name": camera_metrics.name,
                "status": camera_metrics.status,
                "uptime_seconds": camera_metrics.uptime_seconds,
                "temperature": camera_metrics.temperature,
                "motion_detected": camera_metrics.motion_detected,
                "motion_events_count": camera_metrics.motion_events_count,
                "network_latency_ms": camera_metrics.network_latency_ms,
                "signal_strength": camera_metrics.signal_strength,
                "storage_used_percent": (
                    (camera_metrics.storage_used_mb / camera_metrics.storage_total_mb * 100)
                    if camera_metrics.storage_total_mb > 0 else 0
                ),
                "last_seen": camera_metrics.last_seen.isoformat(),
                "model": camera_metrics.model,
                "ip_address": camera_metrics.ip_address,
                "firmware": camera_metrics.firmware
            }

        # Add aggregate metrics
        total_cameras = len(self.current_metrics)
        online_cameras = sum(1 for m in self.current_metrics.values() if m.status == 'online')

        metrics["summary"] = {
            "total_cameras": total_cameras,
            "online_cameras": online_cameras,
            "offline_cameras": total_cameras - online_cameras,
            "motion_active_count": sum(1 for m in self.current_metrics.values() if m.motion_detected),
            "average_latency_ms": sum(m.network_latency_ms for m in self.current_metrics.values()) / max(total_cameras, 1)
        }

        return metrics

# FastAPI HTTP Server for Grafana
class GrafanaMetricsServer:
    """HTTP server providing metrics endpoint for Grafana"""

    def __init__(self, metrics_collector: MetricsCollector, port: int = 8080):
        self.metrics_collector = metrics_collector
        self.port = port
        self.app = FastAPI(title="Tapo Camera Metrics API")

        # Enable CORS for Grafana
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.setup_routes()

    def setup_routes(self):
        """Setup API routes"""

        @self.app.get("/")
        async def health_check():
            return {"status": "healthy", "service": "tapo-camera-metrics"}

        @self.app.get("/metrics")
        async def get_metrics():
            """Main metrics endpoint for Grafana"""
            try:
                return self.metrics_collector.get_grafana_metrics()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/metrics/cameras")
        async def get_camera_list():
            """Get list of all cameras"""
            metrics = self.metrics_collector.get_grafana_metrics()
            return list(metrics.get("cameras", {}).keys())

        @self.app.get("/metrics/cameras/{camera_id}")
        async def get_camera_metrics(camera_id: str):
            """Get metrics for specific camera"""
            metrics = self.metrics_collector.get_grafana_metrics()
            cameras = metrics.get("cameras", {})

            if camera_id not in cameras:
                raise HTTPException(status_code=404, detail="Camera not found")

            return cameras[camera_id]

        @self.app.get("/metrics/history/{camera_id}")
        async def get_camera_history(camera_id: str, hours: int = 1):
            """Get historical metrics for camera"""
            if camera_id not in self.metrics_collector.metrics_history:
                raise HTTPException(status_code=404, detail="Camera not found")

            cutoff_time = datetime.now() - timedelta(hours=hours)
            history = [
                {
                    "timestamp": m.last_seen.isoformat(),
                    "uptime_seconds": m.uptime_seconds,
                    "temperature": m.temperature,
                    "network_latency_ms": m.network_latency_ms,
                    "motion_detected": m.motion_detected,
                    "status": m.status
                }
                for m in self.metrics_collector.metrics_history[camera_id]
                if m.last_seen > cutoff_time
            ]

            return {"camera_id": camera_id, "history": history}

    async def start_server(self):
        """Start the HTTP server"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
```

### 1.2 Integration with Existing MCP Server

**File**: `src/devices_mcp/server.py` (modifications)

```python
# Add to existing imports
from .metrics_service import MetricsCollector, GrafanaMetricsServer
import asyncio
import threading

class TapoCameraMCPServer:
    def __init__(self):
        # ... existing initialization ...

        # Add metrics collection
        self.metrics_collector = MetricsCollector(self.tapo_client)
        self.metrics_server = GrafanaMetricsServer(self.metrics_collector)

        # Start background tasks
        self.start_background_services()

    def start_background_services(self):
        """Start metrics collection and HTTP server in background"""
        # Start metrics collection
        asyncio.create_task(self.metrics_collector.start_collection())

        # Start HTTP server in separate thread
        def run_metrics_server():
            asyncio.run(self.metrics_server.start_server())

        metrics_thread = threading.Thread(target=run_metrics_server, daemon=True)
        metrics_thread.start()
```

### 1.3 Configuration Updates

**File**: `config.yaml` (add metrics section)

```yaml
# Existing config...

# Grafana Integration Settings
grafana:
  enabled: true
  metrics_port: 8080  # Port for HTTP metrics endpoint
  collection_interval: 30  # seconds between metric collections
  history_retention_hours: 24  # How long to keep historical data

  # Alert thresholds
  alerts:
    camera_offline_timeout: 300  # seconds
    high_latency_threshold: 1000  # milliseconds
    high_temperature_threshold: 60  # celsius
    motion_event_burst_threshold: 10  # events per minute
```

## Phase 2: Grafana Configuration

### 2.1 Data Source Configuration

**Grafana Data Source JSON Configuration**:

```json
{
  "name": "Tapo Camera Metrics",
  "type": "infinity",
  "url": "http://localhost:8080",
  "access": "proxy",
  "jsonData": {
    "datasource_mode": "json",
    "global_queries": [
      {
        "name": "cameras",
        "url": "/metrics",
        "method": "GET",
        "format": "json",
        "refId": "cameras"
      }
    ]
  }
}
```

### 2.2 Dashboard Templates

**File**: `docs/grafana/dashboards/tapo-camera-overview.json`

```json
{
  "dashboard": {
    "id": null,
    "title": "Tapo Camera Security Overview",
    "tags": ["security", "cameras", "home-automation"],
    "timezone": "Europe/Vienna",
    "panels": [
      {
        "id": 1,
        "title": "Camera Status Overview",
        "type": "stat",
        "targets": [
          {
            "expr": "cameras.summary.online_cameras",
            "legendFormat": "Online Cameras"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 1},
                {"color": "green", "value": 2}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Motion Detection Status",
        "type": "table",
        "targets": [
          {
            "expr": "cameras.cameras",
            "format": "table"
          }
        ],
        "transformations": [
          {
            "id": "organize",
            "options": {
              "excludeByName": {},
              "indexByName": {},
              "renameByName": {
                "name": "Camera Name",
                "status": "Status",
                "motion_detected": "Motion Active",
                "network_latency_ms": "Latency (ms)",
                "temperature": "Temperature (°C)"
              }
            }
          }
        ]
      },
      {
        "id": 3,
        "title": "Network Performance",
        "type": "timeseries",
        "targets": [
          {
            "expr": "cameras.cameras.*.network_latency_ms",
            "legendFormat": "{{camera_name}} Latency"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "ms",
            "min": 0
          }
        }
      },
      {
        "id": 4,
        "title": "Temperature Monitoring",
        "type": "gauge",
        "targets": [
          {
            "expr": "cameras.cameras.*.temperature"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "celsius",
            "min": 0,
            "max": 80,
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 50},
                {"color": "red", "value": 65}
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "Motion Events Timeline",
        "type": "logs",
        "targets": [
          {
            "expr": "motion_events",
            "legendFormat": "Motion Events"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

### 2.3 Alert Rules Configuration

**File**: `docs/grafana/alerts/tapo-camera-alerts.yaml`

```yaml
groups:
  - name: tapo_camera_alerts
    interval: 30s
    rules:
      - alert: CameraOffline
        expr: cameras.cameras.*.status != "online"
        for: 5m
        labels:
          severity: critical
          service: security
        annotations:
          summary: "Tapo camera {{ $labels.camera_name }} is offline"
          description: "Camera {{ $labels.camera_name }} has been offline for more than 5 minutes"

      - alert: HighLatency
        expr: cameras.cameras.*.network_latency_ms > 1000
        for: 2m
        labels:
          severity: warning
          service: network
        annotations:
          summary: "High network latency for camera {{ $labels.camera_name }}"
          description: "Camera {{ $labels.camera_name }} latency is {{ $value }}ms"

      - alert: HighTemperature
        expr: cameras.cameras.*.temperature > 60
        for: 1m
        labels:
          severity: warning
          service: hardware
        annotations:
          summary: "Camera {{ $labels.camera_name }} running hot"
          description: "Camera temperature is {{ $value }}°C"

      - alert: MotionBurst
        expr: increase(cameras.cameras.*.motion_events_count[1m]) > 10
        for: 30s
        labels:
          severity: info
          service: security
        annotations:
          summary: "High motion activity detected"
          description: "Camera {{ $labels.camera_name }} detected {{ $value }} motion events in 1 minute"
```

## Phase 3: Advanced Features

### 3.1 Custom Grafana Panel Plugin

**File**: `grafana-plugins/tapo-camera-panel/plugin.json`

```json
{
  "type": "panel",
  "name": "Tapo Camera Live View",
  "id": "tapo-camera-panel",
  "info": {
    "description": "Live camera feed panel for Tapo cameras",
    "author": {
      "name": "Sandra Schipal",
      "url": "https://github.com/sandraschi"
    },
    "version": "1.0.0"
  },
  "dependencies": {
    "grafanaVersion": "10.0.0"
  }
}
```

### 3.2 Real-Time Motion Detection Integration

**Enhanced metrics with WebSocket support for real-time updates**:

```python
from fastapi import WebSocket, WebSocketDisconnect
import json

class RealTimeMetricsService:
    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_motion_event(self, camera_id: str, event_data: dict):
        """Broadcast motion events to connected Grafana instances"""
        message = {
            "type": "motion_event",
            "camera_id": camera_id,
            "timestamp": datetime.now().isoformat(),
            "data": event_data
        }

        if self.active_connections:
            for connection in self.active_connections.copy():
                try:
                    await connection.send_text(json.dumps(message))
                except WebSocketDisconnect:
                    self.disconnect(connection)
```

### 3.3 Austrian-Specific Dashboard Features

**Kitchen Monitoring Dashboard** (`kitchen-security.json`):
- Timer integration with camera feeds
- Cooking detection based on motion patterns
- Smoke/steam detection alerts
- Energy usage correlation

**Vienna Security Dashboard** (`vienna-home-security.json`):
- Multi-camera apartment building monitoring
- Package delivery detection
- Visitor pattern analysis
- Integration with local crime data APIs

### 3.4 Performance Optimization

**Database Integration for Historical Data**:

```python
# Optional: PostgreSQL/InfluxDB integration for long-term storage
class MetricsDatabase:
    def __init__(self, connection_string: str):
        self.conn = connection_string

    async def store_metrics_batch(self, metrics_batch: List[CameraMetrics]):
        """Batch insert for efficient storage"""
        # Implementation for database storage
        pass

    async def query_historical_data(self, camera_id: str, start_time: datetime, end_time: datetime):
        """Query historical data with time range"""
        # Implementation for historical queries
        pass
```

## Installation & Setup Guide

### Prerequisites
- **Grafana 10.0+** installed and running
- **devices-mcp** server running
- **Python 3.11+** with required dependencies

### Step-by-Step Setup

1. **Update devices-mcp server**:
```bash
cd D:\Dev\repos\devices-mcp
pip install fastapi uvicorn
# Implement metrics service code above
```

2. **Configure Grafana data source**:
- Go to Configuration → Data Sources
- Add new "JSON API" data source
- URL: `http://localhost:8080`
- Save & Test

3. **Import dashboards**:
```bash
# Import dashboard JSON files via Grafana UI
# Or use Grafana API
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @docs/grafana/dashboards/tapo-camera-overview.json
```

4. **Set up alerts**:
- Import alert rules from YAML files
- Configure notification channels (email, Slack, etc.)

### Testing & Validation

**Test metrics endpoint**:
```bash
# Test basic connectivity
curl http://localhost:8080/metrics

# Test specific camera
curl http://localhost:8080/metrics/cameras/camera_001

# Test historical data
curl http://localhost:8080/metrics/history/camera_001?hours=2
```

**Validate Grafana integration**:
1. Check data source connectivity
2. Verify dashboard panels display data
3. Test alert rules trigger correctly
4. Confirm real-time updates working

## Troubleshooting Guide

### Common Issues

**1. Metrics endpoint not accessible**:
- Check port 8080 is not blocked by firewall
- Verify devices-mcp server is running
- Check logs for HTTP server startup errors

**2. Grafana shows "No data"**:
- Verify data source configuration
- Check JSON path expressions in panels
- Test metrics endpoint directly with curl

**3. Alerts not triggering**:
- Verify alert rule expressions
- Check evaluation intervals
- Confirm notification channels configured

**4. High CPU/Memory usage**:
- Adjust collection intervals
- Reduce history retention period
- Implement database storage for historical data

### Debugging Commands

```bash
# Check server logs
tail -f logs/devices-mcp.log

# Test camera connectivity
curl http://localhost:8080/metrics/cameras

# Monitor metrics collection
watch -n 5 'curl -s http://localhost:8080/metrics | jq .summary'
```

## Future Enhancements

### Phase 4: Advanced Analytics
- **AI-powered motion analysis** (person vs. vehicle detection)
- **Behavior pattern recognition** (unusual activity detection)
- **Integration with smart home systems** (lights, alarms)
- **Mobile app notifications** via Grafana mobile

### Phase 5: Enterprise Features
- **Multi-tenant support** for apartment buildings
- **Role-based access control** for different users
- **API rate limiting and authentication**
- **Backup and disaster recovery** for metrics data

---

## Implementation Checklist

### Development Tasks
- [ ] Implement `MetricsCollector` class
- [ ] Create `GrafanaMetricsServer` FastAPI app
- [ ] Add background service startup to main server
- [ ] Update configuration schema
- [ ] Create unit tests for metrics collection
- [ ] Add integration tests for HTTP endpoints

### Grafana Setup Tasks
- [ ] Install Grafana (if not already installed)
- [ ] Configure JSON API data source
- [ ] Import dashboard templates
- [ ] Set up alert rules
- [ ] Configure notification channels
- [ ] Test end-to-end functionality

### Documentation Tasks
- [ ] Update main README with Grafana setup
- [ ] Create user guide for dashboard usage
- [ ] Document alert configuration
- [ ] Add troubleshooting section
- [ ] Create video walkthrough (optional)

### Deployment Tasks
- [ ] Update `requirements.txt` with new dependencies
- [ ] Update DXT build scripts
- [ ] Create Docker Compose file for Grafana + MCP
- [ ] Test deployment on fresh system
- [ ] Update CI/CD pipeline

---

**Ready for Windsurf Implementation** 🚀
*All architecture decisions finalized, ready to code!*
