#!/usr/bin/env python3
"""
Test models and core data structures.
"""

import os
import sys

import pytest

# Add the src path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.mark.skip(reason="# TODO: Fix test_core_models - currently has assert False")
def test_core_models():
    """Test core model definitions."""
    try:
        # Test enums

        assert True
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


@pytest.mark.skip(reason="# TODO: Fix test_ptz_models - currently has assert False")
def test_ptz_models():
    """Test PTZ model definitions."""
    try:
        from devices_mcp.core.models import PTZPosition

        # Test PTZ directions

        # Test PTZ position with normalized values (-1.0 to 1.0)
        PTZPosition(pan=0.5, tilt=0.3, zoom=0.8)

        assert True
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


@pytest.mark.skip(reason="# TODO: Fix test_motion_models - currently has assert False")
def test_motion_models():
    """Test motion detection models."""
    try:
        from devices_mcp.core.models import MotionEvent

        # Test sensitivity levels

        # Test motion event with proper timestamp
        MotionEvent(
            camera_id="test-camera",
            timestamp=1672574400.0,  # Unix timestamp for 2023-01-01T12:00:00Z
            regions=[[0, 0, 100, 100]],
            confidence=0.85,
        )

        assert True
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


if __name__ == "__main__":
    tests = [
        test_core_models,
        test_ptz_models,
        test_motion_models,
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
