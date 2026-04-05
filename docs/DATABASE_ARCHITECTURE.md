# Database Architecture

**Last Updated:** 2025-12-02
**Status:** Dual Database System (SQLite + PostgreSQL)

---

## Overview

The `devices-mcp` platform uses a **dual database architecture**:

1. **SQLite** - Time series data (energy, weather)
2. **PostgreSQL** - Media metadata (recordings, snapshots, AI analysis)

This design provides:
- ✅ **Simplicity** - SQLite for lightweight time series data (no server required)
- ✅ **Performance** - PostgreSQL for complex queries and media metadata
- ✅ **Flexibility** - Can run without PostgreSQL (SQLite-only mode)
- ✅ **Scalability** - PostgreSQL for production deployments

---

## Database 1: SQLite (Time Series)

### **Purpose**
Stores time series data for:
- Energy consumption (Tapo P115 smart plugs)
- Weather data (Netatmo stations)

### **Location**

#### **Outside Docker (Host):**
```
D:\Dev\repos\devices-mcp\data\timeseries.db
```

#### **Inside Docker:**
```
/app/data/timeseries.db  (mounted volume or container filesystem)
```

### **Implementation**

**File:** `src/devices_mcp/db/timeseries.py`

**Connection:**
```python
import sqlite3

# Default path: data/timeseries.db (project root)
db = TimeSeriesDB()
# Or custom path:
db = TimeSeriesDB(db_path="/custom/path/timeseries.db")
```

**Tables:**

1. **`energy_timeseries`**
   - Stores power consumption data from Tapo P115 plugs
   - Columns: `device_id`, `timestamp`, `power_w`, `voltage_v`, `current_a`, `daily_energy_kwh`, `monthly_energy_kwh`, `power_state`
   - Index: `(device_id, timestamp)`

2. **`weather_timeseries`**
   - Stores weather data from Netatmo stations
   - Columns: `station_id`, `module_type`, `timestamp`, `temperature_c`, `humidity_percent`, `co2_ppm`, `pressure_mbar`, `noise_db`
   - Index: `(station_id, module_type, timestamp)`

**Usage:**
```python
from devices_mcp.db import TimeSeriesDB

db = TimeSeriesDB()

# Store energy data
db.store_energy_data(
    device_id="tapo_p115_aircon",
    timestamp=datetime.now(),
    power_w=150.5,
    voltage_v=230.0,
    current_a=0.65
)

# Store weather data
db.store_weather_data(
    station_id="70:ee:50:3a:0e:dc",
    module_type="indoor",
    timestamp=datetime.now(),
    temperature_c=22.5,
    humidity_percent=45.0,
    co2_ppm=450
)

# Query history
energy_history = db.get_energy_history(device_id="tapo_p115_aircon", hours=24)
weather_history = db.get_weather_history(station_id="70:ee:50:3a:0e:dc", module_type="indoor", hours=24)
```

**Configuration:**
- No configuration required (file-based)
- Auto-creates database file if missing
- Auto-creates tables on first use

---

## Database 2: PostgreSQL (Media Metadata)

### **Purpose**
Stores metadata for:
- Video recordings (camera footage)
- Snapshots (images)
- AI analysis results (detections, tags, analysis)

**Note:** Actual media files are stored on disk; PostgreSQL only stores metadata.

### **Location**

#### **Outside Docker (Host):**
- **Connection:** `localhost:5432` (default)
- **Database:** `myhomecontrol` (default)
- **User:** `myhomecontrol` (default)
- **Password:** `myhomecontrol` (default)

**⚠️ PostgreSQL must be installed and running on the host!**

#### **Inside Docker:**
- **Connection:** `postgres:5432` (Docker service name)
- **Database:** `myhomecontrol`
- **User:** `myhomecontrol`
- **Password:** `myhomecontrol`

**PostgreSQL runs as a separate Docker container** (see `deploy/myhomecontrol/docker-compose.yml`)

### **Implementation**

**File:** `src/devices_mcp/db/media.py`

**Connection:**
```python
from devices_mcp.db import MediaMetadataDB

# Uses environment variables or defaults
db = MediaMetadataDB()
# Or explicit:
db = MediaMetadataDB(
    host="localhost",
    port=5432,
    database="myhomecontrol",
    user="myhomecontrol",
    password="myhomecontrol"
)
```

**Environment Variables:**
```bash
POSTGRES_HOST=localhost      # or "postgres" in Docker
POSTGRES_PORT=5432
POSTGRES_DB=myhomecontrol
POSTGRES_USER=myhomecontrol
POSTGRES_PASSWORD=myhomecontrol
```

**Tables:**

1. **`recordings`**
   - Video recording metadata
   - Columns: `recording_id`, `camera_id`, `file_path`, `file_size_bytes`, `duration_seconds`, `recording_type`, `timestamp`, `is_emergency`, `is_unusual`, `metadata` (JSONB)
   - Indexes: `(camera_id, timestamp)`, `recording_type`, `is_emergency`, `metadata` (GIN)

2. **`snapshots`**
   - Image snapshot metadata
   - Columns: `snapshot_id`, `camera_id`, `file_path`, `file_size_bytes`, `timestamp`, `metadata` (JSONB)
   - Indexes: `(camera_id, timestamp)`, `metadata` (GIN)

3. **`ai_analysis`**
   - AI analysis results (detections, tags, etc.)
   - Columns: `media_id`, `media_type`, `analysis_type`, `confidence`, `detected_at`, `details` (JSONB)
   - Indexes: `(media_id, media_type)`, `analysis_type`, `detected_at`, `details` (GIN)

**Usage:**
```python
from devices_mcp.db import MediaMetadataDB

db = MediaMetadataDB()

# Add recording
db.add_recording(
    recording_id="rec_20251202_143022",
    camera_id="kitchen_cam",
    file_path="/recordings/kitchen_cam_20251202_143022.mp4",
    file_size_bytes=15728640,
    duration_seconds=30.5,
    recording_type="motion",
    is_emergency=False
)

# Add AI analysis
db.add_ai_analysis(
    media_id="rec_20251202_143022",
    media_type="recording",
    analysis_type="person_detected",
    confidence=0.95,
    details={"person_count": 1, "bounding_boxes": [...]}
)

# Query recordings
recordings = db.get_recordings(
    camera_id="kitchen_cam",
    limit=10,
    emergency_only=False,
    with_ai_analysis=True
)
```

**Connection Pooling:**
- Uses `psycopg2.pool.SimpleConnectionPool`
- Min connections: 1
- Max connections: 10
- Connections are reused for performance

---

## Docker Configuration

### **docker-compose.yml (Simple)**

**No PostgreSQL** - Only SQLite is used:
```yaml
services:
  dashboard:
    volumes:
      - ./data:/app/data  # SQLite database stored here
```

### **deploy/myhomecontrol/docker-compose.yml (Full Stack)**

**PostgreSQL included:**
```yaml
services:
  app:
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=myhomecontrol
      - POSTGRES_USER=myhomecontrol
      - POSTGRES_PASSWORD=myhomecontrol
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=myhomecontrol
      - POSTGRES_USER=myhomecontrol
      - POSTGRES_PASSWORD=myhomecontrol
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myhomecontrol"]
```

**Volumes:**
- `postgres_data` - PostgreSQL data directory (persistent)
- `./data` - SQLite database (mounted from host)

---

## Fallback Behavior

### **PostgreSQL Unavailable**

If PostgreSQL is not available, the system falls back to **JSONL files** for media metadata:

**File:** `src/devices_mcp/utils/storage.py`

```python
# Automatic fallback
try:
    from devices_mcp.db import MediaMetadataDB
    self.db = MediaMetadataDB()
    self.use_postgres = True
except Exception as e:
    logger.warning(f"PostgreSQL not available, falling back to JSONL: {e}")
    self.recordings_file = self.storage_dir / "recordings.jsonl"
    self.use_postgres = False
```

**Fallback Storage:**
- `recordings.jsonl` - One JSON object per line
- No query capabilities (sequential read only)
- Suitable for development/testing

---

## Data Flow

### **Time Series Data (SQLite)**

```
Tapo P115 Plug → Ingestion Service → TimeSeriesDB (SQLite)
Netatmo Station → Netatmo Client → TimeSeriesDB (SQLite)
                                    ↓
                            Weather/Energy Dashboard
```

### **Media Metadata (PostgreSQL)**

```
Camera → Recording Service → MediaMetadataDB (PostgreSQL)
                              ↓
                        AI Analysis Service
                              ↓
                        MediaMetadataDB (PostgreSQL)
                              ↓
                        Recordings Dashboard
```

---

## Database Status Monitoring

The system health dashboard shows database status:

**Endpoint:** `/api/health`

**Response:**
```json
{
  "databases": {
    "timeseries": {
      "status": "ok",
      "path": "D:\\Dev\\repos\\devices-mcp\\data\\timeseries.db",
      "size_bytes": 1048576,
      "size_mb": 1.0
    },
    "postgres": {
      "status": "reachable",
      "host": "localhost"
    }
  }
}
```

**Health Dashboard:** `http://localhost:7777/health-dashboard`

---

## Migration & Backup

### **SQLite Backup**

```bash
# Backup
cp data/timeseries.db data/timeseries.db.backup

# Restore
cp data/timeseries.db.backup data/timeseries.db
```

### **PostgreSQL Backup**

```bash
# Backup (outside Docker)
pg_dump -h localhost -U myhomecontrol -d myhomecontrol > backup.sql

# Backup (inside Docker)
docker exec myhomecontrol-postgres pg_dump -U myhomecontrol myhomecontrol > backup.sql

# Restore
psql -h localhost -U myhomecontrol -d myhomecontrol < backup.sql
```

---

## Performance Considerations

### **SQLite**
- ✅ Fast for time series data (millions of rows)
- ✅ No server overhead
- ✅ Suitable for single-instance deployments
- ⚠️ Not suitable for high-concurrency writes

### **PostgreSQL**
- ✅ Excellent for complex queries
- ✅ JSONB support for flexible metadata
- ✅ Connection pooling for performance
- ✅ Suitable for production deployments
- ⚠️ Requires separate server/container

---

## Dependencies

### **SQLite**
- Built into Python (`sqlite3` module)
- No additional dependencies

### **PostgreSQL**
- **Driver:** `psycopg2-binary>=2.9.0,<3.0.0`
- **Server:** PostgreSQL 12+ (recommended: 16+)

**Installation:**
```bash
# Python driver (already in pyproject.toml)
pip install psycopg2-binary

# PostgreSQL server (outside Docker)
# Windows: Download from postgresql.org
# Linux: sudo apt-get install postgresql
# macOS: brew install postgresql
```

---

## Summary

| Database | Type | Purpose | Location (Host) | Location (Docker) | Required? |
|----------|------|---------|-----------------|-------------------|-----------|
| **SQLite** | File-based | Time series (energy, weather) | `data/timeseries.db` | `/app/data/timeseries.db` | ✅ Always |
| **PostgreSQL** | Server | Media metadata (recordings, snapshots, AI) | `localhost:5432` | `postgres:5432` | ⚠️ Optional (fallback to JSONL) |

---

## Related Files

- `src/devices_mcp/db/timeseries.py` - SQLite implementation
- `src/devices_mcp/db/media.py` - PostgreSQL implementation
- `src/devices_mcp/db/__init__.py` - Database module exports
- `src/devices_mcp/utils/storage.py` - Fallback JSONL storage
- `deploy/myhomecontrol/docker-compose.yml` - PostgreSQL Docker setup
- `pyproject.toml` - Dependencies (`psycopg2-binary`)

---

**Next Steps:**
- Consider adding TimescaleDB extension for PostgreSQL (time series optimization)
- Add database migration scripts for schema changes
- Implement automatic backups
