"""State management for Nest Protect MCP."""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StateManager:
    """Thread-safe state manager with persistence."""

    _instance = None
    _state: Dict[str, Any] = {}
    _state_file: Path = Path("data/state.json")
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = {}
            cls._instance._state_file.parent.mkdir(parents=True, exist_ok=True)
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self) -> None:
        """Initialize the state manager and load state from disk."""
        if self._initialized:
            return

        try:
            await self._load_state()
            self._initialized = True
        except Exception:
            logger.exception("Failed to initialize state manager:")
            self._state = {}
            self._initialized = True

    async def _load_state(self) -> None:
        """Load state from file if it exists."""
        if not self._state_file.exists():
            logger.debug(f"No state file found at {self._state_file}, using empty state")
            self._state = {}
            return

        try:
            async with self._lock:
                try:
                    with open(self._state_file, encoding="utf-8") as f:
                        self._state = json.load(f)
                    logger.info(f"Successfully loaded state from {self._state_file}")
                    logger.debug(f"State content: {self._state}")
                except json.JSONDecodeError:
                    logger.exception("Invalid JSON in state file {self._state_file}:")
                    # Try to back up the corrupted file
                    backup_file = f"{self._state_file}.corrupted.{int(time.time())}"
                    try:
                        import shutil

                        shutil.copy2(self._state_file, backup_file)
                        logger.warning(f"Backed up corrupted state file to {backup_file}")
                    except Exception:
                        logger.exception("Failed to back up corrupted state file:")
                    self._state = {}
        except Exception:
            logger.exception("Failed to load state from {self._state_file}:")
            self._state = {}

    async def _save_state(self) -> None:
        """
        Save current state to file.

        This method is thread-safe and includes error handling for file operations.
        It ensures the state is only saved if the state manager is initialized.
        """
        if not self._initialized:
            logger.warning("Attempted to save state before initialization")
            return

        try:
            # Create the directory if it doesn't exist
            self._state_file.parent.mkdir(parents=True, exist_ok=True)

            # Use a temporary file for atomic writes
            temp_file = f"{self._state_file}.tmp"

            async with self._lock:
                try:
                    # Write to a temporary file first
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(self._state, f, indent=2, ensure_ascii=False)

                    # On Windows, we need to remove the destination file first
                    if os.name == "nt" and self._state_file.exists():
                        os.replace(temp_file, self._state_file)
                    else:
                        # On Unix-like systems, we can use rename which is atomic
                        os.rename(temp_file, self._state_file)

                    logger.debug(f"Successfully saved state to {self._state_file}")

                except Exception:
                    logger.exception("Error saving state to {self._state_file}:")
                    # Clean up the temporary file if it exists
                    if os.path.exists(temp_file):
                        try:
                            os.unlink(temp_file)
                        except Exception as cleanup_error:
                            logger.exception(
                                f"Failed to clean up temporary file {temp_file}: {cleanup_error}"
                            )

        except Exception:
            logger.exception("Unexpected error in _save_state:")

    async def get(self, key: str, default: T = None) -> T:
        """Get a value from the state."""
        async with self._lock:
            return self._state.get(key, default)

    async def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Set a value in the state."""
        async with self._lock:
            self._state[key] = value
        if persist:
            await self._save_state()

    async def update(
        self,
        key: str,
        updater: Callable[[Any], Any],
        default: Any = None,
        persist: bool = True,
    ) -> Any:
        """Update a value using a function."""
        async with self._lock:
            current = self._state.get(key, default)
            updated = updater(current)
            self._state[key] = updated

        if persist:
            await self._save_state()
        return updated

    async def delete(self, key: str) -> None:
        """Delete a key from the state."""
        async with self._lock:
            if key in self._state:
                del self._state[key]
        await self._save_state()

    async def clear(self) -> None:
        """Clear all state."""
        async with self._lock:
            self._state.clear()
        await self._save_state()

    async def get_all(self) -> Dict[str, Any]:
        """Get all state."""
        async with self._lock:
            return self._state.copy()


# Global instance
state_manager = StateManager()


# FastAPI integration
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    logger.info("Initializing state manager...")
    await state_manager.initialize()

    # Store state manager in app state
    app.state.state_manager = state_manager

    try:
        yield
    finally:
        logger.info("Saving state before shutdown...")
        await state_manager._save_state()


def setup_state(app: FastAPI) -> None:
    """Set up state management for FastAPI app."""
    app.state.state_manager = state_manager


# Legacy compatibility layer for tools
class AppState(BaseModel):
    """Legacy AppState for backward compatibility."""

    config: Any = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_in: Optional[int] = None
    oauth_state: Optional[str] = None
    http_session: Any = None  # aiohttp.ClientSession

    model_config = ConfigDict(arbitrary_types_allowed=True)


_app_state: Optional[AppState] = None


def initialize_app_state(config_instance: Any = None) -> None:
    """Initialize app state for legacy compatibility."""
    global _app_state
    if _app_state is None:
        _app_state = AppState(config=config_instance)
        logger.info("App state initialized for legacy compatibility.")


def get_app_state() -> AppState:
    """Get app state for legacy compatibility."""
    global _app_state
    if _app_state is None:
        # Auto-initialize with empty state
        initialize_app_state()
    return _app_state
