"""
FastMCP 3.1 integration for Devices MCP.

This module provides base classes and utilities for FastMCP 3.1 compatibility.
"""

import inspect
import logging
from enum import StrEnum
from typing import TypeVar

from fastmcp.tools import Tool as FastMCPTool
from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolResult[T](BaseModel):
    """Standard response format for tool execution results."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Result message or error description")
    data: T = Field(default=None, description="Result data if successful")

    @classmethod
    def success_result(cls, message: str, data: T = None) -> "ToolResult[T]":
        """Create a successful result."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str) -> "ToolResult[None]":
        """Create an error result."""
        return cls(success=False, message=message, data=None)


logger = logging.getLogger(__name__)


class ToolCategory(StrEnum):
    """Categories for organizing tools in the MCP interface."""

    CAMERA = "Camera"
    SYSTEM = "System"
    MEDIA = "Media"
    PTZ = "PTZ"
    CONFIGURATION = "Configuration"
    UTILITY = "Utility"


class BaseTool(FastMCPTool):
    """Base class for all Devices MCP tools."""

    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="Description of what the tool does")

    class Meta:
        abstract = True
        category: ToolCategory = ToolCategory.UTILITY
        is_async: bool = True

    @classmethod
    def get_tool_metadata(cls):
        """Get the tool metadata including name, description, and category."""
        return {
            "name": getattr(cls, "name", cls.__name__),
            "description": cls.__doc__ or "",
            "meta": {
                "category": (cls.Meta.category if hasattr(cls.Meta, "category") else ToolCategory.UTILITY),
                **getattr(cls.Meta, "meta", {}),
            },
        }


def tool(name: str | None = None, **kwargs):
    """Decorator for FastMCP 3.1+ tools.

    Args:
        name: The name of the tool (default: function/class name).
        **kwargs: Additional metadata for the tool.
    """

    def decorator(func_or_cls):
        # Handle both function and class decoration
        if inspect.isclass(func_or_cls):
            cls = func_or_cls
            if not hasattr(cls, "Meta"):

                class Meta:
                    pass

                cls.Meta = Meta

            # Set metadata in Meta class
            if name is not None:
                cls.tool_name = name

            # Add any additional metadata to Meta
            for key, value in kwargs.items():
                setattr(cls.Meta, key, value)

            # Make sure the class has an execute method
            if not hasattr(cls, "execute") or not callable(cls.execute):
                raise TypeError(f"Tool class {cls.__name__} must implement an 'execute' method")

            # Add the tool to the registry
            from ..tools.discovery import register_tool

            register_tool(cls)

            return cls
        # For functions, wrap them in a class
        func = func_or_cls
        tool_name = name or func.__name__

        # Create Meta class with name and other attributes
        meta_dict = {"name": tool_name}
        meta_dict.update(kwargs)
        Meta = type("Meta", (), meta_dict)

        class WrappedTool(BaseTool):
            """Wrapper class for function-based tools."""

            Meta = Meta

            async def execute(self, *args, **kwargs):
                return await func(*args, **kwargs)

        WrappedTool.__name__ = func.__name__
        WrappedTool.__qualname__ = func.__qualname__
        WrappedTool.__module__ = func.__module__

        # Add the tool to the registry
        from ..tools.discovery import register_tool

        register_tool(WrappedTool)

        return WrappedTool

    return decorator
