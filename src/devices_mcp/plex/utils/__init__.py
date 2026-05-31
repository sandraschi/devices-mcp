"""
PlexMCP Utilities Package

This package contains various utility modules for the PlexMCP application.
"""

# Import and re-export from logging_utils.py
# Import and re-export from async_utils.py
from .async_utils import (
    AsyncLock,
    TaskPool,
    async_retry,
    async_timeout,
    cancel_all_tasks,
    create_task,
    gather_with_concurrency,
    run_in_executor,
    run_in_process,
    run_until_complete_with_timeout,
)

# Import and re-export from config.py
from .config import get_config_value, load_config, save_config, set_config_value
from .logging_utils import (
    get_logger,
    setup_logging,
)
from .network import (
    async_is_port_open as wait_for_port,
)
from .network import (
    get_local_ip as get_local_ip_address,
)

# Import and re-export from network.py
from .network import (
    is_plex_server_reachable as check_plex_server_connection,
)
from .network import (
    is_port_open as is_port_in_use,
)

# Import and re-export from validation.py
from .validation import (
    ValidationError,
    validate_media_item,
    validate_playlist,
    validate_plex_token,
    validate_plex_url,
)

__all__ = [
    "AsyncLock",
    "TaskPool",
    # From validation
    "ValidationError",
    # From async_utils
    "async_retry",
    "async_timeout",
    "cancel_all_tasks",
    # From network
    "check_plex_server_connection",
    "create_task",
    "gather_with_concurrency",
    "get_config_value",
    "get_local_ip_address",
    # From logging_utils
    "get_logger",
    "is_port_in_use",
    # From config
    "load_config",
    "run_in_executor",
    "run_in_process",
    "run_until_complete_with_timeout",
    "save_config",
    "set_config_value",
    "setup_logging",
    "validate_media_item",
    "validate_playlist",
    "validate_plex_token",
    "validate_plex_url",
    "wait_for_port",
]
