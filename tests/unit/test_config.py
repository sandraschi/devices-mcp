"""
Unit tests for configuration handling.
"""

import os
import tempfile

import pytest

from devices_mcp.config import ConfigManager, get_config


class TestConfigManager:
    """Test configuration manager."""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_config_loading(self):
        """Test config loading with mocked file."""
        config_data = {
            "server": {"host": "0.0.0.0", "port": 7777, "debug": False, "log_level": "WARNING"},
            "cameras": {
                "tapo_kitchen": {
                    "type": "tapo",
                    "params": {"host": "192.168.0.100", "username": "test", "password": "test"},
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Test config loading
            config = ConfigManager(config_path)
            assert config.get("server.host") == "0.0.0.0"
            assert config.get("server.port") == 7777
            assert config.get("cameras.tapo_kitchen.type") == "tapo"
        finally:
            os.unlink(config_path)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_config_defaults(self):
        """Test config default values."""
        config = ConfigManager()  # Load default config

        # Test that defaults are set
        assert config.get("web.host") is not None
        assert config.get("web.port") is not None
        assert config.get("debug") is not None


class TestGlobalConfig:
    """Test global config functions."""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_get_config_function(self):
        """Test get_config function returns valid config."""
        config = get_config()

        # Should return a dict-like object
        assert hasattr(config, "get")
        # Config should be loaded (not None)
        assert config is not None
