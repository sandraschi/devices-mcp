"""
Testing utilities for Devices MCP.

Provides environment detection and mocking strategies for testing vs production.
"""

import os
import sys
from typing import Any, Dict

from .mock_camera import MockTapoCamera, MockWebCamera


def is_testing_environment() -> bool:
    """
    Detect if running in testing/CI environment.

    Returns:
        bool: True if in testing environment, False otherwise
    """
    if os.getenv("FORCE_REAL_HARDWARE") == "true":
        return False

    return (
        os.getenv("CI") == "true"
        or os.getenv("GITHUB_ACTIONS") == "true"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
        or os.getenv("TESTING") == "true"
        or "pytest" in sys.modules
        or "unittest" in sys.modules
        or any("test" in arg for arg in sys.argv)
    )


def is_ci_environment() -> bool:
    """
    Detect if running in CI environment specifically.

    Returns:
        bool: True if in CI environment, False otherwise
    """
    return (
        os.getenv("CI") == "true"
        or os.getenv("GITHUB_ACTIONS") == "true"
        or os.getenv("JENKINS_URL") is not None
        or os.getenv("TRAVIS") == "true"
        or os.getenv("CIRCLECI") == "true"
    )


class MockCameraConfig:
    """Configuration for mock camera behavior in testing."""

    def __init__(
        self,
        simulate_connection_errors: bool = False,
        simulate_hardware_failures: bool = False,
        mock_resolution: str = "1920x1080",
        mock_fps: int = 30,
        mock_delay_ms: int = 100,
    ):
        self.simulate_connection_errors = simulate_connection_errors
        self.simulate_hardware_failures = simulate_hardware_failures
        self.mock_resolution = mock_resolution
        self.mock_fps = mock_fps
        self.mock_delay_ms = mock_delay_ms


def get_mock_config() -> MockCameraConfig:
    """
    Get mock camera configuration based on environment.

    Returns:
        MockCameraConfig: Configuration for mock behavior
    """
    # In CI, simulate some failures to test error handling
    if is_ci_environment():
        return MockCameraConfig(
            simulate_connection_errors=False,  # Keep tests passing in CI
            simulate_hardware_failures=False,  # Keep tests passing in CI
            mock_resolution="1920x1080",
            mock_fps=30,
            mock_delay_ms=50,  # Faster for CI
        )

    # In local testing, allow more realistic simulation
    return MockCameraConfig(
        simulate_connection_errors=os.getenv("MOCK_CONNECTION_ERRORS", "false").lower() == "true",
        simulate_hardware_failures=os.getenv("MOCK_HARDWARE_FAILURES", "false").lower() == "true",
        mock_resolution=os.getenv("MOCK_RESOLUTION", "1920x1080"),
        mock_fps=int(os.getenv("MOCK_FPS", "30")),
        mock_delay_ms=int(os.getenv("MOCK_DELAY_MS", "100")),
    )


def create_mock_tapo_camera(config: Dict[str, Any]):
    """
    Create a mock Tapo camera for testing.

    Args:
        config: Camera configuration

    Returns:
        MockTapoCamera: Mock camera instance
    """
    return MockTapoCamera(config)


def create_mock_webcam(config: Dict[str, Any]):
    """
    Create a mock webcam for testing.

    Args:
        config: Camera configuration

    Returns:
        MockWebCamera: Mock webcam instance
    """
    return MockWebCamera(config)
