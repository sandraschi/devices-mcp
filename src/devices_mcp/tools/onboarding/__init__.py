"""
Onboarding Tools Package

This package provides device discovery and onboarding tools for the
Devices MCP platform, enabling users to easily set up their
diverse device collections.
"""

from .device_discovery_tools import (
    CompleteOnboardingTool,
    ConfigureDeviceTool,
    DeviceDiscoveryManager,
    DiscoverDevicesTool,
    DiscoveredDevice,
    GetOnboardingProgressTool,
    OnboardingState,
    discovery_manager,
)

__all__ = [
    "CompleteOnboardingTool",
    "ConfigureDeviceTool",
    "DeviceDiscoveryManager",
    "DiscoverDevicesTool",
    "DiscoveredDevice",
    "GetOnboardingProgressTool",
    "OnboardingState",
    "discovery_manager",
]
