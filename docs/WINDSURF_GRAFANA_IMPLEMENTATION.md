# Windsurf Implementation Guide: Grafana HTTP Integration

## Important Notice

**CRITICAL: FOR WINDSURF IDE - DO NOT USE PROMETHEUS APPROACH**

## Mandatory Requirements

### 1. HTTP Data Source ONLY - NO PROMETHEUS

* Use **FastAPI HTTP endpoints** in existing `web_server.py`
* **NO Prometheus server setup**
* **NO metric exporters**
* **NO time-series database complexity**
* Keep it **SIMPLE and DIRECT**

### 2. Live Video/Images Are Required

Sandra **INSISTS** on seeing live camera feeds in Grafana dashboards:

* **Live JPEG snapshots** served via HTTP endpoints
* **Grafana Image panels** displaying camera feeds
* **Real-time refresh** every 5-30 seconds
* **Mobile-optimized** for iPhone viewing

## Implementation Structure

```markdown
src/devices_mcp/
├── tools/grafana/              # ← CREATE THIS
│   ├── __init__.py            # ← Tool discovery
│   ├── metrics.py             # ← Camera metrics collection
│   ├── snapshots.py           # ← Live image capture
│   └── dashboards.py          # ← Vienna dashboard data
└── web_server.py              # ← EXTEND with HTTP endpoints
```

## 🛠️ **Step 1: Create Grafana Tools Module**

### **A) Create `/tools/grafana/__init__.py`**
```python
"""Grafana integration tools for Devices MCP."""

from .metrics import GrafanaMetricsTool
from .snapshots import GrafanaSnapshotsTool
from .dashboards import ViennaDashboardTool

__all__ = [
    'GrafanaMetricsTool',
    'GrafanaSnapshotsTool',
    'ViennaDashboardTool'
]
```

### **B) Create `/tools/grafana/metrics.py`**
```python
"""Grafana metrics collection tool."""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List
from ..base_tool import BaseTool

class GrafanaMetricsTool(BaseTool):
    """Tool for collecting camera metrics in Grafana-compatible format."""

    name = "get_grafana_metrics"
    description = "Export comprehensive camera metrics for Grafana HTTP data source"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Collect all camera metrics for Grafana consumption."""
        try:
            # Get camera manager instance
            camera_manager = self.get_camera_manager()

            metrics = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cameras": {},
                "system": {
                    "active_cameras": 0,
                    "total_cameras": len(camera_manager.cameras),
                    "alerts_pending": 0,
                    "recordings_active": 0,
                    "vienna_context": {
                        "timezone": "Europe/Vienna",
                        "season": self._get_vienna_season(),
                        "heating_period": self._is_heating_period(),
                        "local_time": datetime.now().strftime("%H:%M CET")
                    }
                }
            }

            # Collect metrics for each camera
            for camera_id, camera in camera_manager.cameras.items():
                try:
                    # Get camera status and info
                    status = await camera.get_device_info()

                    camera_metrics = {
                        "status": "online" if status.get("online", False) else "offline",
                        "uptime_minutes": status.get("uptime", 0) // 60,
                        "motion_events_1h": await self._get_motion_events(camera_id, hours=1),
                        "motion_events_24h": await self._get_motion_events(camera_id, hours=24),
                        "last_motion_time": await self._get_last_motion_time(camera_id),
                        "recording_active": status.get("recording", False),
                        "temperature_celsius": status.get("temperature", 25.0),
                        "signal_strength_dbm": status.get("wifi_signal", -50),
                        "battery_level": status.get("battery_level", 100),
                        "storage_used_mb": status.get("storage_used", 0),
                        "storage_total_mb": status.get("storage_total", 32000)
                    }

                    metrics["cameras"][camera_id] = camera_metrics

                    # Update system counters
                    if camera_metrics["status"] == "online":
                        metrics["system"]["active_cameras"] += 1
                    if camera_metrics["recording_active"]:
                        metrics["system"]["recordings_active"] += 1

                except Exception as e:
                    # Camera offline or error - provide default metrics
                    metrics["cameras"][camera_id] = {
                        "status": "offline",
                        "error": str(e),
                        "uptime_minutes": 0,
                        "motion_events_1h": 0,
                        "motion_events_24h": 0,
                        "recording_active": False
                    }

            return {
                "success": True,
                "data": metrics,
                "content_type": "application/json"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to collect metrics: {str(e)}",
                "data": {"timestamp": datetime.utcnow().isoformat() + "Z", "cameras": {}}
            }

    def _get_vienna_season(self) -> str:
        """Get current season in Vienna."""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    def _is_heating_period(self) -> bool:
        """Check if it's heating period in Vienna (Oct-May)."""
        month = datetime.now().month
        return month >= 10 or month <= 5

    async def _get_motion_events(self, camera_id: str, hours: int) -> int:
        """Get motion event count for specified time period."""
        # TODO: Implement motion event counting from camera logs
        # For now, return mock data - replace with actual implementation
        import random
        if hours == 1:
            return random.randint(0, 10)
        else:
            return random.randint(5, 50)

    async def _get_last_motion_time(self, camera_id: str) -> str:
        """Get timestamp of last motion detection."""
        # TODO: Implement from actual camera logs
        # For now, return recent time - replace with actual implementation
        recent_time = datetime.utcnow().replace(minute=45, second=23)
        return recent_time.isoformat() + "Z"
```

### **C) Create `/tools/grafana/snapshots.py` - CRITICAL FOR VIDEO/IMAGES**
```python
"""Grafana live camera snapshot tool - MANDATORY FOR VIDEO/IMAGES."""
import base64
import io
import time
from datetime import datetime
from typing import Dict, Any, Optional
from ..base_tool import BaseTool

class GrafanaSnapshotsTool(BaseTool):
    """Tool for capturing live camera snapshots for Grafana image panels."""

    name = "get_camera_snapshot"
    description = "Capture live camera snapshot for Grafana image panels - MANDATORY FOR VIDEO/IMAGES"

    parameters = [
        {
            "name": "camera_id",
            "type": "string",
            "description": "Camera ID to capture snapshot from",
            "required": True
        },
        {
            "name": "quality",
            "type": "string",
            "description": "Image quality: low/medium/high",
            "default": "medium"
        },
        {
            "name": "width",
            "type": "integer",
            "description": "Image width in pixels",
            "default": 640
        },
        {
            "name": "height",
            "type": "integer",
            "description": "Image height in pixels",
            "default": 480
        }
    ]

    async def execute(self, camera_id: str, quality: str = "medium",
                     width: int = 640, height: int = 480, **kwargs) -> Dict[str, Any]:
        """Capture live snapshot from camera for Grafana image display."""
        try:
            # Get camera manager instance
            camera_manager = self.get_camera_manager()

            if camera_id not in camera_manager.cameras:
                return {
                    "success": False,
                    "error": f"Camera '{camera_id}' not found",
                    "camera_id": camera_id
                }

            camera = camera_manager.cameras[camera_id]

            # Capture snapshot from camera
            try:
                # Set quality parameters based on request
                quality_map = {
                    "low": (320, 240),
                    "medium": (640, 480),
                    "high": (1280, 720)
                }

                if quality in quality_map:
                    width, height = quality_map[quality]

                # Capture image from camera
                image_data = await camera.capture_image(width=width, height=height)

                if not image_data:
                    raise Exception("Failed to capture image from camera")

                # Convert to base64 for JSON transport
                base64_image = base64.b64encode(image_data).decode('utf-8')

                # Generate cache-busting URL for Grafana
                timestamp = int(time.time())
                snapshot_url = f"http://localhost:8080/api/snapshot/{camera_id}?t={timestamp}"

                return {
                    "success": True,
                    "camera_id": camera_id,
                    "snapshot_url": snapshot_url,
                    "base64_image": base64_image,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "resolution": f"{width}x{height}",
                    "quality": quality,
                    "file_size_kb": len(image_data) // 1024,
                    "content_type": "image/jpeg"
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to capture snapshot: {str(e)}",
                    "camera_id": camera_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Snapshot tool error: {str(e)}",
                "camera_id": camera_id
            }

class GrafanaStreamTool(BaseTool):
    """Tool for getting RTSP stream URLs for Grafana video panels."""

    name = "get_camera_stream_url"
    description = "Get RTSP/HTTP stream URL for Grafana video panels"

    parameters = [
        {
            "name": "camera_id",
            "type": "string",
            "description": "Camera ID to get stream URL for",
            "required": True
        },
        {
            "name": "stream_type",
            "type": "string",
            "description": "Stream type: rtsp/http/hls",
            "default": "rtsp"
        }
    ]

    async def execute(self, camera_id: str, stream_type: str = "rtsp", **kwargs) -> Dict[str, Any]:
        """Get live stream URL for camera."""
        try:
            camera_manager = self.get_camera_manager()

            if camera_id not in camera_manager.cameras:
                return {
                    "success": False,
                    "error": f"Camera '{camera_id}' not found"
                }

            camera = camera_manager.cameras[camera_id]

            # Get stream URL based on type
            if stream_type == "rtsp":
                stream_url = await camera.get_rtsp_url()
            elif stream_type == "http":
                # HTTP MJPEG stream for better Grafana compatibility
                stream_url = f"http://localhost:8080/api/stream/{camera_id}/mjpeg"
            elif stream_type == "hls":
                stream_url = f"http://localhost:8080/api/stream/{camera_id}/hls/stream.m3u8"
            else:
                return {
                    "success": False,
                    "error": f"Unsupported stream type: {stream_type}"
                }

            return {
                "success": True,
                "camera_id": camera_id,
                "stream_url": stream_url,
                "stream_type": stream_type,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get stream URL: {str(e)}"
            }
```

### **D) Create `/tools/grafana/dashboards.py`**
```python
"""Vienna-specific dashboard data tool."""
from datetime import datetime
from typing import Dict, Any
from ..base_tool import BaseTool

class ViennaDashboardTool(BaseTool):
    """Tool for Vienna-specific security dashboard data."""

    name = "get_vienna_security_dashboard"
    description = "Get formatted data for Vienna-specific security dashboard with German labels"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Get Vienna security dashboard data with Austrian context."""
        try:
            camera_manager = self.get_camera_manager()

            # Get current Vienna time
            vienna_time = datetime.now().strftime("%H:%M")

            dashboard_data = {
                "haustor_monitoring": {
                    "status": "aktiv",
                    "letzter_besuch": "14:30",
                    "pakete_heute": 3,
                    "bewegungen_heute": 12,
                    "aufnahme_aktiv": True
                },
                "building_security": {
                    "alle_kameras": len(camera_manager.cameras),
                    "online_kameras": sum(1 for c in camera_manager.cameras.values()
                                        if c.is_online()),
                    "bewegungsmelder": "aktiv",
                    "tuersensor_batterie": 95
                },
                "vienna_context": {
                    "aktuelle_zeit": f"{vienna_time} CET",
                    "jahreszeit": self._get_season_german(),
                    "heizperiode": self._is_heating_period(),
                    "tageslicht_verbleibend": self._daylight_hours_remaining(),
                    "wien_energie_spitzenzeit": self._is_peak_hours()
                },
                "german_labels": {
                    "status": "Status",
                    "bewegung": "Bewegung",
                    "aufnahme": "Aufnahme",
                    "batterie": "Batterie",
                    "temperatur": "Temperatur",
                    "signal": "WLAN Signal",
                    "speicher": "Speicher",
                    "online": "Online",
                    "offline": "Offline",
                    "aktiv": "Aktiv",
                    "inaktiv": "Inaktiv"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            return {
                "success": True,
                "data": dashboard_data,
                "content_type": "application/json"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get Vienna dashboard data: {str(e)}"
            }

    def _get_season_german(self) -> str:
        """Get current season in German."""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Frühling"
        elif month in [6, 7, 8]:
            return "Sommer"
        else:
            return "Herbst"

    def _is_heating_period(self) -> bool:
        """Check if heating period in Vienna."""
        month = datetime.now().month
        return month >= 10 or month <= 5

    def _daylight_hours_remaining(self) -> float:
        """Calculate daylight hours remaining today."""
        hour = datetime.now().hour
        if hour < 7:
            return 12.0  # Full day ahead
        elif hour < 19:
            return (19 - hour)
        else:
            return 0.0  # After sunset

    def _is_peak_hours(self) -> bool:
        """Check if Wien Energie peak hours (17:00-20:00)."""
        hour = datetime.now().hour
        return 17 <= hour <= 20
```

## 🌐 **Step 2: Extend Web Server with HTTP Endpoints**

### **Modify `web_server.py` - ADD THESE ENDPOINTS:**

```python
# ADD TO EXISTING web_server.py - DO NOT REPLACE EXISTING CODE

# Add these imports at the top
import base64
from io import BytesIO
from fastapi.responses import StreamingResponse

# ADD these routes to the existing setup_routes method:

@self.app.get("/api/grafana/metrics")
async def grafana_metrics_endpoint():
    """Grafana HTTP Data Source - Camera metrics in JSON format."""
    try:
        # Call the MCP tool
        result = await self.mcp_server.call_tool("get_grafana_metrics")
        if result.get("success", False):
            return JSONResponse(result["data"])
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@self.app.get("/api/snapshot/{camera_id}")
async def snapshot_endpoint(camera_id: str, t: Optional[int] = None):
    """Live camera snapshot - MANDATORY for Grafana image panels."""
    try:
        # Call the MCP tool
        result = await self.mcp_server.call_tool("get_camera_snapshot", {
            "camera_id": camera_id,
            "quality": "medium"
        })

        if result.get("success", False):
            # Decode base64 image data
            image_data = base64.b64decode(result["base64_image"])

            return StreamingResponse(
                BytesIO(image_data),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Snapshot failed"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snapshot error: {str(e)}")

@self.app.get("/api/vienna-dashboard")
async def vienna_dashboard_endpoint():
    """Vienna-specific dashboard data with German labels."""
    try:
        result = await self.mcp_server.call_tool("get_vienna_security_dashboard")
        if result.get("success", False):
            return JSONResponse(result["data"])
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Dashboard error"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@self.app.get("/api/stream/{camera_id}/mjpeg")
async def mjpeg_stream_endpoint(camera_id: str):
    """MJPEG stream for Grafana video panels."""
    try:
        # Get RTSP URL from camera
        result = await self.mcp_server.call_tool("get_camera_stream_url", {
            "camera_id": camera_id,
            "stream_type": "rtsp"
        })

        if not result.get("success", False):
            raise HTTPException(status_code=404, detail="Camera not found")

        # TODO: Convert RTSP to MJPEG stream
        # This is a placeholder - implement RTSP->MJPEG conversion
        return StreamingResponse(
            self._rtsp_to_mjpeg_generator(result["stream_url"]),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")

async def _rtsp_to_mjpeg_generator(self, rtsp_url: str):
    """Convert RTSP stream to MJPEG for web browser compatibility."""
    # TODO: Implement RTSP to MJPEG conversion using OpenCV or FFmpeg
    # This is a critical feature for live video in Grafana
    yield b'--frame\r\n'
    yield b'Content-Type: image/jpeg\r\n\r\n'
    # Placeholder - implement actual stream conversion
```

## 📊 **Step 3: Grafana Configuration**

### **A) HTTP Data Source Setup:**
```json
{
  "name": "Tapo Camera HTTP",
  "type": "grafana-http-datasource",
  "url": "http://localhost:8080/api/grafana",
  "access": "proxy",
  "jsonData": {
    "httpMethod": "GET",
    "timeout": 30
  }
}
```

### **B) Vienna Security Dashboard Panels:**

#### **🚨 MANDATORY: Live Camera Image Panels**
```json
{
  "id": 1,
  "title": "Haustor Kamera - Live",
  "type": "image",
  "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
  "options": {
    "mode": "url",
    "url": "http://localhost:8080/api/snapshot/haustor_camera?t=${__from:date:seconds}"
  },
  "fieldConfig": {
    "defaults": {
      "custom": {
        "width": "100%",
        "height": "auto"
      }
    }
  },
  "refresh": "5s"
}
```

#### **Camera Status Panel:**
```json
{
  "id": 2,
  "title": "Kamera Status",
  "type": "stat",
  "targets": [
    {
      "url": "/metrics",
      "jsonPath": "$.system.active_cameras",
      "alias": "Aktive Kameras"
    }
  ]
}
```

## ⚠️ **CRITICAL REQUIREMENTS FOR WINDSURF:**

### **1. LIVE IMAGES ARE MANDATORY** 📹

* Sandra **INSISTS** on seeing live camera feeds
* Implement `/api/snapshot/{camera_id}` endpoint **FIRST**
* Test image display in Grafana immediately
* Use cache-busting URLs (`?t=${timestamp}`)

### **2. NO PROMETHEUS COMPLEXITY**

* Do **NOT** implement Prometheus exporters
* Do **NOT** create metric collection services
* Keep it **simple HTTP endpoints only**

### **3. Vienna-Specific Context**

* German labels: "Bewegung", "Aufnahme", "Batterie"
* CET timezone display
* Austrian building context

### **4. Mobile-First Design**

* Fast loading on iPhone cellular
* Touch-optimized panel sizes
* Efficient image compression

## 🚀 **Testing Instructions**

1. **Test HTTP endpoints:**
```bash
curl http://localhost:8080/api/grafana/metrics
curl http://localhost:8080/api/snapshot/haustor_camera
curl http://localhost:8080/api/vienna-dashboard
```

2. **Verify image display:**
