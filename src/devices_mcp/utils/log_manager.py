"""
Log rotation and sanitization utilities for Devices MCP
"""

import gzip
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LogConfig:
    """Configuration for log management"""

    max_size_mb: float = 10.0  # Maximum size before rotation (MB)
    max_files: int = 5  # Maximum number of rotated files to keep
    compress_after_days: int = 1  # Compress files older than X days
    delete_after_days: int = 30  # Delete files older than X days
    log_directory: Optional[str] = None  # Directory to manage (defaults to script dir)
    enabled: bool = True


class LogManager:
    """Manages log file rotation, compression, and cleanup"""

    def __init__(self, config: Optional[LogConfig] = None):
        self.config = config or LogConfig()
        if self.config.log_directory is None:
            # Default to the directory containing this script
            self.config.log_directory = Path(__file__).parent.parent.parent

        self.log_dir = Path(self.config.log_directory)
        logger.info(f"LogManager initialized for directory: {self.log_dir}")

    def rotate_log(self, log_file: str, force: bool = False) -> bool:
        """Rotate a log file if it exceeds the size limit"""
        if not self.config.enabled:
            return False

        log_path = self.log_dir / log_file
        if not log_path.exists():
            return False

        # Check file size
        size_mb = log_path.stat().st_size / (1024 * 1024)
        if not force and size_mb < self.config.max_size_mb:
            return False

        # Create rotated filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = log_path.stem
        extension = log_path.suffix
        rotated_name = f"{base_name}_{timestamp}{extension}"
        rotated_path = self.log_dir / rotated_name

        try:
            # Rename the current log file
            log_path.rename(rotated_path)
            logger.info(f"Rotated log file: {log_file} -> {rotated_name}")

            # Compress the rotated file
            self._compress_file(rotated_path)

            return True
        except Exception:
            logger.exception("Failed to rotate log file {log_file}:")
            return False

    def compress_old_logs(self, days_old: Optional[int] = None) -> int:
        """Compress log files older than specified days"""
        if not self.config.enabled:
            return 0

        days = days_old or self.config.compress_after_days
        cutoff_date = datetime.now() - timedelta(days=days)
        compressed_count = 0

        try:
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    if self._compress_file(log_file):
                        compressed_count += 1

            logger.info(f"Compressed {compressed_count} old log files")
            return compressed_count
        except Exception:
            logger.exception("Failed to compress old logs:")
            return 0

    def cleanup_old_logs(self, days_old: Optional[int] = None) -> int:
        """Delete log files older than specified days"""
        if not self.config.enabled:
            return 0

        days = days_old or self.config.delete_after_days
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        try:
            # Clean up uncompressed logs
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old log file: {log_file.name}")

            # Clean up compressed logs (older than double the delete threshold)
            double_cutoff = datetime.now() - timedelta(days=days * 2)
            for gz_file in self.log_dir.glob("*.log.gz"):
                if gz_file.stat().st_mtime < double_cutoff.timestamp():
                    gz_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old compressed log file: {gz_file.name}")

            # Clean up rotated log files beyond max_files limit
            rotated_files = sorted(
                self.log_dir.glob("*.log_*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,  # Newest first
            )

            if len(rotated_files) > self.config.max_files:
                files_to_delete = rotated_files[self.config.max_files :]
                for old_file in files_to_delete:
                    old_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted excess rotated log file: {old_file.name}")

            logger.info(f"Cleaned up {deleted_count} old log files")
            return deleted_count
        except Exception:
            logger.exception("Failed to cleanup old logs:")
            return 0

    def sanitize_logs(self, log_files: Optional[List[str]] = None) -> Dict[str, int]:
        """Complete log sanitization: rotate, compress, and cleanup"""
        if not self.config.enabled:
            return {"rotated": 0, "compressed": 0, "deleted": 0}

        logger.info("Starting log sanitization process")

        results = {"rotated": 0, "compressed": 0, "deleted": 0}

        try:
            # Rotate specified log files or all .log files
            if log_files:
                files_to_check = log_files
            else:
                files_to_check = [f.name for f in self.log_dir.glob("*.log")]

            for log_file in files_to_check:
                if self.rotate_log(log_file):
                    results["rotated"] += 1

            # Compress old logs
            results["compressed"] = self.compress_old_logs()

            # Clean up very old logs
            results["deleted"] = self.cleanup_old_logs()

            logger.info(f"Log sanitization completed: {results}")
            return results

        except Exception:
            logger.exception("Log sanitization failed:")
            return results

    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about log files"""
        if not self.config.enabled:
            return {"enabled": False}

        try:
            stats = {
                "enabled": True,
                "directory": str(self.log_dir),
                "total_files": 0,
                "total_size_mb": 0.0,
                "oldest_file": None,
                "newest_file": None,
                "files_by_type": {"active_logs": 0, "rotated_logs": 0, "compressed_logs": 0},
            }

            if not self.log_dir.exists():
                return stats

            oldest_time = float("inf")
            newest_time = 0

            for log_file in self.log_dir.glob("*.log*"):
                stats["total_files"] += 1
                file_size = log_file.stat().st_size / (1024 * 1024)  # MB
                stats["total_size_mb"] += file_size

                file_time = log_file.stat().st_mtime
                oldest_time = min(oldest_time, file_time)
                newest_time = max(newest_time, file_time)

                # Categorize files
                if log_file.name.endswith(".gz"):
                    stats["files_by_type"]["compressed_logs"] += 1
                elif "_" in log_file.name:
                    stats["files_by_type"]["rotated_logs"] += 1
                else:
                    stats["files_by_type"]["active_logs"] += 1

            if stats["total_files"] > 0:
                stats["oldest_file"] = datetime.fromtimestamp(oldest_time).isoformat()
                stats["newest_file"] = datetime.fromtimestamp(newest_time).isoformat()

            return stats

        except Exception as e:
            logger.exception("Failed to get log stats:")
            return {"enabled": True, "error": str(e)}

    def _compress_file(self, file_path: Path) -> bool:
        """Compress a file using gzip"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + ".gz")

            with file_path.open("rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove original file after successful compression
            file_path.unlink()

            logger.debug(f"Compressed log file: {file_path.name}")
            return True

        except Exception:
            logger.exception("Failed to compress file {file_path}:")
            return False


def create_log_manager(config: Optional[LogConfig] = None) -> LogManager:
    """Factory function to create a LogManager instance"""
    return LogManager(config)


# Default log manager instance
default_log_manager = LogManager()


def sanitize_logs_now(log_files: Optional[List[str]] = None) -> Dict[str, int]:
    """Convenience function to sanitize logs immediately"""
    return default_log_manager.sanitize_logs(log_files)


def get_log_stats() -> Dict[str, Any]:
    """Convenience function to get log statistics"""
    return default_log_manager.get_log_stats()
