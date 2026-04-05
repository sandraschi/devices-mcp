"""
Tests for Tapo lighting integration.
"""

import asyncio

import pytest

from devices_mcp.tools.lighting.tapo_lighting_tools import (
    TapoLight,
    TapoLightingManager,
)


class TestTapoLight:
    """Test TapoLight model."""

    def test_tapo_light_creation(self):
        """Test creating a TapoLight instance."""
        light = TapoLight(
            device_id="test_light_1",
            name="Test Light",
            location="Living Room",
            model="L900",
            on=True,
            brightness=80,
            reachable=True,
            last_seen="2024-01-01T12:00:00Z",
        )

        assert light.device_id == "test_light_1"
        assert light.name == "Test Light"
        assert light.location == "Living Room"
        assert light.model == "L900"
        assert light.on is True
        assert light.brightness == 80
        assert light.reachable is True

    def test_tapo_light_to_dict(self):
        """Test converting TapoLight to dictionary."""
        light = TapoLight(
            device_id="test_light_2",
            name="Test Light 2",
            location="Kitchen",
            model="L920",
            on=False,
            brightness=50,
            color_temp=2700,
            hue=120,
            saturation=80,
            effect="Rainbow",
            reachable=True,
            last_seen="2024-01-01T12:00:00Z",
        )

        data = light.model_dump()
        assert data["device_id"] == "test_light_2"
        assert data["name"] == "Test Light 2"
        assert data["on"] is False
        assert data["brightness"] == 50
        assert data["color_temp"] == 2700
        assert data["hue"] == 120
        assert data["saturation"] == 80
        assert data["effect"] == "Rainbow"


class TestTapoLightingManager:
    """Test TapoLightingManager functionality."""

    @pytest.fixture
    def lighting_manager(self):
        """Create a fresh TapoLightingManager instance."""
        manager = TapoLightingManager()
        # Reset the singleton state
        TapoLightingManager._instance = None
        TapoLightingManager._initialized = False
        TapoLightingManager._initializing = False
        return manager

    def test_manager_initialization(self, lighting_manager):
        """Test manager initialization."""
        assert not lighting_manager._initialized
        assert lighting_manager._devices == {}
        assert lighting_manager._config is None

    def test_get_all_lights_with_devices(self, lighting_manager):
        """Test getting all lights when devices exist."""
        lighting_manager._devices = {
            "light_1": TapoLight(
                device_id="light_1",
                name="Test Light",
                location="Living Room",
                model="L900",
                on=True,
                brightness=80,
                reachable=True,
                last_seen="2024-01-01T12:00:00Z",
            )
        }
        lighting_manager._initialized = True

        lights = asyncio.run(lighting_manager.get_all_lights())

        assert len(lights) == 1
        assert lights[0].device_id == "light_1"
        assert lights[0].name == "Test Light"

    def test_get_light(self, lighting_manager):
        """Test getting a specific light."""
        lighting_manager._devices = {
            "light_1": TapoLight(
                device_id="light_1",
                name="Test Light",
                location="Living Room",
                model="L900",
                on=True,
                brightness=80,
                reachable=True,
                last_seen="2024-01-01T12:00:00Z",
            )
        }
        lighting_manager._initialized = True

        light = asyncio.run(lighting_manager.get_light("light_1"))
        assert light is not None
        assert light.device_id == "light_1"

        # Test non-existent light
        light = asyncio.run(lighting_manager.get_light("nonexistent"))
        assert light is None

    def test_error_handling_uninitialized(self, lighting_manager):
        """Test error handling when manager is not initialized."""
        # Test with uninitialized manager
        lighting_manager._initialized = False
        result = asyncio.run(lighting_manager.get_all_lights())
        assert result == []
