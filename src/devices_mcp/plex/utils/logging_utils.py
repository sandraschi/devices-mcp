"""Logging utilities for PlexMCP.

Provides standardized logging configuration and helper functions for
consistent logging across all PlexMCP tools and services.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Global logger configuration
LOGGING_CONFIGURED = False
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
    log_to_console: bool = True,
) -> None:
    """Configure global logging settings for PlexMCP.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        log_to_console: Whether to log to console (default: True)
    """
    global LOGGING_CONFIGURED

    if LOGGING_CONFIGURED:
        return

    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler - use stderr for MCP stdio compatibility
    # In stdio mode, stdout must only contain JSON-RPC protocol messages
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically module path like "plexmcp.tools.media")

    Returns:
        Configured logger instance

    Examples:
        logger = get_logger("plexmcp.tools.media")
        logger.info("Processing media item")
    """
    # Ensure logging is configured
    if not LOGGING_CONFIGURED:
        configure_logging()

    return logging.getLogger(name)


def log_operation(logger: logging.Logger, operation: str, level: str = "INFO", **kwargs: Any) -> None:
    """Log an operation with structured context.

    Args:
        logger: Logger instance to use
        operation: Operation name/identifier
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        **kwargs: Additional context to include in log message

    Examples:
        log_operation(logger, "media_search", level="INFO", query="action movies")
        log_operation(logger, "library_scan", level="DEBUG", library_id=1)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Format context
    context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"[{operation}]"
    if context_str:
        message += f" {context_str}"

    logger.log(log_level, message)


def log_error(logger: logging.Logger, operation: str, exception: Exception, **kwargs: Any) -> None:
    """Log an error with exception details and context.

    Args:
        logger: Logger instance to use
        operation: Operation name/identifier where error occurred
        exception: The exception that was raised
        **kwargs: Additional context to include in log message

    Examples:
        try:
            result = await do_something()
        except Exception as e:
            log_error(logger, "do_something_failed", e, param1=value1)
    """
    # Format context
    context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())

    # Build error message
    message = f"[{operation}] ERROR: {type(exception).__name__}: {exception!s}"
    if context_str:
        message += f" | Context: {context_str}"

    # Log with full exception info
    logger.exception(message)


def log_success(logger: logging.Logger, operation: str, **kwargs: Any) -> None:
    """Log successful operation completion with context.

    Args:
        logger: Logger instance to use
        operation: Operation name/identifier
        **kwargs: Additional context to include in log message

    Examples:
        log_success(logger, "media_search_complete", results_found=25)
        log_success(logger, "library_scan_complete", items_added=10)
    """
    log_operation(logger, f"{operation}_SUCCESS", level="INFO", **kwargs)


def log_debug(logger: logging.Logger, operation: str, **kwargs: Any) -> None:
    """Log debug information with context.

    Args:
        logger: Logger instance to use
        operation: Operation name/identifier
        **kwargs: Additional context to include in log message

    Examples:
        log_debug(logger, "cache_check", cache_hit=True, key="media_123")
        log_debug(logger, "api_call", endpoint="/library/sections", method="GET")
    """
    log_operation(logger, operation, level="DEBUG", **kwargs)


def log_warning(logger: logging.Logger, operation: str, message: str, **kwargs: Any) -> None:
    """Log warning with message and context.

    Args:
        logger: Logger instance to use
        operation: Operation name/identifier
        message: Warning message
        **kwargs: Additional context to include in log message

    Examples:
        log_warning(logger, "media_metadata_incomplete", "Missing poster image", media_id=123)
        log_warning(logger, "library_scan_slow", "Scan taking longer than expected", elapsed=300)
    """
    context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    full_message = f"[{operation}] WARNING: {message}"
    if context_str:
        full_message += f" | {context_str}"

    logger.warning(full_message)


# Alias for backward compatibility
setup_logging = configure_logging
