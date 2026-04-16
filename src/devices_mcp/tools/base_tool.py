"""
Base tool classes for Devices MCP tools.

This module provides the base functionality for all tools in the Devices MCP system,
with FastMCP 3.1 compatibility.
"""

import inspect
import logging
from collections.abc import Awaitable
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """The result of a tool execution."""

    content: str | dict[str, Any]
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a dictionary."""
        return {"content": self.content, "is_error": self.is_error}

    def __call__(self, **kwargs) -> "ToolResult | Awaitable[ToolResult]":
        """Execute the tool with the given parameters.

        This method is NOT async to avoid 'unawaited coroutine' warnings during instantiation.
        It handles both sync and async execute methods internally.
        """
        # Check if we have an async execute method
        if hasattr(self, "execute"):
            execute_method = self.execute

            # Check if execute is a coroutine function
            if inspect.iscoroutinefunction(execute_method):
                # Return the coroutine directly - let caller handle await
                return execute_method(**kwargs)
            # Call sync execute method directly
            return execute_method(**kwargs)

        # Fallback: raise error if no execute method
        raise NotImplementedError("Tool must implement execute method")


# Tool registry
_tool_registry: dict[str, type["BaseTool"]] = {}


def register_tool(tool_cls: "type[BaseTool]") -> "type[BaseTool]":
    """Register a tool class in the global registry.

    Args:
        tool_cls: The tool class to register

    Returns:
        The registered tool class

    Raises:
        ValueError: If the tool class is missing required attributes
    """
    if not hasattr(tool_cls, "Meta") or not hasattr(tool_cls.Meta, "name"):
        raise ValueError(f"Tool class {tool_cls.__name__} is missing required Meta.name attribute")

    tool_name = tool_cls.Meta.name
    _tool_registry[tool_name] = tool_cls
    logger.debug(f"Registered tool: {tool_name}")
    return tool_cls


def get_tool(name: str) -> Optional["type[BaseTool]"]:
    """Get a registered tool by name.

    Args:
        name: The name of the tool to retrieve

    Returns:
        The tool class if found, None otherwise
    """
    return _tool_registry.get(name)


def get_all_tools() -> list["type[BaseTool]"]:
    """Get all registered tools.

    Returns:
        List of all registered tool classes
    """
    return list(_tool_registry.values())


class ToolCategory(str, Enum):
    """Categories for organizing tools in the MCP interface."""

    CAMERA = "Camera"
    SYSTEM = "System"
    MEDIA = "Media"
    PTZ = "PTZ"
    CONFIGURATION = "Configuration"
    UTILITY = "Utility"
    ANALYSIS = "Analysis"
    SECURITY = "Security"
    ENERGY = "Energy"
    ALARMS = "Alarms"
    WEATHER = "Weather"
    AI_ANALYSIS = "AI Analysis"
    AUTOMATION = "Automation"
    LIGHTING = "Lighting"
    ONBOARDING = "Onboarding"


class ToolDefinition(BaseModel):
    """Metadata for a tool."""

    name: str
    description: str
    category: ToolCategory
    parameters: list[dict[str, Any]] = []
    is_async: bool = False

    model_config = ConfigDict(use_enum_values=True)


class BaseTool(BaseModel):
    """Base class for all Devices MCP tools.

    This class provides common functionality and metadata for all tools.
    """

    # Pydantic v2 config
    model_config = ConfigDict(
        extra="forbid",
        json_encoders={
            # Add custom JSON encoders here if needed
        },
        use_enum_values=True,
    )

    # Class-level metadata
    class Meta:
        name: str = ""
        description: str = ""
        category: ToolCategory = ToolCategory.UTILITY
        parameters: list[dict[str, Any]] = []

    def __init_subclass__(cls, **kwargs):
        """Register the tool class when it's defined."""
        super().__init_subclass__(**kwargs)

        # Skip registration for abstract base classes
        if not inspect.isabstract(cls):
            register_tool(cls)

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        """Get the tool definition with metadata and parameters."""
        return ToolDefinition(
            name=cls.Meta.name,
            description=cls.Meta.description,
            category=cls.Meta.category,
            parameters=cls.Meta.parameters,
            is_async=inspect.iscoroutinefunction(getattr(cls, "execute", None)),
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters.

        This method should be overridden by subclasses to implement the tool's functionality.
        Must be an async method that returns a ToolResult.
        """
        raise NotImplementedError("Subclasses must implement execute method")


def tool(
    name: str | None = None,
    description: str = "",
    category: "ToolCategory" = ToolCategory.UTILITY,
    **extra_metadata,
):
    """Decorator for defining a tool with metadata.

    This is a simplified decorator that works with FastMCP 3.1+.

    Args:
        name: Optional name for the tool (defaults to class name in snake_case)
        description: Description of what the tool does
        category: Category for the tool (from ToolCategory enum)
        **extra_metadata: Additional metadata for the tool

    Returns:
        A decorator that adds the metadata to the tool class
    """

    def decorator(cls):
        # Create or update the Meta class
        if not hasattr(cls, "Meta"):

            class Meta:
                pass

            cls.Meta = Meta()

        # Set the tool name (default to class name if not provided)
        tool_name = name or cls.__name__.replace("Tool", "").lower()
        cls.Meta.name = tool_name

        # Set description and category
        if description:
            cls.Meta.description = description
        if category:
            cls.Meta.category = category

        # Set additional metadata
        for key, value in extra_metadata.items():
            setattr(cls.Meta, key, value)

        # Ensure the class has an execute method
        if not hasattr(cls, "execute"):
            raise TypeError(f"Tool class {cls.__name__} must implement an 'execute' method")

        # Register the tool
        register_tool(cls)

        return cls

    return decorator
