"""About and general help tool for Nest Protect MCP."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AboutParams(BaseModel):
    """Parameters for getting about information."""

    level: Literal["simple", "intermediate", "technical"] = Field(
        "simple", description="Level of detail (simple, intermediate, technical)"
    )


async def about_server(
    level: Literal["simple", "intermediate", "technical"] = "simple",
) -> dict[str, Any]:
    """Get information about what this MCP server is and what it can do."""

    if level == "simple":
        return {
            "status": "success",
            "about": {
                "title": "🏠 Nest Protect MCP Server",
                "what_is_it": "A smart home control server that lets you monitor and control your Nest Protect smoke and CO detectors through Claude AI.",
                "what_can_it_do": [
                    "📱 Check if your smoke detectors are working",
                    "🔔 Silence false alarms remotely",
                    "🧪 Run safety tests on your devices",
                    "🚨 Sound alarms for testing (with volume control)",
                    "🔒 Arm/disarm Nest security systems",
                    "📊 View device status and battery levels",
                    "🔍 Search through device event history",
                    "⚙️ Manage server settings and authentication",
                ],
                "supported_devices": {
                    "currently_supported": [
                        "🔥 Nest Protect (2nd Generation) - Smoke + CO detector",
                        "🔥 Nest Protect (1st Generation) - Smoke + CO detector",
                    ],
                    "coming_soon": [
                        "🌡️ Nest Thermostat (planned)",
                        "📹 Nest Cameras (planned)",
                        "🚪 Nest Hello Doorbell (planned)",
                        "🔒 Nest × Yale Lock (planned)",
                    ],
                },
                "how_to_use": "Just ask Claude to check your smoke detectors, run a safety test, or silence an alarm. Claude will use this server to talk to your Nest devices!",
                "note": "You need to set up Google Cloud API access and OAuth to connect to your real Nest devices.",
            },
        }

    if level == "intermediate":
        return {
            "status": "success",
            "about": {
                "title": "🏠 Nest Protect MCP Server - Intermediate Guide",
                "overview": "This Model Context Protocol (MCP) server provides Claude AI with the ability to interact with Nest smart home devices through Google's Smart Device Management API.",
                "capabilities": {
                    "device_monitoring": [
                        "Real-time device status (online/offline, battery levels)",
                        "Smoke, CO, and heat sensor readings",
                        "Device connectivity and network status",
                        "Historical event data and alerts",
                    ],
                    "device_control": [
                        "Remote alarm silencing (hush function)",
                        "Manual safety test execution (smoke, CO, heat tests)",
                        "LED brightness adjustment",
                        "Device configuration updates",
                    ],
                    "system_management": [
                        "OAuth 2.0 authentication with Google",
                        "Configuration management (TOML/JSON)",
                        "System health monitoring",
                        "Comprehensive help and documentation system",
                    ],
                },
                "supported_devices": {
                    "nest_protect": {
                        "models": [
                            "Nest Protect 2nd Gen (2015+)",
                            "Nest Protect 1st Gen (2013-2014)",
                        ],
                        "features": [
                            "Smoke detection",
                            "CO detection",
                            "Heat sensing",
                            "Motion sensing",
                            "Night light",
                        ],
                        "controllable": [
                            "Alarm hush",
                            "Safety tests",
                            "LED brightness",
                            "Night light settings",
                        ],
                    },
                    "planned_support": {
                        "nest_thermostat": {
                            "models": [
                                "Nest Learning Thermostat",
                                "Nest Thermostat E",
                                "Nest Thermostat",
                            ],
                            "features": [
                                "Temperature control",
                                "Schedule management",
                                "Energy history",
                            ],
                        },
                        "nest_cameras": {
                            "models": [
                                "Nest Cam Indoor/Outdoor",
                                "Nest Cam IQ",
                                "Nest Hello",
                            ],
                            "features": [
                                "Live streaming",
                                "Motion detection",
                                "Person alerts",
                            ],
                        },
                    },
                },
                "tool_categories": {
                    "device_status": "3 tools for monitoring device health and events",
                    "device_control": "5 tools for controlling device functions (including alarm testing and security)",
                    "system_status": "3 tools for server and API monitoring",
                    "authentication": "3 tools for OAuth setup and token management",
                    "configuration": "5 tools for server configuration management",
                    "help": "5 tools for documentation and assistance",
                },
                "requirements": {
                    "google_cloud": "Google Cloud Project with Smart Device Management API enabled",
                    "oauth_setup": "OAuth 2.0 client credentials from Google Cloud Console",
                    "device_access": "Device Access Console subscription ($5 USD one-time fee)",
                    "nest_account": "Google account with Nest devices linked",
                },
            },
        }

    # technical
    return {
        "status": "success",
        "about": {
            "title": "🏠 Nest Protect MCP Server - Technical Documentation",
            "architecture": {
                "protocol": "Model Context Protocol (MCP) over STDIO transport",
                "framework": "FastMCP 2.12.3 with Pydantic data validation",
                "api_integration": "Google Smart Device Management API v1",
                "authentication": "OAuth 2.0 with PKCE for secure token exchange",
                "state_management": "Centralized app state with persistent token storage",
            },
            "api_endpoints": {
                "device_management": [
                    "GET /enterprises/{project_id}/devices - List all devices",
                    "GET /enterprises/{project_id}/devices/{device_id} - Get device details",
                    "GET /enterprises/{project_id}/devices/{device_id}/events - Get device events",
                    "POST /enterprises/{project_id}/devices/{device_id}:executeCommand - Execute device commands",
                ],
                "supported_commands": [
                    "sdm.devices.commands.SafetyHush.Hush - Silence active alarms",
                    "sdm.devices.commands.SafetyTest.SelfTest - Run safety diagnostics",
                    "sdm.devices.commands.Settings.LedBrightness - Adjust LED brightness",
                ],
                "device_traits": [
                    "sdm.devices.traits.Info - Device model and name",
                    "sdm.devices.traits.Connectivity - Online status",
                    "sdm.devices.traits.Battery - Battery level and status",
                    "sdm.devices.traits.Smoke - Smoke sensor readings",
                    "sdm.devices.traits.CarbonMonoxide - CO sensor readings",
                    "sdm.devices.traits.Heat - Heat sensor readings",
                    "sdm.devices.traits.SafetyAlarm - Alarm status and events",
                ],
            },
            "supported_devices_technical": {
                "nest_protect_2nd_gen": {
                    "device_type": "sdm.devices.types.SMOKE_DETECTOR",
                    "model_numbers": ["05A", "06A"],
                    "supported_traits": [
                        "Info",
                        "Connectivity",
                        "Battery",
                        "Smoke",
                        "CarbonMonoxide",
                        "Heat",
                        "SafetyAlarm",
                    ],
                    "supported_commands": [
                        "SafetyHush.Hush",
                        "SafetyTest.SelfTest",
                        "Settings.LedBrightness",
                    ],
                    "sensors": {
                        "smoke": "Photoelectric sensor with Steam Check™",
                        "co": "Electrochemical CO sensor",
                        "heat": "Heat rise and absolute temperature detection",
                        "motion": "PIR motion sensor for pathlight",
                    },
                },
                "nest_protect_1st_gen": {
                    "device_type": "sdm.devices.types.SMOKE_DETECTOR",
                    "model_numbers": ["01A", "02A", "03A"],
                    "supported_traits": [
                        "Info",
                        "Connectivity",
                        "Battery",
                        "Smoke",
                        "CarbonMonoxide",
                        "SafetyAlarm",
                    ],
                    "supported_commands": [
                        "SafetyHush.Hush",
                        "SafetyTest.SelfTest",
                    ],
                    "limitations": ["No Heat trait", "No LED brightness control"],
                },
            },
            "planned_device_support": {
                "nest_thermostat": {
                    "device_types": ["sdm.devices.types.THERMOSTAT"],
                    "traits": [
                        "ThermostatTemperatureSetpoint",
                        "ThermostatMode",
                        "ThermostatEco",
                        "ThermostatHvac",
                        "Temperature",
                        "Humidity",
                    ],
                    "commands": [
                        "ThermostatTemperatureSetpoint.SetHeat",
                        "ThermostatTemperatureSetpoint.SetCool",
                        "ThermostatMode.SetMode",
                    ],
                },
                "nest_cameras": {
                    "device_types": [
                        "sdm.devices.types.CAMERA",
                        "sdm.devices.types.DOORBELL",
                    ],
                    "traits": [
                        "CameraLiveStream",
                        "CameraEventImage",
                        "CameraMotion",
                        "CameraPerson",
                        "CameraSound",
                        "DoorbellChime",
                    ],
                    "commands": [
                        "CameraLiveStream.GenerateRtspStream",
                        "CameraEventImage.GenerateImage",
                    ],
                },
            },
            "tool_implementation": {
                "total_tools": 21,
                "parameter_validation": "Pydantic BaseModel schemas with field validation",
                "error_handling": "Comprehensive try-catch with detailed error messages",
                "async_support": "Full async/await pattern with aiohttp for HTTP calls",
                "state_management": "Centralized get_app_state() function",
                "help_system": "Multi-level documentation with examples and search",
            },
            "security": {
                "oauth_flow": "OAuth 2.0 with state parameter for CSRF protection",
                "token_storage": "In-memory storage (not persistent across restarts)",
                "api_permissions": "Read/write access to user's Nest devices only",
                "scope": "https://www.googleapis.com/auth/sdm.service",
            },
            "development": {
                "language": "Python 3.8+",
                "dependencies": [
                    "fastmcp>=3.1.0",
                    "aiohttp>=3.8.0",
                    "pydantic>=2.0.0",
                    "psutil>=5.9.0",
                ],
                "configuration": "TOML-based config with environment variable support",
                "logging": "Structured logging with configurable levels",
                "testing": "Comprehensive tool registration and API integration tests",
            },
        },
    }


async def get_supported_devices() -> dict[str, Any]:
    """Get detailed information about supported and planned devices."""
    return {
        "status": "success",
        "devices": {
            "currently_supported": {
                "nest_protect_2nd_generation": {
                    "name": "Nest Protect (2nd Generation)",
                    "release_year": "2015-present",
                    "model_numbers": ["05A", "06A"],
                    "features": [
                        "🔥 Split-spectrum smoke sensor",
                        "☠️ Electrochemical CO sensor",
                        "🌡️ Heat sensor",
                        "💡 Motion-activated pathlight",
                        "🔔 Spoken alerts in multiple languages",
                        "📱 Smartphone notifications",
                        "🔗 Wireless interconnection",
                        "🔋 10-year battery life (battery version)",
                    ],
                    "controllable_features": [
                        "Alarm silencing (hush)",
                        "Manual safety tests",
                        "LED brightness adjustment",
                        "Pathlight settings",
                    ],
                    "available_models": [
                        "Nest Protect 2nd Gen (Wired 120V)",
                        "Nest Protect 2nd Gen (Battery)",
                    ],
                },
                "nest_protect_1st_generation": {
                    "name": "Nest Protect (1st Generation)",
                    "release_year": "2013-2014",
                    "model_numbers": ["01A", "02A", "03A"],
                    "features": [
                        "🔥 Photoelectric smoke sensor",
                        "☠️ Electrochemical CO sensor",
                        "🔔 Spoken alerts",
                        "📱 Basic smartphone notifications",
                        "🔗 Wireless interconnection",
                    ],
                    "controllable_features": [
                        "Alarm silencing (hush)",
                        "Manual safety tests",
                    ],
                    "limitations": [
                        "No heat sensing",
                        "No pathlight",
                        "No LED brightness control",
                        "Limited customization options",
                    ],
                    "note": "⚠️ 1st generation devices have limited API support",
                },
            },
            "planned_support": {
                "nest_thermostats": {
                    "nest_learning_thermostat": {
                        "name": "Nest Learning Thermostat (3rd Gen)",
                        "features": [
                            "Auto-scheduling",
                            "Home/Away assist",
                            "Energy history",
                            "Remote control",
                        ],
                        "eta": "Q2 2025",
                    },
                    "nest_thermostat_e": {
                        "name": "Nest Thermostat E",
                        "features": [
                            "Proven energy saving",
                            "Simple scheduling",
                            "Home/Away assist",
                        ],
                        "eta": "Q2 2025",
                    },
                    "nest_thermostat_2020": {
                        "name": "Nest Thermostat (2020)",
                        "features": [
                            "Mirror display",
                            "Savings finder",
                            "Quick schedule",
                        ],
                        "eta": "Q2 2025",
                    },
                },
                "nest_cameras": {
                    "nest_cam_indoor": {
                        "name": "Nest Cam Indoor/Outdoor",
                        "features": [
                            "1080p HD",
                            "Night vision",
                            "Motion detection",
                            "24/7 streaming",
                        ],
                        "eta": "Q3 2025",
                    },
                    "nest_cam_iq": {
                        "name": "Nest Cam IQ Indoor/Outdoor",
                        "features": [
                            "4K sensor",
                            "Person alerts",
                            "Face recognition",
                            "Zoom tracking",
                        ],
                        "eta": "Q3 2025",
                    },
                    "nest_hello": {
                        "name": "Nest Hello Video Doorbell",
                        "features": [
                            "HD video",
                            "Person detection",
                            "Pre-recorded messages",
                            "24/7 streaming",
                        ],
                        "eta": "Q3 2025",
                    },
                },
                "nest_security": {
                    "nest_x_yale_lock": {
                        "name": "Nest × Yale Lock",
                        "features": [
                            "Keyless entry",
                            "Passcode management",
                            "Auto-lock",
                            "Remote control",
                        ],
                        "eta": "Q4 2025",
                    },
                    "nest_secure_guard": {
                        "name": "Nest Guard (Discontinued)",
                        "status": "⚠️ Discontinued - Limited API support",
                        "features": [
                            "Security hub",
                            "Keypad",
                            "Motion detection",
                            "Alarm system",
                        ],
                        "note": "Works if still connected, but no new installations",
                    },
                    "nest_detect": {
                        "name": "Nest Detect (Discontinued)",
                        "status": "⚠️ Discontinued - Limited API support",
                        "features": [
                            "Motion/door sensor",
                            "Security system integration",
                        ],
                        "note": "Works if still connected, but no new installations",
                    },
                },
            },
            "requirements": {
                "all_devices": [
                    "Google account with Nest devices",
                    "Google Cloud Project with Device Access API",
                    "OAuth 2.0 credentials setup",
                    "Device Access Console subscription ($5 USD)",
                ],
                "network": [
                    "Wi-Fi connection for all devices",
                    "Internet connectivity",
                    "Google Nest app setup completed",
                ],
            },
            "compatibility_notes": {
                "works_with": [
                    "Google Assistant",
                    "Google Home app",
                    "This MCP server",
                    "IFTTT (limited)",
                    "SmartThings (select devices)",
                ],
                "limitations": [
                    "Requires Google ecosystem",
                    "No local-only control",
                    "Internet dependency",
                    "API rate limits apply",
                ],
            },
        },
    }
