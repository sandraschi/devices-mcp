"""
Base service classes for PlexMCP.

This module contains abstract base classes for services in the PlexMCP application.
"""

import asyncio
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

# Import our utility modules
from ..utils import async_retry, get_logger, log_exceptions, log_execution_time

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")


class ServiceError(Exception):
    """Base exception for service-related errors."""

    def __init__(
        self,
        message: str,
        code: str = "service_error",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary for API responses."""
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class ServiceInitializationError(ServiceError):
    """Raised when a service fails to initialize."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code="service_initialization_error", details=details, status_code=500
        )


class ServiceValidationError(ServiceError):
    """Raised when service input validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="validation_error", details=details, status_code=400)


class ServiceOperationError(ServiceError):
    """Raised when a service operation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="operation_failed", details=details, status_code=400)


def service_method(
    log_errors: bool = True,
    log_execution: bool = False,
    retry_attempts: int = 3,
    retry_delay: float = 1.0,
) -> Callable[..., Callable[..., Coroutine[Any, Any, R]]]:
    """Decorator for service methods with common functionality.

    Args:
        log_errors: Whether to log errors
        log_execution: Whether to log method execution time
        retry_attempts: Number of retry attempts on failure
        retry_delay: Delay between retry attempts in seconds
    """

    def decorator(
        method: Callable[..., Coroutine[Any, Any, R]],
    ) -> Callable[..., Coroutine[Any, Any, R]]:
        @wraps(method)
        @log_exceptions(log_errors=log_errors)
        @async_retry(tries=retry_attempts + 1, delay=retry_delay)
        async def wrapper(self, *args, **kwargs) -> R:
            # Get logger for the service
            logger = getattr(self, "logger", get_logger(f"{self.__class__.__name__}"))

            # Log method entry if requested
            if log_execution:
                logger.debug(f"Calling {method.__name__} with args={args}, kwargs={kwargs}")

            # Time the execution if requested
            if log_execution:
                result = await log_execution_time(logger=logger)(method)(self, *args, **kwargs)
            else:
                result = await method(self, *args, **kwargs)

            return result

        return wrapper

    return decorator


class BaseService(ABC):
    """Base class for all services in the application.

    Provides common functionality including:
    - Service initialization
    - Logging
    - Error handling
    - Lifecycle management
    """

    def __init__(self, logger_name: Optional[str] = None):
        """Initialize the base service.

        Args:
            logger_name: Optional custom logger name. If not provided,
                        the class name will be used.
        """
        self._initialized = False
        self._logger = get_logger(logger_name or self.__class__.__name__)

    @property
    def logger(self):
        """Get the logger instance for this service."""
        return self._logger

    @property
    def is_initialized(self) -> bool:
        """Check if the service has been initialized."""
        return self._initialized

    async def initialize(self, **kwargs) -> None:
        """Initialize the service.

        Args:
            **kwargs: Additional initialization parameters

        Raises:
            ServiceInitializationError: If initialization fails
        """
        if not self._initialized:
            try:
                self.logger.debug("Initializing service")
                await self._initialize(**kwargs)
                self._initialized = True
                self.logger.debug("Service initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize service: {e!s}"
                self.logger.exception(error_msg)
                raise ServiceInitializationError(error_msg) from e

    @abstractmethod
    async def _initialize(self, **kwargs) -> None:
        """Initialize the service implementation.

        Subclasses should override this method to implement their specific
        initialization logic.

        Args:
            **kwargs: Additional initialization parameters

        Raises:
            Exception: If initialization fails
        """

    async def shutdown(self) -> None:
        """Shut down the service and release resources.

        Subclasses should override _shutdown() to implement their specific
        shutdown logic.
        """
        if self._initialized:
            try:
                self.logger.debug("Shutting down service")
                await self._shutdown()
                self._initialized = False
                self.logger.debug("Service shutdown complete")
            except Exception:
                self.logger.exception("Error during service shutdown:")

    async def _shutdown(self) -> None:
        """Shutdown implementation for the service.

        Subclasses should override this method to implement their specific
        shutdown logic.
        """

    def __del__(self):
        """Ensure resources are cleaned up when the service is garbage collected."""
        if hasattr(self, "_initialized") and self._initialized:
            self.logger.warning("Service was not properly shut down before destruction")
            if asyncio.iscoroutinefunction(self.shutdown):
                # Schedule the coroutine to run in the event loop
                asyncio.create_task(self.shutdown())
            self.initialized = True

    @abstractmethod
    async def _initialize(self) -> None:
        """Service-specific initialization."""

    async def close(self) -> None:
        """Clean up resources used by the service."""
        if self.initialized:
            await self._close()
            self.initialized = False

    async def _close(self) -> None:
        """Service-specific cleanup."""


class CRUDService(BaseService, Generic[T]):
    """Base class for CRUD services."""

    @abstractmethod
    async def create(self, data: T) -> T:
        """Create a new item."""

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Get an item by ID."""

    @abstractmethod
    async def list(self, **filters) -> List[T]:
        """List items with optional filtering."""

    @abstractmethod
    async def update(self, id: str, data: T) -> T:
        """Update an existing item."""

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an item by ID."""
