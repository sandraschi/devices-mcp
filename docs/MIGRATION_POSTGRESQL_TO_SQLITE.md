# Migration Plan: PostgreSQL → SQLite

**Last Updated:** 2025-12-02
**Status:** Planning Phase
**Priority:** Medium (Simplification)

---

## Overview

Migrate media metadata storage from PostgreSQL to SQLite to simplify architecture, reduce dependencies, and improve deployment ease.

---

## Goals

1. **Simplify Architecture** - Remove PostgreSQL server dependency
2. **Reduce Complexity** - Single database system (SQLite only)
3. **Improve Deployment** - No separate database server required
4. **Maintain Functionality** - All features work identically
5. **Zero Downtime** - Seamless migration for existing deployments

---

## Current State

### **PostgreSQL Implementation**
- **File:** `src/devices_mcp/db/media.py`
- **Tables:** `recordings`, `snapshots`, `ai_analysis`
- **Features:** JSONB columns, GIN indexes, connection pooling
- **Dependencies:** `psycopg2-binary`
- **Docker:** Separate PostgreSQL container

### **Fallback System**
- **File:** `src/devices_mcp/utils/storage.py`
- **Fallback:** JSONL files if PostgreSQL unavailable
- **Status:** Already suggests PostgreSQL is optional

---

## Target State

### **SQLite Implementation**
- **File:** `src/devices_mcp/db/media_sqlite.py` (new)
- **Tables:** Same schema, JSON text instead of JSONB
- **Features:** JSON support, proper indexes, WAL mode
- **Dependencies:** None (built-in Python)
- **Docker:** No database container needed

---

## Migration Steps

### **Phase 1: Create SQLite Implementation** ⏱️ 2-3 hours

#### **1.1 Create `media_sqlite.py`**

```python
# src/devices_mcp/db/media_sqlite.py
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class MediaMetadataDBSQLite:
    """SQLite-based media metadata database with same interface as PostgreSQL version."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite database."""
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "media.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database with WAL mode and proper indexes."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")

            cursor = conn.cursor()

            # Recordings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recording_id TEXT UNIQUE NOT NULL,
                    camera_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    duration_seconds REAL,
                    recording_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    is_emergency INTEGER DEFAULT 0,
                    is_unusual INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

            # Snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id TEXT UNIQUE NOT NULL,
                    camera_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    timestamp INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

            # AI analysis table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    confidence REAL,
                    detected_at INTEGER NOT NULL,
                    details TEXT DEFAULT '{}',
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

            # Create indexes (same as PostgreSQL version)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recordings_camera_timestamp
                ON recordings(camera_id, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recordings_type
                ON recordings(recording_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recordings_emergency
                ON recordings(is_emergency) WHERE is_emergency = 1
            """)
            # ... more indexes

            conn.commit()
            logger.info(f"SQLite media database initialized at {self.db_path}")

    def add_recording(self, recording_id: str, camera_id: str,
                     file_path: str, file_size_bytes: int,
                     duration_seconds: Optional[float] = None,
                     recording_type: str = "automatic",
                     timestamp: Optional[datetime] = None,
                     is_emergency: bool = False,
                     is_unusual: bool = False,
                     metadata: Optional[dict] = None) -> dict:
        """Add recording (same interface as PostgreSQL version)."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        ts = int(timestamp.timestamp())

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO recordings
                (recording_id, camera_id, file_path, file_size_bytes,
                 duration_seconds, recording_type, timestamp,
                 is_emergency, is_unusual, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recording_id, camera_id, file_path, file_size_bytes,
                duration_seconds, recording_type, ts,
                1 if is_emergency else 0,
                1 if is_unusual else 0,
                json.dumps(metadata or {})
            ))
            conn.commit()

            cursor.execute("SELECT * FROM recordings WHERE recording_id = ?", (recording_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return {}

    def get_recordings(self, limit: int = 100, camera_id: Optional[str] = None,
                      recording_type: Optional[str] = None,
                      since: Optional[datetime] = None,
                      emergency_only: bool = False,
                      unusual_only: bool = False,
                      with_ai_analysis: bool = False,
                      recording_id: Optional[str] = None) -> List[dict]:
        """Get recordings with optional filters (same interface)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM recordings WHERE 1=1"
            params = []

            if recording_id:
                query += " AND recording_id = ?"
                params.append(recording_id)
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            if recording_type:
                query += " AND recording_type = ?"
                params.append(recording_type)
            if since:
                query += " AND timestamp >= ?"
                params.append(int(since.timestamp()))
            if emergency_only:
                query += " AND is_emergency = 1"
            if unusual_only:
                query += " AND is_unusual = 1"

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = [self._row_to_dict(row) for row in cursor.fetchall()]

            # Add AI analysis if requested
            if with_ai_analysis and results:
                recording_ids = [r["recording_id"] for r in results]
                if recording_ids:
                    placeholders = ",".join(["?"] * len(recording_ids))
                    cursor.execute(f"""
                        SELECT * FROM ai_analysis
                        WHERE media_type = 'recording' AND media_id IN ({placeholders})
                    """, recording_ids)
                    ai_results: dict[str, List[dict]] = {rid: [] for rid in recording_ids}
                    for row in cursor.fetchall():
                        media_id = row["media_id"]
                        if media_id in ai_results:
                            ai_results[media_id].append(self._row_to_dict(row))

                    for recording in results:
                        recording["ai_analysis"] = ai_results.get(recording["recording_id"], [])

            return results

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert SQLite row to dict, parsing JSON fields."""
        d = dict(row)
        # Parse JSON fields
        for key in ["metadata", "details"]:
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except json.JSONDecodeError:
                    d[key] = {}
        # Convert timestamps
        for key in ["timestamp", "detected_at", "created_at"]:
            if key in d and isinstance(d[key], int):
                d[key] = datetime.fromtimestamp(d[key], tz=timezone.utc)
        # Convert booleans
        for key in ["is_emergency", "is_unusual"]:
            if key in d:
                d[key] = bool(d[key])
        return d

    # ... implement all other methods (add_snapshot, get_snapshots, add_ai_analysis, etc.)
```

#### **1.2 Update `db/__init__.py`**

```python
# src/devices_mcp/db/__init__.py
from .media_sqlite import MediaMetadataDBSQLite
from .timeseries import TimeSeriesDB

# Export SQLite version as default
MediaMetadataDB = MediaMetadataDBSQLite

__all__ = ["MediaMetadataDB", "TimeSeriesDB"]
```

#### **1.3 Update `storage.py`**

```python
# src/devices_mcp/utils/storage.py
# Replace PostgreSQL with SQLite
try:
    from devices_mcp.db import MediaMetadataDB
    self.db = MediaMetadataDB()
    self.use_sqlite = True
    logger.info("Using SQLite for media metadata")
except Exception as e:
    logger.warning(f"SQLite not available, falling back to JSONL: {e}")
    self.recordings_file = self.storage_dir / "recordings.jsonl"
    self.db = None
    self.use_sqlite = False
```

---

### **Phase 2: Data Migration** ⏱️ 1-2 hours

#### **2.1 Create Migration Script**

```python
# scripts/migrate_postgres_to_sqlite.py
"""Migrate data from PostgreSQL to SQLite."""
import logging
import sqlite3
from pathlib import Path
from devices_mcp.db.media import MediaMetadataDB as PostgresDB
from devices_mcp.db.media_sqlite import MediaMetadataDBSQLite

logger = logging.getLogger(__name__)

def migrate():
    """Migrate all data from PostgreSQL to SQLite."""
    logger.info("Starting migration from PostgreSQL to SQLite...")

    # Connect to both databases
    postgres_db = PostgresDB()
    sqlite_db = MediaMetadataDBSQLite()

    # Migrate recordings
    logger.info("Migrating recordings...")
    recordings = postgres_db.get_recordings(limit=10000)
    for rec in recordings:
        sqlite_db.add_recording(**rec)
    logger.info(f"Migrated {len(recordings)} recordings")

    # Migrate snapshots
    logger.info("Migrating snapshots...")
    snapshots = postgres_db.get_snapshots(limit=10000)
    for snap in snapshots:
        sqlite_db.add_snapshot(**snap)
    logger.info(f"Migrated {len(snapshots)} snapshots")

    # Migrate AI analysis
    logger.info("Migrating AI analysis...")
    ai_results = postgres_db.get_ai_analysis(limit=10000)
    for ai in ai_results:
        sqlite_db.add_ai_analysis(**ai)
    logger.info(f"Migrated {len(ai_results)} AI analysis records")

    logger.info("Migration complete!")

if __name__ == "__main__":
    migrate()
```

---

### **Phase 3: Remove PostgreSQL** ⏱️ 1 hour

#### **3.1 Update `pyproject.toml`**

```toml
# Remove:
# "psycopg2-binary>=2.9.0,<3.0.0",
```

#### **3.2 Update Docker Compose**

```yaml
# deploy/myhomecontrol/docker-compose.yml
# Remove:
# - postgres service
# - POSTGRES_* environment variables
# - depends_on: postgres
```

#### **3.3 Update Health Dashboard**

```python
# src/devices_mcp/web/server.py
# Remove PostgreSQL health check
# Update to check SQLite database file
```

---

### **Phase 4: Testing** ⏱️ 2-3 hours

#### **4.1 Unit Tests**
- [ ] Test all MediaMetadataDB methods
- [ ] Test JSON parsing
- [ ] Test concurrent access (WAL mode)
- [ ] Test performance with large datasets

#### **4.2 Integration Tests**
- [ ] Test recording storage/retrieval
- [ ] Test snapshot storage/retrieval
- [ ] Test AI analysis storage/retrieval
- [ ] Test queries with filters

#### **4.3 Performance Tests**
- [ ] Compare query performance (PostgreSQL vs SQLite)
- [ ] Test with 10,000+ records
- [ ] Test concurrent reads/writes

---

### **Phase 5: Documentation** ⏱️ 1 hour

#### **5.1 Update Documentation**
- [ ] Update `DATABASE_ARCHITECTURE.md`
- [ ] Update `README.md`
- [ ] Update deployment guides
- [ ] Add migration guide

#### **5.2 Update Health Dashboard**
- [ ] Remove PostgreSQL status
- [ ] Add SQLite database size/status

---

## Rollback Plan

If issues arise:

1. **Keep PostgreSQL code** - Don't delete `media.py` immediately
2. **Feature flag** - Add config option to choose database
3. **Data backup** - Keep PostgreSQL data for 30 days
4. **Quick revert** - Can switch back by changing import

---

## Testing Checklist

- [ ] All existing tests pass
- [ ] New SQLite implementation works
- [ ] Data migration successful
- [ ] Performance acceptable
- [ ] No regressions in functionality
- [ ] Health dashboard updated
- [ ] Documentation updated
- [ ] Docker deployment works
- [ ] Host deployment works

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Create SQLite Implementation | 2-3 hours | ⏳ Pending |
| Phase 2: Data Migration | 1-2 hours | ⏳ Pending |
| Phase 3: Remove PostgreSQL | 1 hour | ⏳ Pending |
| Phase 4: Testing | 2-3 hours | ⏳ Pending |
| Phase 5: Documentation | 1 hour | ⏳ Pending |
| **Total** | **7-10 hours** | ⏳ Pending |

---

## Success Criteria

1. ✅ All functionality works identically
2. ✅ No performance degradation
3. ✅ Simpler deployment (no PostgreSQL server)
4. ✅ All tests pass
5. ✅ Documentation updated
6. ✅ Zero data loss during migration

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation | Medium | Benchmark before/after, optimize indexes |
| Data loss during migration | High | Backup PostgreSQL data, test migration script |
| Breaking changes | High | Keep PostgreSQL code, feature flag |
| JSON query performance | Low | SQLite JSON support is adequate for scale |

---

## Next Steps

1. **Review this plan** - Get approval
2. **Create SQLite implementation** - Phase 1
3. **Test thoroughly** - Phase 4
4. **Migrate data** - Phase 2
5. **Deploy** - Phase 3
6. **Monitor** - Watch for issues

---

**Related Documents:**
- `docs/WHY_POSTGRESQL_ANALYSIS.md` - Why migrate
- `docs/DATABASE_ARCHITECTURE.md` - Current architecture
- `src/devices_mcp/db/media.py` - Current PostgreSQL implementation
