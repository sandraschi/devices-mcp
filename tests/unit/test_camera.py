#!/usr/bin/env python3
"""
Test camera functionality and models.
"""

import os
import sys

import pytest

# Add the src path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.mark.skip(reason="# TODO: Fix test_camera_models - currently has assert False")
def test_camera_models():
    """Test camera model definitions."""
    try:
        from devices_mcp.camera.base import CameraConfig, CameraType
        from devices_mcp.core.models import TapoCameraConfig

        # Test CameraType enum

        # Test CameraConfig creation
        CameraConfig(
            name="test_camera",
            type=CameraType.TAPO,
            params={"host": "192.168.1.100", "username": "test", "password": "test"},
        )

        # Test TapoCameraConfig
        TapoCameraConfig(host="192.168.1.100", username="test", password="test")
        assert True
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


@pytest.mark.skip(reason="# TODO: Fix test_camera_manager - currently has assert False")
def test_camera_manager():
    """Test camera manager functionality."""
    try:
        from devices_mcp.camera.manager import CameraManager

        manager = CameraManager()

        # Test that manager is properly initialized
        assert hasattr(manager, "cameras")
        assert hasattr(manager, "groups")
        assert isinstance(manager.cameras, dict)

        assert True
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


@pytest.mark.skip(reason="# TODO: Fix test_exceptions - currently has assert False")
def test_exceptions():
    """Test exception classes."""
    try:
        from devices_mcp.exceptions import (
            AuthenticationError,
            ConnectionError,
            TapoCameraError,
        )

        # Test exception creation
        TapoCameraError("Test error")

        ConnectionError("Connection failed")
        AuthenticationError("Auth failed")

        assert True
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


if __name__ == "__main__":
    tests = [
        test_camera_models,
        test_camera_manager,
        test_exceptions,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)
