"""
Vienna home-rig default template (Stroheckgasse / 192.168.0.x LAN).

Used when no config.yaml exists or `home_preset: vienna` is set.
Credentials are placeholders — replace in config.yaml before use.
Discovery flags default to on so LAN scan can override static hosts.
"""

from __future__ import annotations

from typing import Any

VIENNA_SUBNET_BROADCAST = "192.168.0.255"
TIMEZONE = "Europe/Vienna"


def get_vienna_default_config() -> dict[str, Any]:
    """Return a full config skeleton for the Vienna rig (no real secrets)."""
    return {
        "server": {
            "host": "0.0.0.0",  # nosec B104
            "port": 10717,
            "debug": False,
            "log_level": "INFO",
        },
        "home_preset": "vienna",
        "discovery": {
            "enabled": True,
            "tapo_p115": True,
            "tapo_p115_broadcast": VIENNA_SUBNET_BROADCAST,
            "usb_cameras": True,
            "philips_hue": True,
            "tapo_lighting": True,
            "ring": False,
            "shelly": False,
            "nest_home_assistant": True,
        },
        "cameras": {
            "tapo_kitchen": {
                "type": "onvif",
                "host": "192.168.0.164",
                "username": "YOUR_TAPO_USERNAME",
                "password": "YOUR_TAPO_PASSWORD",
                "rtsp_port": 554,
                "onvif_port": 2020,
            },
            "tapo_living_room": {
                "type": "onvif",
                "host": "192.168.0.206",
                "username": "YOUR_TAPO_USERNAME",
                "password": "YOUR_TAPO_PASSWORD",
                "rtsp_port": 554,
                "onvif_port": 2020,
            },
            "usb_microscope": {
                "type": "microscope",
                "device_id": 0,
                "resolution": "1280x720",
            },
            "usb_webcam": {
                "type": "webcam",
                "device_id": 1,
                "resolution": "1920x1080",
            },
        },
        "energy": {
            "tapo_p115": {
                "electricity_rate": 0.25,
                "account": {
                    "username": "YOUR_TAPO_CLOUD_EMAIL",
                    "password": "YOUR_TAPO_CLOUD_PASSWORD",
                },
                "devices": [
                    {
                        "host": "192.168.0.17",
                        "device_id": "tapo_p115_aircon",
                        "name": "Aircon",
                        "location": "Living room",
                    },
                    {
                        "host": "192.168.0.137",
                        "device_id": "tapo_p115_kitchen",
                        "name": "Kitchen Zojirushi",
                        "location": "Kitchen",
                    },
                    {
                        "host": "192.168.0.38",
                        "device_id": "tapo_p115_server",
                        "name": "Server rack",
                        "location": "Office",
                    },
                ],
                "discovery": {
                    "enabled": True,
                    "broadcast": VIENNA_SUBNET_BROADCAST,
                    "timeout": 10,
                },
            },
        },
        "lighting": {
            "philips_hue": {
                "bridge_ip": "192.168.0.83",
                "username": "YOUR_HUE_API_KEY",
                "auto_discover": True,
            },
            "tapo_lighting": {
                "account": {
                    "username": "YOUR_TAPO_CLOUD_EMAIL",
                    "password": "YOUR_TAPO_CLOUD_PASSWORD",
                },
                "devices": [
                    {
                        "host": "192.168.0.172",
                        "device_id": "tapo_l900_lightstrip",
                        "name": "Lightstrip L900",
                    },
                ],
            },
        },
        "ring": {
            "enabled": False,
            "email": "YOUR_RING_EMAIL",
            "password": "YOUR_RING_PASSWORD",
            "token_file": "ring_token.cache",
        },
        "shelly": {
            "enabled": False,
            "devices": [],
        },
        "security": {
            "integrations": {
                "homeassistant": {
                    "enabled": False,
                    "url": "http://192.168.0.10:8123",
                    "access_token": "YOUR_HA_LONG_LIVED_TOKEN",
                },
            },
        },
        "weather": {
            "integrations": {
                "netatmo": {
                    "enabled": False,
                    "client_id": "",
                    "client_secret": "",
                    "refresh_token": "",
                },
                "openmeteo": {
                    "enabled": True,
                    "latitude": 48.2082,
                    "longitude": 16.3738,
                    "location_name": "Vienna, Austria",
                    "timezone": TIMEZONE,
                },
            },
        },
        "public_webcams": {
            "vienna_webcams": {
                "enabled": True,
                "region": "Wien",
            },
        },
        "alerts": {
            "regions": ["Wien"],
        },
        "web": {
            "enabled": True,
            "host": "0.0.0.0",  # nosec B104
            "port": 10717,
            "theme": "dark",
        },
        "logging": {
            "level": "INFO",
            "file": "devices-mcp.log",
        },
        "robotics_mcp": {
            "devices": {
                "dreame_d20": {"host": "192.168.0.144", "enabled": False},
                "yahboom_car": {"host": "192.168.0.100", "enabled": False},
            },
        },
    }


def get_generic_default_config() -> dict[str, Any]:
    """Minimal generic LAN template with discovery on."""
    cfg = get_vienna_default_config()
    cfg["home_preset"] = "generic"
    cfg["cameras"] = {
        "example_tapo": {
            "type": "tapo",
            "host": "192.168.1.100",
            "username": "YOUR_TAPO_USERNAME",
            "password": "YOUR_TAPO_PASSWORD",
        },
    }
    cfg["energy"]["tapo_p115"]["devices"] = []
    cfg["energy"]["tapo_p115"]["discovery"]["broadcast"] = "255.255.255.255"
    cfg["lighting"]["philips_hue"]["bridge_ip"] = "192.168.1.2"
    cfg["discovery"]["tapo_p115_broadcast"] = "255.255.255.255"
    return cfg


def resolve_preset_config(preset: str | None) -> dict[str, Any]:
    """Map home_preset name to a default config dict."""
    key = (preset or "vienna").strip().lower()
    if key in ("off", "none", "empty"):
        return {"home_preset": "off", "discovery": {"enabled": False}, "cameras": {}}
    if key == "generic":
        return get_generic_default_config()
    return get_vienna_default_config()
