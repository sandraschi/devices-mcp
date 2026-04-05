"""
Input validation and error handling utilities for Devices MCP tools.

This module provides comprehensive input validation decorators and error handling
utilities to ensure robust and secure tool execution.
"""

import functools
import inspect
import logging
import re
from enum import Enum
from typing import Any, Callable, Optional, Type, Union, get_type_hints

from pydantic import ValidationError as PydanticValidationError

from devices_mcp.tools.base_tool import ToolResult

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class ToolValidationError(ValidationError):
    """Raised when tool input validation fails."""


def validate_required(value: Any, field_name: str) -> Any:
    """Validate that a required field is not None or empty."""
    if value is None:
        raise ToolValidationError(f"Required field '{field_name}' cannot be None")
    if isinstance(value, str) and not value.strip():
        raise ToolValidationError(f"Required field '{field_name}' cannot be empty")
    return value


def validate_string_length(
    value: str, field_name: str, min_length: Optional[int] = None, max_length: Optional[int] = None
) -> str:
    """Validate string length constraints."""
    if not isinstance(value, str):
        raise ToolValidationError(f"Field '{field_name}' must be a string")

    if min_length is not None and len(value) < min_length:
        raise ToolValidationError(
            f"Field '{field_name}' must be at least {min_length} characters long"
        )

    if max_length is not None and len(value) > max_length:
        raise ToolValidationError(
            f"Field '{field_name}' must be at most {max_length} characters long"
        )

    return value


def validate_ip_address(value: str, field_name: str) -> str:
    """Validate IP address format."""
    if not isinstance(value, str):
        raise ToolValidationError(f"Field '{field_name}' must be a string")

    # Basic IP address validation (IPv4)
    ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(ip_pattern, value):
        raise ToolValidationError(f"Field '{field_name}' must be a valid IP address")

    # Check each octet is valid (0-255)
    octets = value.split(".")
    for octet in octets:
        if not 0 <= int(octet) <= 255:
            raise ToolValidationError(f"Field '{field_name}' contains invalid octet: {octet}")

    return value


def validate_port(value: Union[int, str], field_name: str) -> int:
    """Validate port number."""
    try:
        port = int(value)
        if not 1 <= port <= 65535:
            raise ToolValidationError(f"Field '{field_name}' must be between 1 and 65535")
        return port
    except (ValueError, TypeError):
        raise ToolValidationError(f"Field '{field_name}' must be a valid port number") from None


def validate_enum_value(value: Any, field_name: str, enum_class: Type[Enum]) -> Any:
    """Validate that a value is a valid enum member."""
    if not isinstance(value, enum_class):
        # Try to convert string to enum
        try:
            return enum_class(value)
        except (ValueError, TypeError):
            valid_values = [e.value for e in enum_class]
            raise ToolValidationError(
                f"Field '{field_name}' must be one of: {valid_values}"
            ) from None

    return value


def validate_camera_name(value: str, field_name: str) -> str:
    """Validate camera name format."""
    if not isinstance(value, str):
        raise ToolValidationError(f"Field '{field_name}' must be a string")

    # Camera names should be alphanumeric with underscores and hyphens
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise ToolValidationError(
            f"Field '{field_name}' must contain only letters, numbers, underscores, and hyphens"
        )

    return validate_string_length(value, field_name, min_length=1, max_length=50)


def validate_credentials(username: str, password: str) -> tuple[str, str]:
    """Validate username and password credentials."""
    username = validate_string_length(username, "username", min_length=1, max_length=100)
    password = validate_string_length(password, "password", min_length=1, max_length=100)

    # Check for common weak passwords
    weak_passwords = ["password", "123456", "admin", "qwerty"]
    if password.lower() in weak_passwords:
        logger.warning("Weak password detected for camera authentication")

    return username, password


def validate_tool_input(func: Callable) -> Callable:
    """Decorator to validate tool input parameters.

    This decorator performs comprehensive validation of tool input parameters
    based on the function signature and type hints.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Bind arguments to signature for validation
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Validate each parameter
            for param_name, param_value in bound_args.arguments.items():
                if param_name == "self":
                    continue

                # Get parameter type hint
                param_type = type_hints.get(param_name)

                # Apply specific validations based on parameter name and type
                if param_name in ["camera_name", "name"]:
                    validate_camera_name(param_value, param_name)
                elif param_name in ["host", "ip", "ip_address"]:
                    validate_ip_address(param_value, param_name)
                elif param_name in ["port"]:
                    validate_port(param_value, param_name)
                elif param_name in ["username"] or param_name in ["password"]:
                    validate_string_length(param_value, param_name, min_length=1, max_length=100)
                elif (
                    param_type
                    and hasattr(param_type, "__origin__")
                    and param_type.__origin__ is list
                ) and not isinstance(param_value, list):
                    raise ToolValidationError(f"Field '{param_name}' must be a list")

            # Execute the original function
            return await func(*args, **kwargs)

        except PydanticValidationError as e:
            logger.exception("Input validation failed for {func.__name__}:")
            return ToolResult(content={"error": e.message, "field": e.field}, is_error=True)
        except Exception as e:
            logger.exception("Unexpected error in %s", func.__name__)
            return ToolResult(content={"error": f"Internal error: {e!s}"}, is_error=True)

    return wrapper


def handle_tool_errors(func: Callable) -> Callable:
    """Decorator to handle errors in tool execution gracefully.

    This decorator wraps tool execution with comprehensive error handling,
    logging, and user-friendly error responses.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Execute the tool
            result = await func(*args, **kwargs)

            # Ensure result is a ToolResult
            if not isinstance(result, ToolResult):
                result = ToolResult(content=result, is_error=False)

            return result

        except PydanticValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return ToolResult(
                content={"error": e.message, "type": "validation_error"}, is_error=True
            )

        except ConnectionError as e:
            logger.exception("Connection error in %s", func.__name__)
            return ToolResult(
                content={"error": "Camera connection failed", "details": str(e)},
                is_error=True,
            )

        except TimeoutError as e:
            logger.exception("Timeout error in %s", func.__name__)
            return ToolResult(
                content={"error": "Operation timed out", "details": str(e)},
                is_error=True,
            )

        except PermissionError as e:
            logger.exception("Permission error in %s", func.__name__)
            return ToolResult(
                content={"error": "Permission denied", "details": str(e)}, is_error=True
            )

        except Exception as e:
            logger.exception("Unexpected error in {func.__name__}:")
            return ToolResult(
                content={"error": "Internal server error", "details": str(e)},
                is_error=True,
            )

    return wrapper


def safe_execute(func: Callable) -> Callable:
    """Combined decorator for comprehensive tool safety.

    This decorator combines input validation, error handling, and logging
    for maximum tool reliability and security.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Apply input validation first
        validated_func = validate_tool_input(func)

        # Apply error handling
        safe_func = handle_tool_errors(validated_func)

        # Execute with all safety measures
        return await safe_func(*args, **kwargs)

    return wrapper
