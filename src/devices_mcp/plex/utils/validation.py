"""
Validation utilities for PlexMCP.

This module provides functions for validating various types of data.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Type, TypeVar, Union
from urllib.parse import urlparse

import pytz
from pydantic import BaseModel

# Type variable for validators
T = TypeVar("T")

# Common regex patterns
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

# Plex-specific patterns
PLEX_TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{20,}$")
PLEX_CLIENT_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]{20,}$")


class ValidationError(Exception):
    """Custom validation error class."""

    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code or "validation_error"
        super().__init__(self.message)


def validate_required(value: Any, field: str = "field") -> None:
    """Validate that a required field is not None or empty.

    Args:
        value: The value to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the value is None or empty.
    """
    if value is None or (isinstance(value, (str, list, dict)) and not value):
        raise ValidationError(f"{field} is required", field=field, code="required")


def validate_type(value: Any, expected_type: Type[T], field: str = "field") -> None:
    """Validate that a value is of the expected type.

    Args:
        value: The value to validate.
        expected_type: The expected type of the value.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the value is not of the expected type.
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{field} must be of type {expected_type.__name__}, got {type(value).__name__}",
            field=field,
            code="invalid_type",
        )


def validate_length(
    value: Union[str, list, dict],
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field: str = "field",
) -> None:
    """Validate the length of a string, list, or dictionary.

    Args:
        value: The value to validate.
        min_length: Minimum allowed length (inclusive).
        max_length: Maximum allowed length (inclusive).
        field: The name of the field being validated.

    Raises:
        ValidationError: If the length is outside the specified range.
    """
    length = len(value)

    if min_length is not None and length < min_length:
        raise ValidationError(
            f"{field} must be at least {min_length} characters long", field=field, code="min_length"
        )

    if max_length is not None and length > max_length:
        raise ValidationError(
            f"{field} must be at most {max_length} characters long", field=field, code="max_length"
        )


def validate_regex(
    value: str,
    pattern: Union[str, Pattern],
    field: str = "field",
    error_message: Optional[str] = None,
) -> None:
    """Validate a string against a regular expression pattern.

    Args:
        value: The string to validate.
        pattern: The regex pattern to match against.
        field: The name of the field being validated.
        error_message: Custom error message to use.

    Raises:
        ValidationError: If the value does not match the pattern.
    """
    if not re.match(pattern, value):
        msg = error_message or f"{field} has an invalid format"
        raise ValidationError(msg, field=field, code="invalid_format")


def validate_enum(value: Any, allowed_values: List[Any], field: str = "field") -> None:
    """Validate that a value is one of the allowed values.

    Args:
        value: The value to validate.
        allowed_values: List of allowed values.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the value is not in the allowed values.
    """
    if value not in allowed_values:
        allowed = ", ".join(str(v) for v in allowed_values)
        raise ValidationError(
            f"{field} must be one of: {allowed}", field=field, code="invalid_choice"
        )


def validate_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    field: str = "field",
) -> None:
    """Validate that a numeric value is within a specified range.

    Args:
        value: The numeric value to validate.
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive).
        field: The name of the field being validated.

    Raises:
        ValidationError: If the value is outside the specified range.
    """
    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{field} must be at least {min_value}", field=field, code="min_value"
        )

    if max_value is not None and value > max_value:
        raise ValidationError(f"{field} must be at most {max_value}", field=field, code="max_value")


def validate_datetime(
    value: Union[str, datetime],
    timezone_aware: bool = False,
    future_only: bool = False,
    past_only: bool = False,
    field: str = "field",
) -> datetime:
    """Validate and parse a datetime string or object.

    Args:
        value: The datetime value to validate (string or datetime object).
        timezone_aware: Whether the datetime must be timezone-aware.
        future_only: Whether the datetime must be in the future.
        past_only: Whether the datetime must be in the past.
        field: The name of the field being validated.

    Returns:
        The parsed datetime object.

    Raises:
        ValidationError: If the datetime is invalid or doesn't meet the criteria.
    """
    dt = None

    if isinstance(value, str):
        try:
            # Try parsing ISO 8601 format
            dt = datetime.fromisoformat(value)
        except ValueError:
            # Try other common formats if ISO parsing fails
            formats = [
                "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
                "%Y-%m-%d %H:%M:%S%z",  # Space instead of T
                "%Y-%m-%dT%H:%M:%S",  # No timezone
                "%Y-%m-%d %H:%M:%S",  # Space, no timezone
                "%Y-%m-%d",  # Date only
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                raise ValidationError(
                    f"{field} must be a valid datetime string", field=field, code="invalid_datetime"
                )
    elif isinstance(value, datetime):
        dt = value
    else:
        raise ValidationError(
            f"{field} must be a datetime string or datetime object",
            field=field,
            code="invalid_type",
        )

    # Check timezone awareness
    if timezone_aware and dt.tzinfo is None:
        raise ValidationError(
            f"{field} must be timezone-aware", field=field, code="timezone_required"
        )

    # Check if datetime is in the future/past if required
    now = datetime.now(pytz.UTC)

    if dt.tzinfo is not None:
        # Convert to UTC for comparison
        dt_utc = dt.astimezone(pytz.UTC)
    else:
        # Assume naive datetimes are in local timezone
        dt_utc = pytz.UTC.localize(dt)

    if future_only and dt_utc <= now:
        raise ValidationError(f"{field} must be in the future", field=field, code="not_in_future")

    if past_only and dt_utc >= now:
        raise ValidationError(f"{field} must be in the past", field=field, code="not_in_past")

    return dt


def validate_uuid(value: str, field: str = "field") -> None:
    """Validate that a string is a valid UUID.

    Args:
        value: The string to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the string is not a valid UUID.
    """
    if not UUID_PATTERN.match(value):
        raise ValidationError(f"{field} must be a valid UUID", field=field, code="invalid_uuid")


def validate_plex_token(value: str, field: str = "token") -> None:
    """Validate a Plex authentication token.

    Args:
        value: The token to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the token is invalid.
    """
    validate_required(value, field)
    validate_type(value, str, field)
    validate_length(value, min_length=20, field=field)

    if not PLEX_TOKEN_PATTERN.match(value):
        raise ValidationError(
            f"{field} is not a valid Plex token", field=field, code="invalid_plex_token"
        )


def validate_plex_client_identifier(value: str, field: str = "client_identifier") -> None:
    """Validate a Plex client identifier.

    Args:
        value: The client identifier to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the client identifier is invalid.
    """
    validate_required(value, field)
    validate_type(value, str, field)
    validate_length(value, min_length=20, field=field)

    if not PLEX_CLIENT_IDENTIFIER_PATTERN.match(value):
        raise ValidationError(
            f"{field} is not a valid Plex client identifier",
            field=field,
            code="invalid_client_identifier",
        )


def validate_file_path(
    path: Union[str, Path],
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    writable: bool = False,
    readable: bool = True,
    field: str = "path",
) -> Path:
    """Validate a file system path.

    Args:
        path: The path to validate.
        must_exist: Whether the path must exist.
        must_be_file: Whether the path must be a file.
        must_be_dir: Whether the path must be a directory.
        writable: Whether the path must be writable.
        readable: Whether the path must be readable.
        field: The name of the field being validated.

    Returns:
        The validated Path object.

    Raises:
        ValidationError: If the path is invalid or doesn't meet the criteria.
    """
    if not isinstance(path, (str, Path)):
        raise ValidationError(
            f"{field} must be a string or Path object", field=field, code="invalid_type"
        )

    path_obj = Path(path).expanduser().resolve()

    if must_exist and not path_obj.exists():
        raise ValidationError(f"{field} does not exist: {path}", field=field, code="not_found")

    if must_be_file and path_obj.exists() and not path_obj.is_file():
        raise ValidationError(f"{field} is not a file: {path}", field=field, code="not_a_file")

    if must_be_dir and path_obj.exists() and not path_obj.is_dir():
        raise ValidationError(
            f"{field} is not a directory: {path}", field=field, code="not_a_directory"
        )

    if readable and path_obj.exists() and not os.access(path_obj, os.R_OK):
        raise ValidationError(f"{field} is not readable: {path}", field=field, code="not_readable")

    if writable and path_obj.exists() and not os.access(path_obj, os.W_OK):
        raise ValidationError(f"{field} is not writable: {path}", field=field, code="not_writable")

    return path_obj


def validate_pydantic_model(
    model_class: Type[BaseModel], data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Validate data against a Pydantic model.

    Args:
        model_class: The Pydantic model class to validate against.
        data: The data to validate.
        context: Optional context to pass to the model's Config.

    Returns:
        The validated data as a dictionary.

    Raises:
        ValidationError: If the data is invalid according to the model.
    """
    try:
        if context:
            instance = model_class(**data, __context__=context)
        else:
            instance = model_class(**data)

        return instance.dict()
    except ValidationError as e:
        # Convert Pydantic's ValidationError to our custom ValidationError
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")

        raise ValidationError(
            f"Validation failed: {', '.join(errors)}", code="validation_error"
        ) from e


def validate_with_schema(
    schema: Dict[str, Any], data: Dict[str, Any], allow_extra: bool = False
) -> Dict[str, Any]:
    """Validate data against a JSON Schema.

    Args:
        schema: The JSON Schema to validate against.
        data: The data to validate.
        allow_extra: Whether to allow extra fields not in the schema.

    Returns:
        The validated data.

    Raises:
        ValidationError: If the data is invalid according to the schema.
    """
    try:
        from jsonschema import ValidationError as JsonSchemaValidationError
        from jsonschema.validators import validator_for

        # Create a validator with the specified schema

        validator = validator_for(schema)

        # Configure the validator
        if allow_extra:
            validator = validator(schema)
        else:
            validator = validator(schema, additional_properties=False)

        # Validate the data
        validator.validate(data)
        return data

    except ImportError:
        raise RuntimeError("jsonschema package is required for schema validation")
    except JsonSchemaValidationError as e:
        raise ValidationError(
            f"Schema validation failed: {e.message}",
            field=".".join(str(p) for p in e.path) if e.path else None,
            code="schema_validation_failed",
        ) from e


def validate_condition(
    condition: bool, message: str, field: Optional[str] = None, code: str = "validation_error"
) -> None:
    """Validate a custom condition.

    Args:
        condition: The condition to check.
        message: The error message if the condition is False.
        field: The name of the field being validated.
        code: The error code to use.

    Raises:
        ValidationError: If the condition is False.
    """
    if not condition:
        raise ValidationError(message, field=field, code=code)


def validate_plex_url(value: str, field: str = "url") -> None:
    """
    Validate a Plex server URL.

    Args:
        value: The URL to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the URL is invalid.
    """
    validate_required(value, field)
    validate_type(value, str, field)

    try:
        parsed = urlparse(value)
    except Exception:
        raise ValidationError(f"{field} is not a valid URL", field=field, code="invalid_url")

    # Check if scheme is provided
    if not parsed.scheme:
        raise ValidationError(
            f"{field} must include a scheme (http:// or https://)",
            field=field,
            code="missing_scheme",
        )

    # Check if scheme is valid
    if parsed.scheme not in ["http", "https"]:
        raise ValidationError(
            f"{field} must use http:// or https:// scheme", field=field, code="invalid_scheme"
        )

    # Check if hostname is provided
    if not parsed.hostname:
        raise ValidationError(
            f"{field} must include a hostname", field=field, code="missing_hostname"
        )

    # Check if port is valid (if provided)
    if parsed.port is not None and (parsed.port < 1 or parsed.port > 65535):
        raise ValidationError(
            f"{field} port must be between 1 and 65535", field=field, code="invalid_port"
        )


def validate_media_item(data: Dict[str, Any], field: str = "media_item") -> None:
    """
    Validate a Plex media item data structure.

    Args:
        data: The media item data to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the media item data is invalid.
    """
    validate_required(data, field)
    validate_type(data, dict, field)

    # Required fields for media items
    required_fields = ["key", "title"]
    for req_field in required_fields:
        if req_field not in data:
            raise ValidationError(
                f"{field} must contain '{req_field}' field",
                field=f"{field}.{req_field}",
                code="missing_required_field",
            )

    # Validate key (should be a string starting with /)
    key = data.get("key")
    if not isinstance(key, str) or not key.startswith("/"):
        raise ValidationError(
            f"{field} key must be a string starting with '/'",
            field=f"{field}.key",
            code="invalid_key_format",
        )

    # Validate title
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError(
            f"{field} title must be a non-empty string",
            field=f"{field}.title",
            code="invalid_title",
        )

    # Optional validation for common fields
    if "ratingKey" in data:
        rating_key = data["ratingKey"]
        if not isinstance(rating_key, (str, int)):
            raise ValidationError(
                f"{field} ratingKey must be a string or integer",
                field=f"{field}.ratingKey",
                code="invalid_rating_key",
            )

    if "type" in data:
        media_type = data["type"]
        valid_types = ["movie", "show", "season", "episode", "artist", "album", "track", "photo"]
        if media_type not in valid_types:
            raise ValidationError(
                f"{field} type must be one of: {', '.join(valid_types)}",
                field=f"{field}.type",
                code="invalid_media_type",
            )


def validate_playlist(data: Dict[str, Any], field: str = "playlist") -> None:
    """
    Validate a Plex playlist data structure.

    Args:
        data: The playlist data to validate.
        field: The name of the field being validated.

    Raises:
        ValidationError: If the playlist data is invalid.
    """
    validate_required(data, field)
    validate_type(data, dict, field)

    # Required fields for playlists
    required_fields = ["title"]
    for req_field in required_fields:
        if req_field not in data:
            raise ValidationError(
                f"{field} must contain '{req_field}' field",
                field=f"{field}.{req_field}",
                code="missing_required_field",
            )

    # Validate title
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError(
            f"{field} title must be a non-empty string",
            field=f"{field}.title",
            code="invalid_title",
        )

    # Optional validation for description
    if "description" in data:
        description = data["description"]
        if description is not None and not isinstance(description, str):
            raise ValidationError(
                f"{field} description must be a string or None",
                field=f"{field}.description",
                code="invalid_description",
            )

    # Optional validation for items list
    if "items" in data:
        items = data["items"]
        if not isinstance(items, list):
            raise ValidationError(
                f"{field} items must be a list", field=f"{field}.items", code="invalid_items_type"
            )

        # Validate each item in the playlist
        for i, item in enumerate(items):
            try:
                validate_media_item(item, f"{field}.items[{i}]")
            except ValidationError as e:
                # Re-raise with more context
                raise ValidationError(
                    f"{field} item {i}: {e.message}", field=e.field, code=e.code
                ) from e

    # Optional validation for playlist type
    if "playlistType" in data:
        playlist_type = data["playlistType"]
        valid_types = ["audio", "video", "photo"]
        if playlist_type not in valid_types:
            raise ValidationError(
                f"{field} playlistType must be one of: {', '.join(valid_types)}",
                field=f"{field}.playlistType",
                code="invalid_playlist_type",
            )
