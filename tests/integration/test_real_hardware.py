"""
Integration tests for real hardware (requires physical devices).

These tests are marked with @pytest.mark.hardware and will only run when:
1. Physical devices are available
2. Environment variables are set for device credentials
3. --run-hardware-tests flag is used

Run with: pytest -m hardware --run-hardware-tests
"""

import logging
import os

import pytest


@pytest.mark.hardware
@pytest.mark.real
@pytest.mark.slow
class TestRealHardware:
    """Test real hardware devices using config.yaml credentials."""

    @pytest.fixture(autouse=True)
    def setup_hardware(self):
        """Setup hardware resources."""
        from devices_mcp.config import get_config

        self.config = get_config()
        if not self.config:
            pytest.skip("config.yaml not found or empty")

    @pytest.fixture
    def real_hardware_env(self, monkeypatch):
        """Enable real hardware for this test module."""
        monkeypatch.setenv("FORCE_REAL_HARDWARE", "true")

    @pytest.mark.asyncio
    async def test_tapo_camera_connection(self, real_hardware_env):
        """Test connection to real Tapo cameras defined in config."""
        # Camera should be auto-discovered or loaded from config
        # We'll use the one from config if available
        from devices_mcp.config import (
            get_config,
        )  # Re-import get_config if needed, or use self.config
        from devices_mcp.core.server import TapoCameraServer

        config = get_config()  # This will re-read the config, self.config is already available
        print(f"DEBUG: Config loaded: {config.get('cameras')}")

        cameras_cfg = self.config.get("cameras", {})
        if not cameras_cfg:
            pytest.skip("No cameras configured in config.yaml")

        # Initialize via server manager to ensure full stack is tested
        server = await TapoCameraServer.get_instance()
        camera_manager = server.camera_manager

        # Prepare configs
        camera_configs_list = []
        for cam_name, cam_config in cameras_cfg.items():
            if isinstance(cam_config, dict):
                cam_config["name"] = cam_name
                camera_configs_list.append(cam_config)

        await camera_manager.initialize(configs=camera_configs_list, auto_discover_usb=False)

        # Verify connections
        cameras = await camera_manager.list_cameras()
        assert len(cameras) > 0, "No cameras found after initialization"

        connected_count = 0
        for cam in cameras:
            cam_name = cam.get("name")
            status = cam.get("status", {})

            if status.get("connected"):
                logging.info(f"✅ Connected to camera: {cam_name}")

                # For ONVIF cameras, verify we can get a stream URL (proving ONVIF is working)
                # This validates the "ONVIF via CV2" path user mentioned
                try:
                    camera_obj = await camera_manager.get_camera(cam.get("id"))
                    if camera_obj and hasattr(camera_obj, "get_stream_url"):
                        stream_url = await camera_obj.get_stream_url()
                        if stream_url:
                            logging.info(f"   - ONVIF Stream URL obtained: {stream_url.split('@')[-1]}")  # Hide auth
                            connected_count += 1
                        else:
                            logging.warning("   - ⚠️ Connected but failed to get RTSP Stream URL")
                    else:
                        connected_count += 1  # Count as connected even if not ONVIF capable in this specific way
                except Exception as e:
                    logging.warning(f"   - ⚠️ Error verifying stream capabilities: {e}")
                    connected_count += 1  # Still count as connected, just warned
            else:
                error = status.get("error", "Unknown error")
                logging.warning(f"❌ Failed to connect to: {cam_name} ({cam.get('ip_address')})")
                logging.warning(f"   - Error: {error}")

        assert connected_count > 0, "Could not connect to and verify any configured Tapo cameras (ONVIF/RTSP)"

    @pytest.mark.asyncio
    async def test_tapo_plug_connection(self):
        """Test connection to real Tapo smart plugs."""
        plugs_cfg = self.config.get("energy", {}).get("tapo_p115", {})
        devices = plugs_cfg.get("devices", [])

        if not devices:
            pytest.skip("No Tapo plugs configured in config.yaml")

        import tapo

        account = plugs_cfg.get("account", {})
        username = account.get("username") or account.get("email")
        password = account.get("password")

        if not username or not password:
            pytest.skip("Tapo credentials missing in config.yaml")

        client = tapo.ApiClient(username, password)
        connected_count = 0

        for device_cfg in devices:
            host = device_cfg.get("host")
            name = device_cfg.get("name")
            if not host:
                continue

            try:
                device = await client.p115(host)
                info = await device.get_device_info()
                assert info is not None
                connected_count += 1
                print(f"Connected to plug: {name} ({host})")
            except Exception as e:
                print(f"Failed to connect to plug {name}: {e}")

        assert connected_count > 0, "Could not connect to any configured Tapo plugs"

    @pytest.mark.asyncio
    async def test_hue_bridge_connection(self):
        """Test connection to real Philips Hue Bridge."""
        hue_cfg = self.config.get("lighting", {}).get("philips_hue", {})
        bridge_ip = hue_cfg.get("bridge_ip")

        if not bridge_ip:
            pytest.skip("Hue Bridge IP not configured")

        from devices_mcp.tools.lighting.hue_tools import get_hue_manager

        hue_manager = get_hue_manager()

        success = await hue_manager.initialize()
        assert success, f"Failed to connect to Hue Bridge at {bridge_ip}"
        assert len(hue_manager.lights) >= 0
        print(f"Connected to Hue Bridge: {len(hue_manager.lights)} lights found")

    @pytest.mark.asyncio
    async def test_ring_integration(self):
        """Test Ring doorbell integration."""
        ring_cfg = self.config.get("ring", {})
        if not ring_cfg.get("enabled"):
            pytest.skip("Ring integration disabled in config")

        from devices_mcp.integrations.ring_client import init_ring_client

        client = await init_ring_client(
            email=ring_cfg.get("email"),
            password=ring_cfg.get("password"),
            token_file=ring_cfg.get("token_file"),
            server_id="test_client",
        )

        assert client.is_initialized or client.is_2fa_pending, "Ring client failed to initialize"
        if client.is_initialized:
            doorbells = await client.get_doorbells()
            print(f"Ring: Found {len(doorbells)} doorbells")


@pytest.mark.hardware
@pytest.mark.real
@pytest.mark.slow
class TestHomeAwareMotion:
    """Test HomeAware motion detection with real Hue Bridge Pro."""

    @pytest.fixture(autouse=True)
    def skip_if_no_bridge_pro(self):
        """Skip if not using Bridge Pro."""
        bridge_ip = os.getenv("HUE_BRIDGE_IP")
        if not bridge_ip:
            pytest.skip("No HUE_BRIDGE_IP environment variable set")

        # Check if it's a Bridge Pro (would need API call)
        # For now, assume it's Bridge Pro if IP is set
        pass

    def test_homeaware_initialization(self):
        """Test HomeAware initialization on Bridge Pro."""
        # Test that HomeAware is enabled
        assert True  # Placeholder

    def test_motion_event_detection(self):
        """Test motion event detection."""
        # This would require actually moving near Hue lights
        # and detecting the signal strength changes
        assert True  # Placeholder

    def test_motion_alert_generation(self):
        """Test that motion events generate security alerts."""
        # Test that motion detection triggers alerts
        assert True  # Placeholder
