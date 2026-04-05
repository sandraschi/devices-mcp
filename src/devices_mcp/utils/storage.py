"""
Storage utilities for recordings and events.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _default_events_storage_dir() -> Path:
    """Prefer DEVICES_MCP_EVENTS_DIR, then ./data/events under cwd, else user share."""
    env = os.environ.get("DEVICES_MCP_EVENTS_DIR", "").strip()
    if env:
        p = Path(env).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    candidate = Path.cwd() / "data" / "events"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        logger.debug("Could not use cwd data/events, falling back to user share")
    p = Path("~/.local/share/devices-mcp/events").expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _parse_event_ts(raw: str) -> Optional[datetime]:
    """Parse event timestamp for filtering (handles trailing Z)."""
    if not raw:
        return None
    try:
        s = raw.replace("Z", "+00:00") if raw.endswith("Z") and "+" not in raw else raw
        return datetime.fromisoformat(s)
    except ValueError:
        return None


class EventStore:
    """Append-only JSONL event log (camera, security, automation, etc.)."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize event store."""
        self.storage_dir = Path(storage_dir) if storage_dir else _default_events_storage_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.storage_dir / "events.jsonl"

    def add_event(
        self,
        event_type: str,
        camera_id: Optional[str] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "api",
    ) -> Dict[str, Any]:
        """Add an event to storage. Raises OSError if the file cannot be written."""
        now = datetime.now(timezone.utc)
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": now.isoformat(),
            "type": event_type,
            "camera_id": camera_id,
            "message": message,
            "metadata": metadata or {},
            "source": source,
        }

        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(line)

        return event

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Return a single event by id, or None."""
        if not self.events_file.exists():
            return None
        try:
            with open(self.events_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("id") == event_id:
                            return event
                    except json.JSONDecodeError:
                        continue
        except OSError:
            logger.exception("Error reading events file")
        return None

    def delete_event(self, event_id: str) -> bool:
        """Remove one event by id (rewrite file). Returns True if removed."""
        if not self.events_file.exists():
            return False
        kept: List[Dict[str, Any]] = []
        removed = False
        try:
            with open(self.events_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("id") == event_id:
                            removed = True
                            continue
                        kept.append(event)
                    except json.JSONDecodeError:
                        continue
            if not removed:
                return False
            with open(self.events_file, "w", encoding="utf-8") as f:
                for event in kept:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            return True
        except OSError:
            logger.exception("Error deleting event")
            return False

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        camera_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get events from storage with filters; sorted newest first; supports offset pagination."""
        events: List[Dict[str, Any]] = []

        if not self.events_file.exists():
            return events

        try:
            with open(self.events_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)

                        if event_type and event.get("type") != event_type:
                            continue

                        if camera_id and event.get("camera_id") != camera_id:
                            continue

                        if source and event.get("source") != source:
                            continue

                        event_time = _parse_event_ts(event.get("timestamp", ""))
                        if since and event_time is not None:
                            et = event_time
                            if et.tzinfo is None:
                                et = et.replace(tzinfo=timezone.utc)
                            st = since
                            if st.tzinfo is None:
                                st = st.replace(tzinfo=timezone.utc)
                            if et < st:
                                continue
                        if until and event_time is not None:
                            et = event_time
                            if et.tzinfo is None:
                                et = et.replace(tzinfo=timezone.utc)
                            ut = until
                            if ut.tzinfo is None:
                                ut = ut.replace(tzinfo=timezone.utc)
                            if et > ut:
                                continue

                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            logger.exception("Error reading events")

        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events[offset : offset + limit]

    def count_events(
        self,
        event_type: Optional[str] = None,
        camera_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Count matching events (no limit)."""
        return len(
            self.get_events(limit=1_000_000, event_type=event_type, camera_id=camera_id, since=since)
        )

    def distinct_types(self) -> List[str]:
        """Return sorted distinct event types in the log."""
        types: set[str] = set()
        if not self.events_file.exists():
            return []
        try:
            with open(self.events_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        t = event.get("type")
                        if isinstance(t, str):
                            types.add(t)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            logger.exception("Error reading events for types")
        return sorted(types)

    def stats(self) -> Dict[str, Any]:
        """Aggregate counts for dashboard use."""
        if not self.events_file.exists():
            return {
                "total": 0,
                "by_type": {},
                "storage_path": str(self.events_file),
            }
        by_type: Dict[str, int] = {}
        total = 0
        try:
            with open(self.events_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        total += 1
                        t = str(event.get("type", "unknown"))
                        by_type[t] = by_type.get(t, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            logger.exception("Error computing event stats")
        return {
            "total": total,
            "by_type": by_type,
            "storage_path": str(self.events_file),
            "storage_dir": str(self.storage_dir),
        }

    def clear_old_events(self, days: int = 30) -> int:
        """Remove events with timestamp older than ``days`` (rewrite file)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        if not self.events_file.exists():
            return 0
        all_events = self.get_events(limit=1_000_000)
        n_before = len(all_events)
        kept: List[Dict[str, Any]] = []
        for e in all_events:
            ts = _parse_event_ts(e.get("timestamp", ""))
            if ts is None:
                kept.append(e)
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                kept.append(e)
        if len(kept) == n_before:
            return 0
        try:
            with open(self.events_file, "w", encoding="utf-8") as f:
                for event in kept:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            return n_before - len(kept)
        except OSError:
            logger.exception("Error clearing old events")
            return 0


class RecordingStore:
    """Recording storage for camera recordings using PostgreSQL for metadata."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize recording store."""
        if storage_dir is None:
            storage_dir = Path("~/.local/share/devices-mcp/recordings").expanduser()
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir = self.storage_dir / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)

        # Use PostgreSQL for metadata (with fallback to JSONL if unavailable)
        try:
            from devices_mcp.db import MediaMetadataDB

            self.db = MediaMetadataDB()
            self.use_postgres = True
        except Exception as e:
            logger.warning(f"PostgreSQL not available, falling back to JSONL: {e}")
            self.recordings_file = self.storage_dir / "recordings.jsonl"
            self.db = None
            self.use_postgres = False

    def add_recording(
        self,
        camera_id: str,
        video_path: Optional[Path] = None,
        duration_seconds: float = 0.0,
        size_bytes: int = 0,
        recording_type: str = "automatic",  # 'on_demand', 'automatic', 'motion', 'emergency'
        is_emergency: bool = False,
        is_unusual: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a recording to storage."""
        recording_id = f"rec_{datetime.now().timestamp():.6f}"
        timestamp = datetime.now(timezone.utc)

        if self.use_postgres and self.db:
            # Use PostgreSQL
            file_path = str(video_path) if video_path else ""
            self.db.add_recording(
                recording_id=recording_id,
                camera_id=camera_id,
                file_path=file_path,
                file_size_bytes=size_bytes,
                duration_seconds=duration_seconds,
                recording_type=recording_type,
                timestamp=timestamp,
                is_emergency=is_emergency,
                is_unusual=is_unusual,
                metadata=metadata or {},
            )
            # Convert to expected format
            return {
                "id": recording_id,
                "recording_id": recording_id,
                "timestamp": timestamp.isoformat(),
                "camera_id": camera_id,
                "video_path": file_path,
                "duration_seconds": duration_seconds,
                "size_bytes": size_bytes,
                "recording_type": recording_type,
                "is_emergency": is_emergency,
                "is_unusual": is_unusual,
                "metadata": metadata or {},
            }
        # Fallback to JSONL
        recording = {
            "id": recording_id,
            "timestamp": timestamp.isoformat(),
            "camera_id": camera_id,
            "video_path": str(video_path) if video_path else None,
            "duration_seconds": duration_seconds,
            "size_bytes": size_bytes,
            "recording_type": recording_type,
            "is_emergency": is_emergency,
            "is_unusual": is_unusual,
            "metadata": metadata or {},
        }

        try:
            with open(self.recordings_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(recording) + "\n")
        except Exception:
            logger.exception("Error writing recording")

        return recording

    def get_recordings(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        recording_type: Optional[str] = None,
        since: Optional[datetime] = None,
        emergency_only: bool = False,
        unusual_only: bool = False,
        with_ai_analysis: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get recordings from storage."""
        if self.use_postgres and self.db:
            # Use PostgreSQL
            results = self.db.get_recordings(
                limit=limit,
                camera_id=camera_id,
                recording_type=recording_type,
                since=since,
                emergency_only=emergency_only,
                unusual_only=unusual_only,
                with_ai_analysis=with_ai_analysis,
            )
            # Convert to expected format
            recordings = []
            for row in results:
                recordings.append(
                    {
                        "id": row.get("recording_id", ""),
                        "recording_id": row.get("recording_id", ""),
                        "timestamp": row.get("timestamp").isoformat()
                        if row.get("timestamp")
                        else "",
                        "camera_id": row.get("camera_id", ""),
                        "video_path": row.get("file_path", ""),
                        "duration_seconds": row.get("duration_seconds", 0.0),
                        "size_bytes": row.get("file_size_bytes", 0),
                        "recording_type": row.get("recording_type", "automatic"),
                        "is_emergency": row.get("is_emergency", False),
                        "is_unusual": row.get("is_unusual", False),
                        "metadata": row.get("metadata", {}),
                        "ai_analysis": row.get("ai_analysis", []),
                    }
                )
            return recordings
        # Fallback to JSONL
        recordings = []

        if not self.recordings_file.exists():
            return recordings

        try:
            with open(self.recordings_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        recording = json.loads(line)

                        # Filter by camera
                        if camera_id and recording.get("camera_id") != camera_id:
                            continue

                        # Filter by type
                        if recording_type and recording.get("recording_type") != recording_type:
                            continue

                        # Filter by emergency/unusual
                        if emergency_only and not recording.get("is_emergency", False):
                            continue
                        if unusual_only and not recording.get("is_unusual", False):
                            continue

                        # Filter by time
                        if since:
                            recording_time = datetime.fromisoformat(recording.get("timestamp", ""))
                            if recording_time < since:
                                continue

                        recordings.append(recording)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            logger.exception("Error reading recordings")

        # Sort by timestamp descending
        recordings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Limit results
        return recordings[:limit]

    def delete_recording(self, recording_id: str) -> bool:
        """Delete a recording and its file."""
        if self.use_postgres and self.db:
            # Get recording to find file path
            recordings = self.db.get_recordings(limit=1, recording_id=recording_id)
            recording = recordings[0] if recordings else None

            if not recording:
                return False

            # Delete video file if it exists
            video_path = recording.get("file_path")
            if video_path:
                try:
                    Path(video_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Error deleting video file: %s", e)

            # Delete from database
            return self.db.delete_recording(recording_id)
        # Fallback to JSONL
        recordings = self.get_recordings(limit=10000)
        recording = next((r for r in recordings if r.get("id") == recording_id), None)

        if not recording:
            return False

        # Delete video file if it exists
        video_path = recording.get("video_path")
        if video_path:
            try:
                Path(video_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Error deleting video file: %s", e)

        # Remove from storage
        filtered_recordings = [r for r in recordings if r.get("id") != recording_id]
        try:
            with open(self.recordings_file, "w", encoding="utf-8") as f:
                for rec in filtered_recordings:
                    f.write(json.dumps(rec) + "\n")
            return True
        except Exception:
            logger.exception("Error deleting recording")
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if self.use_postgres and self.db:
            return self.db.get_storage_stats()
        # Fallback to JSONL
        recordings = self.get_recordings(limit=10000)
        total_size = sum(r.get("size_bytes", 0) for r in recordings)
        total_count = len(recordings)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = len(
            [r for r in recordings if datetime.fromisoformat(r.get("timestamp", "")) >= today]
        )

        return {
            "total_recordings": total_count,
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "today_recordings": today_count,
            "emergency_recordings": len([r for r in recordings if r.get("is_emergency", False)]),
            "unusual_recordings": len([r for r in recordings if r.get("is_unusual", False)]),
        }
