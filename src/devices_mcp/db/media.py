"""
PostgreSQL database for media metadata (recordings, snapshots, AI analysis).
"""

import os
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from ..utils import get_logger

logger = get_logger(__name__)


class MediaMetadataDB:
    """
    Manages PostgreSQL database for media metadata (recordings, snapshots, AI analysis).
    Files are stored on disk; database stores metadata only.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        """Initialize database connection."""
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DB", "myhomecontrol")
        self.user = user or os.getenv("POSTGRES_USER", "myhomecontrol")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "myhomecontrol")

        self._pool: SimpleConnectionPool | None = None
        self._init_db()

    def _get_connection(self):
        """Get connection from pool."""
        if self._pool is None:
            self._pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
        return self._pool.getconn()

    def _return_connection(self, conn):
        """Return connection to pool."""
        if self._pool:
            self._pool.putconn(conn)

    def _init_db(self):
        """Initialize database tables and indexes."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Recordings table (videos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recordings (
                    id SERIAL PRIMARY KEY,
                    recording_id VARCHAR(255) UNIQUE NOT NULL,
                    camera_id VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_bytes BIGINT NOT NULL,
                    duration_seconds REAL,
                    recording_type VARCHAR(50) NOT NULL,  -- 'on_demand', 'automatic', 'motion', 'emergency'
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    is_emergency BOOLEAN DEFAULT FALSE,
                    is_unusual BOOLEAN DEFAULT FALSE,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for recordings
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
                ON recordings(is_emergency) WHERE is_emergency = TRUE
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_recordings_metadata_gin
                ON recordings USING GIN(metadata)
            """)

            # Snapshots table (images)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id SERIAL PRIMARY KEY,
                    snapshot_id VARCHAR(255) UNIQUE NOT NULL,
                    camera_id VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_bytes BIGINT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for snapshots
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_camera_timestamp
                ON snapshots(camera_id, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_metadata_gin
                ON snapshots USING GIN(metadata)
            """)

            # AI analysis table (tags, detections, analysis results)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis (
                    id SERIAL PRIMARY KEY,
                    media_id VARCHAR(255) NOT NULL,  -- References recording_id or snapshot_id
                    media_type VARCHAR(50) NOT NULL,  -- 'recording' or 'snapshot'
                    analysis_type VARCHAR(100) NOT NULL,  -- 'policeman_at_door', 'pet_no_movement', 'person_of_interest', 'co2_pattern', etc.
                    confidence REAL,  -- 0.0 to 1.0
                    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    details JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for AI analysis
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_media
                ON ai_analysis(media_id, media_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_type
                ON ai_analysis(analysis_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_detected_at
                ON ai_analysis(detected_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_details_gin
                ON ai_analysis USING GIN(details)
            """)

            conn.commit()
            cursor.close()
            self._return_connection(conn)
            logger.info("Media metadata database initialized")

        except Exception:
            logger.exception("Error initializing media metadata database")
            if conn:
                conn.rollback()
                self._return_connection(conn)
            raise

    def add_recording(
        self,
        recording_id: str,
        camera_id: str,
        file_path: str,
        file_size_bytes: int,
        duration_seconds: float | None = None,
        recording_type: str = "automatic",  # 'on_demand', 'automatic', 'motion', 'emergency'
        timestamp: datetime | None = None,
        is_emergency: bool = False,
        is_unusual: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a recording metadata entry."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                INSERT INTO recordings (
                    recording_id, camera_id, file_path, file_size_bytes,
                    duration_seconds, recording_type, timestamp,
                    is_emergency, is_unusual, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (recording_id) DO UPDATE SET
                    file_path = EXCLUDED.file_path,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    duration_seconds = EXCLUDED.duration_seconds,
                    recording_type = EXCLUDED.recording_type,
                    is_emergency = EXCLUDED.is_emergency,
                    is_unusual = EXCLUDED.is_unusual,
                    metadata = EXCLUDED.metadata
                RETURNING *
            """,
                (
                    recording_id,
                    camera_id,
                    file_path,
                    file_size_bytes,
                    duration_seconds,
                    recording_type,
                    timestamp,
                    is_emergency,
                    is_unusual,
                    metadata or {},
                ),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return dict(result) if result else {}

        except Exception:
            logger.exception("Error adding recording")
            conn.rollback()
            raise
        finally:
            self._return_connection(conn)

    def add_snapshot(
        self,
        snapshot_id: str,
        camera_id: str,
        file_path: str,
        file_size_bytes: int,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a snapshot metadata entry."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                INSERT INTO snapshots (
                    snapshot_id, camera_id, file_path, file_size_bytes,
                    timestamp, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (snapshot_id) DO UPDATE SET
                    file_path = EXCLUDED.file_path,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    metadata = EXCLUDED.metadata
                RETURNING *
            """,
                (
                    snapshot_id,
                    camera_id,
                    file_path,
                    file_size_bytes,
                    timestamp,
                    metadata or {},
                ),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return dict(result) if result else {}

        except Exception:
            logger.exception("Error adding snapshot")
            conn.rollback()
            raise
        finally:
            self._return_connection(conn)

    def add_ai_analysis(
        self,
        media_id: str,
        media_type: str,  # 'recording' or 'snapshot'
        analysis_type: str,  # 'policeman_at_door', 'pet_no_movement', 'person_of_interest', 'co2_pattern', etc.
        confidence: float | None = None,
        detected_at: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add AI analysis result."""
        if detected_at is None:
            detected_at = datetime.now(timezone.utc)

        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                INSERT INTO ai_analysis (
                    media_id, media_type, analysis_type,
                    confidence, detected_at, details
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """,
                (
                    media_id,
                    media_type,
                    analysis_type,
                    confidence,
                    detected_at,
                    details or {},
                ),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            return dict(result) if result else {}

        except Exception:
            logger.exception("Error adding AI analysis")
            conn.rollback()
            raise
        finally:
            self._return_connection(conn)

    def get_recordings(
        self,
        limit: int = 100,
        camera_id: str | None = None,
        recording_type: str | None = None,
        since: datetime | None = None,
        emergency_only: bool = False,
        unusual_only: bool = False,
        with_ai_analysis: bool = False,
        recording_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get recordings with optional filters."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = "SELECT * FROM recordings WHERE 1=1"
            params = []

            if recording_id:
                query += " AND recording_id = %s"
                params.append(recording_id)

            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)

            if recording_type:
                query += " AND recording_type = %s"
                params.append(recording_type)

            if since:
                query += " AND timestamp >= %s"
                params.append(since)

            if emergency_only:
                query += " AND is_emergency = TRUE"

            if unusual_only:
                query += " AND is_unusual = TRUE"

            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Add AI analysis if requested
            if with_ai_analysis and results:
                recording_ids = [r["recording_id"] for r in results]
                if recording_ids:
                    placeholders = ",".join(["%s"] * len(recording_ids))
                    cursor.execute(
                        f"""
                        SELECT * FROM ai_analysis
                        WHERE media_type = 'recording' AND media_id IN ({placeholders})
                    """,
                        recording_ids,
                    )
                    ai_results: dict[str, list[dict[str, Any]]] = {rid: [] for rid in recording_ids}
                    for row in cursor.fetchall():
                        media_id = row["media_id"]
                        if media_id in ai_results:
                            ai_results[media_id].append(dict(row))

                    for recording in results:
                        recording["ai_analysis"] = ai_results.get(recording["recording_id"], [])

            cursor.close()
            return results

        except Exception:
            logger.exception("Error getting recordings")
            raise
        finally:
            self._return_connection(conn)

    def get_snapshots(
        self,
        limit: int = 100,
        camera_id: str | None = None,
        since: datetime | None = None,
        with_ai_analysis: bool = False,
    ) -> list[dict[str, Any]]:
        """Get snapshots with optional filters."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = "SELECT * FROM snapshots WHERE 1=1"
            params = []

            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)

            if since:
                query += " AND timestamp >= %s"
                params.append(since)

            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Add AI analysis if requested
            if with_ai_analysis and results:
                snapshot_ids = [r["snapshot_id"] for r in results]
                if snapshot_ids:
                    placeholders = ",".join(["%s"] * len(snapshot_ids))
                    cursor.execute(
                        f"""
                        SELECT * FROM ai_analysis
                        WHERE media_type = 'snapshot' AND media_id IN ({placeholders})
                    """,
                        snapshot_ids,
                    )
                    ai_results: dict[str, list[dict[str, Any]]] = {sid: [] for sid in snapshot_ids}
                    for row in cursor.fetchall():
                        media_id = row["media_id"]
                        if media_id in ai_results:
                            ai_results[media_id].append(dict(row))

                    for snapshot in results:
                        snapshot["ai_analysis"] = ai_results.get(snapshot["snapshot_id"], [])

            cursor.close()
            return results

        except Exception:
            logger.exception("Error getting snapshots")
            raise
        finally:
            self._return_connection(conn)

    def get_ai_analysis(
        self,
        media_id: str | None = None,
        media_type: str | None = None,
        analysis_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get AI analysis results with optional filters."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = "SELECT * FROM ai_analysis WHERE 1=1"
            params = []

            if media_id:
                query += " AND media_id = %s"
                params.append(media_id)

            if media_type:
                query += " AND media_type = %s"
                params.append(media_type)

            if analysis_type:
                query += " AND analysis_type = %s"
                params.append(analysis_type)

            if since:
                query += " AND detected_at >= %s"
                params.append(since)

            query += " ORDER BY detected_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            return results

        except Exception:
            logger.exception("Error getting AI analysis")
            raise
        finally:
            self._return_connection(conn)

    def delete_recording(self, recording_id: str) -> bool:
        """Delete a recording and its AI analysis."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Delete AI analysis first
            cursor.execute(
                """
                DELETE FROM ai_analysis
                WHERE media_type = 'recording' AND media_id = %s
            """,
                (recording_id,),
            )

            # Delete recording
            cursor.execute("DELETE FROM recordings WHERE recording_id = %s", (recording_id,))
            deleted = cursor.rowcount > 0

            conn.commit()
            cursor.close()
            return deleted

        except Exception:
            logger.exception("Error deleting recording")
            conn.rollback()
            raise
        finally:
            self._return_connection(conn)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot and its AI analysis."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Delete AI analysis first
            cursor.execute(
                """
                DELETE FROM ai_analysis
                WHERE media_type = 'snapshot' AND media_id = %s
            """,
                (snapshot_id,),
            )

            # Delete snapshot
            cursor.execute("DELETE FROM snapshots WHERE snapshot_id = %s", (snapshot_id,))
            deleted = cursor.rowcount > 0

            conn.commit()
            cursor.close()
            return deleted

        except Exception:
            logger.exception("Error deleting snapshot")
            conn.rollback()
            raise
        finally:
            self._return_connection(conn)

    def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Recording stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_recordings,
                    SUM(file_size_bytes) as total_size_bytes,
                    COUNT(*) FILTER (WHERE timestamp >= CURRENT_DATE) as today_recordings,
                    COUNT(*) FILTER (WHERE is_emergency = TRUE) as emergency_recordings,
                    COUNT(*) FILTER (WHERE is_unusual = TRUE) as unusual_recordings
                FROM recordings
            """)
            rec_stats = dict(cursor.fetchone())

            # Snapshot stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_snapshots,
                    SUM(file_size_bytes) as total_size_bytes
                FROM snapshots
            """)
            snap_stats = dict(cursor.fetchone())

            cursor.close()

            total_size_bytes = (rec_stats.get("total_size_bytes") or 0) + (
                snap_stats.get("total_size_bytes") or 0
            )

            return {
                "total_recordings": rec_stats.get("total_recordings", 0) or 0,
                "total_snapshots": snap_stats.get("total_snapshots", 0) or 0,
                "total_size_bytes": total_size_bytes,
                "total_size_gb": round(total_size_bytes / (1024**3), 2),
                "today_recordings": rec_stats.get("today_recordings", 0) or 0,
                "emergency_recordings": rec_stats.get("emergency_recordings", 0) or 0,
                "unusual_recordings": rec_stats.get("unusual_recordings", 0) or 0,
            }

        except Exception:
            logger.exception("Error getting storage stats")
            raise
        finally:
            self._return_connection(conn)
