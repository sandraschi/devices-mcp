import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Body, Query

from devices_mcp.config import get_config, get_model, save_config
from devices_mcp.config.models import StorageSettings
from devices_mcp.db import MediaMetadataDB, TimeSeriesDB
from devices_mcp.utils.storage import RecordingStore

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/recordings")
async def get_recordings_api(
    limit: int = Query(100, ge=1, le=1000, description="Number of recordings to retrieve"),
    camera_id: str | None = Query(None, description="Filter by camera ID"),
    recording_type: str | None = Query(
        None,
        description="Filter by type (on_demand, automatic, motion, emergency)",
    ),
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve"),
    emergency_only: bool = Query(False, description="Show only emergency recordings"),
    unusual_only: bool = Query(False, description="Show only unusual recordings"),
    with_ai_analysis: bool = Query(False, description="Include AI analysis results"),
):
    """Get recordings from storage."""
    try:
        recording_store = RecordingStore()
        since = datetime.now() - timedelta(hours=hours) if hours > 0 else None
        recordings = recording_store.get_recordings(
            limit=limit,
            camera_id=camera_id,
            recording_type=recording_type,
            since=since,
            emergency_only=emergency_only,
            unusual_only=unusual_only,
            with_ai_analysis=with_ai_analysis,
        )

        return {
            "recordings": recordings,
            "total": len(recordings),
        }
    except Exception as e:
        logger.exception("Error fetching recordings")
        return {"recordings": [], "total": 0, "error": str(e)}


@router.delete("/api/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete a recording."""
    try:
        recording_store = RecordingStore()
        success = recording_store.delete_recording(recording_id)

        return {
            "success": success,
            "message": "Recording deleted" if success else "Recording not found",
        }
    except Exception as e:
        logger.exception("Error deleting recording")
        return {"success": False, "error": str(e)}


@router.post("/api/recordings/{recording_id}/ai-analysis")
async def add_ai_analysis(
    recording_id: str,
    analysis_type: str = Query(
        ...,
        description="Analysis type (policeman_at_door, pet_no_movement, person_of_interest, co2_pattern, etc.)",
    ),
    confidence: float | None = Query(None, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)"),
    details: dict | None = Body(None, description="Additional analysis details"),
):
    """Add AI analysis result to a recording."""
    try:
        db = MediaMetadataDB()
        result = db.add_ai_analysis(
            media_id=recording_id,
            media_type="recording",
            analysis_type=analysis_type,
            confidence=confidence,
            details=details or {},
        )

        return {
            "success": True,
            "analysis": result,
        }
    except Exception as e:
        logger.exception("Error adding AI analysis")
        return {"success": False, "error": str(e)}


@router.post("/api/snapshots/{snapshot_id}/ai-analysis")
async def add_snapshot_ai_analysis(
    snapshot_id: str,
    analysis_type: str = Query(..., description="Analysis type"),
    confidence: float | None = Query(None, ge=0.0, le=1.0, description="Confidence score"),
    details: dict | None = Body(None, description="Additional analysis details"),
):
    """Add AI analysis result to a snapshot."""
    try:
        db = MediaMetadataDB()
        result = db.add_ai_analysis(
            media_id=snapshot_id,
            media_type="snapshot",
            analysis_type=analysis_type,
            confidence=confidence,
            details=details or {},
        )

        return {
            "success": True,
            "analysis": result,
        }
    except Exception as e:
        logger.exception("Error adding AI analysis")
        return {"success": False, "error": str(e)}


@router.get("/api/settings/retention", summary="Get retention policies")
async def get_retention_policies():
    """Get current retention policy settings."""
    try:
        storage_cfg = get_model(StorageSettings)
        return {
            "success": True,
            "policies": storage_cfg.retention_policies,
        }
    except Exception as e:
        logger.exception("Error getting retention policies")
        return {"success": False, "error": str(e)}


@router.post("/api/settings/retention", summary="Update retention policies")
async def update_retention_policies(
    video_recordings: int | None = Body(None, ge=1, le=3650, description="Days to keep video recordings"),
    snapshots: int | None = Body(None, ge=1, le=3650, description="Days to keep snapshots"),
    environment_data: int | None = Body(None, ge=1, le=3650, description="Days to keep environment data"),
):
    """Update retention policy settings."""
    try:
        config = get_config()
        storage_cfg = get_model(StorageSettings)

        # Update policies
        if video_recordings is not None:
            storage_cfg.retention_policies["video_recordings"] = video_recordings
        if snapshots is not None:
            storage_cfg.retention_policies["snapshots"] = snapshots
        if environment_data is not None:
            storage_cfg.retention_policies["environment_data"] = environment_data

        # Save to config
        if "storage" not in config:
            config["storage"] = {}
        config["storage"]["retention_policies"] = storage_cfg.retention_policies
        save_config(config)

        return {
            "success": True,
            "policies": storage_cfg.retention_policies,
            "message": "Retention policies updated",
        }
    except Exception as e:
        logger.exception("Error updating retention policies")
        return {"success": False, "error": str(e)}


@router.post("/api/storage/scrub", summary="Scrub old data (guarded operation)")
async def scrub_old_data(
    confirm: bool = Body(..., description="Confirmation required (must be true)"),
    dry_run: bool = Body(
        False,
        description="Preview what would be deleted without actually deleting",
    ),
):
    """Scrub old data based on retention policies. Requires explicit confirmation."""
    if not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true to proceed.",
        }

    try:
        storage_cfg = get_model(StorageSettings)
        policies = storage_cfg.retention_policies

        results = {
            "videos_deleted": 0,
            "snapshots_deleted": 0,
            "environment_records_deleted": 0,
            "files_deleted": 0,
            "space_freed_mb": 0,
        }

        # Scrub video recordings
        db = MediaMetadataDB()
        video_cutoff = datetime.now(UTC) - timedelta(days=policies["video_recordings"])
        try:
            # Get all recordings older than retention period
            all_recordings = db.get_recordings(limit=10000, since=None)
            for recording in all_recordings:
                rec_timestamp = recording.get("timestamp")
                if isinstance(rec_timestamp, str):
                    rec_timestamp = datetime.fromisoformat(rec_timestamp.replace("Z", "+00:00"))
                elif not isinstance(rec_timestamp, datetime):
                    continue

                if rec_timestamp < video_cutoff:
                    if not dry_run:
                        file_path = recording.get("file_path")
                        if file_path:
                            try:
                                Path(file_path).unlink(missing_ok=True)
                                results["files_deleted"] += 1
                                results["space_freed_mb"] += recording.get("file_size_bytes", 0) / (1024 * 1024)
                            except Exception:
                                pass
                        db.delete_recording(recording.get("recording_id"))
                    results["videos_deleted"] += 1
        except Exception as e:
            logger.exception("Error scrubbing videos")
            results["error"] = str(e)

        # Scrub snapshots
        snapshot_cutoff = datetime.now(UTC) - timedelta(days=policies["snapshots"])
        try:
            # Get all snapshots older than retention period
            all_snapshots = db.get_snapshots(limit=10000, since=None)
            for snapshot in all_snapshots:
                snap_timestamp = snapshot.get("timestamp")
                if isinstance(snap_timestamp, str):
                    snap_timestamp = datetime.fromisoformat(snap_timestamp.replace("Z", "+00:00"))
                elif not isinstance(snap_timestamp, datetime):
                    continue

                if snap_timestamp < snapshot_cutoff:
                    if not dry_run:
                        file_path = snapshot.get("file_path")
                        if file_path:
                            try:
                                Path(file_path).unlink(missing_ok=True)
                                results["files_deleted"] += 1
                                results["space_freed_mb"] += snapshot.get("file_size_bytes", 0) / (1024 * 1024)
                            except Exception:
                                pass
                        db.delete_snapshot(snapshot.get("snapshot_id"))
                    results["snapshots_deleted"] += 1
        except Exception:
            logger.exception("Error scrubbing snapshots")

        # Scrub environment data (time series)
        env_cutoff = datetime.now(UTC) - timedelta(days=policies["environment_data"])
        try:
            TimeSeriesDB()
            # Placeholder for TimeSeriesDB cleanup
            # SQLite will handle old data via VACUUM
            results["environment_records_deleted"] = 0
            if not dry_run:
                logger.info(f"Environment data cleanup not yet implemented - cutoff: {env_cutoff}")
        except Exception:
            logger.exception("Error scrubbing environment data")

        return {
            "success": True,
            "dry_run": dry_run,
            "results": results,
            "message": "Scrub completed" if not dry_run else "Dry run completed",
        }
    except Exception as e:
        logger.exception("Error scrubbing old data")
        return {"success": False, "error": str(e)}
