"""
Logging configuration and utilities.

Supports both native Windows and Docker deployments:
- Native: Logs to tapo_mcp.log file
- Docker: Logs to stdout/stderr (for Docker json-file driver) AND mounted volume for Promtail
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging (Loki/Promtail compatible)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "category"):
            log_data["category"] = record.category
        if hasattr(record, "source"):
            log_data["source"] = record.source
        if hasattr(record, "severity"):
            log_data["severity"] = record.severity
        if hasattr(record, "details"):
            log_data["details"] = record.details

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: Union[str, int] = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Set up logging configuration.

    In Docker: Logs to stdout/stderr (for Docker json-file driver) AND mounted volume for Promtail.
    In Native: Logs to console and log file.

    Args:
        log_level: Logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: Path to the log file (if None, logs to console only)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Convert string log level to numeric value if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.INFO)

    # Check if running in Docker
    is_docker = os.getenv("CONTAINER") == "yes" or os.path.exists("/.dockerenv")

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # In Docker: Use JSON formatter for structured logging (Loki/Promtail)
    # In Native: Use standard formatter for readability
    if is_docker:
        # JSON formatter for Docker (Loki/Promtail compatible)
        json_formatter = JSONFormatter()
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        logger.addHandler(console_handler)

        # Also log to mounted volume for Promtail file scraping
        # Promtail reads from /var/log/devices-mcp/*.log (mounted from host)
        docker_log_dir = Path("/app/logs")
        if docker_log_dir.exists():
            docker_log_file = docker_log_dir / "tapo_mcp.log"
            file_handler = logging.handlers.RotatingFileHandler(
                str(docker_log_file), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)
    else:
        # Standard formatter for native Windows
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add file handler if log file is specified
        if log_file:
            log_file = Path(log_file)
            # Create directory if it doesn't exist
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    # Set log level for specific noisy loggers
    for logger_name in ["asyncio", "httpx", "httpcore"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Log startup info (use standard logging for this message to avoid recursion)
    if is_docker:
        logger.info("Logging configured successfully (Docker mode: JSON format for Loki/Promtail)")
    else:
        logger.info("Logging configured successfully (Native mode: standard format)")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Name of the logger

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
