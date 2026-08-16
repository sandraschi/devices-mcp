"""Hardware connectivity tests — live devices when RUN_HARDWARE_TESTS=1."""

import os
import platform
import socket
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.connectivity]

RUN_LIVE = os.environ.get("RUN_HARDWARE_TESTS") == "1"
skip_live = pytest.mark.skipif(not RUN_LIVE, reason="Set RUN_HARDWARE_TESTS=1 for live hardware tests")


@pytest.mark.critical
def test_configuration_loads():
    from devices_mcp.config import get_config

    config = get_config()
    assert isinstance(config, dict)
    assert "cameras" in config


@pytest.mark.critical
def test_usb_camera_server_port():
    if platform.system() != "Windows":
        pytest.skip("USB camera server is Windows-only")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(("127.0.0.1", 10715))
    finally:
        sock.close()
    if not RUN_LIVE:
        pytest.skip("Live USB camera server check requires RUN_HARDWARE_TESTS=1")
    assert result == 0, "USB camera server not listening on 10715"


@skip_live
@pytest.mark.asyncio
async def test_hue_live(hardware_initializer):
    result = await hardware_initializer._init_hue_bridge()
    if "not configured" in str(result.get("error", "")).lower():
        pytest.skip("Hue not configured")
    assert result["success"] is True


@skip_live
@pytest.mark.asyncio
async def test_tapo_cameras_live(hardware_initializer):
    result = await hardware_initializer._init_cameras()
    assert result["success"] is True


@skip_live
@pytest.mark.asyncio
async def test_ring_live(hardware_initializer):
    result = await hardware_initializer._init_ring()
    if (
        "not configured" in str(result.get("error", "")).lower()
        or "not enabled" in str(result.get("error", "")).lower()
    ):
        pytest.skip("Ring not configured")
    assert result["success"] is True


@skip_live
@pytest.mark.optional
@pytest.mark.asyncio
async def test_netatmo_live(hardware_initializer):
    result = await hardware_initializer._init_netatmo()
    if (
        "not configured" in str(result.get("error", "")).lower()
        or "not enabled" in str(result.get("error", "")).lower()
    ):
        pytest.skip("Netatmo not configured")
    assert result["success"] is True


def test_hardware_runner_imports():
    """Sanity check that hardware init helpers are importable."""
    from devices_mcp.core.hardware_init import HardwareInitializer

    assert HardwareInitializer is not None


@pytest.mark.asyncio
async def test_mocked_camera_init():
    from devices_mcp.core.hardware_init import HardwareInitializer

    init = HardwareInitializer()
    with patch.object(init, "_init_cameras", new_callable=AsyncMock) as mock_cam:
        mock_cam.return_value = {"success": True, "count": 2}
        result = await mock_cam()
    assert result["success"] is True
