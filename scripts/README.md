# Devices MCP Scripts

This directory contains utility scripts for managing the Devices MCP server.

## Portmanteau Tools Provision Script

**File**: `provision-portmanteau-tools.ps1`

**Purpose**: Verifies and provisions all portmanteau tools for the devices-mcp server.

**Status**: ✅ **PROVISION & REORGANIZATION COMPLETE** - 26 tools provisioned, consolidated to 16 functionality-based tools

**Last Provisioned**: 2025-12-27 - Fixed 6 missing imports/registrations

**Issues Resolved**:
- Added missing imports for: alerts_management, appliance_monitor_management, medical_management, messages_management, shelly_management, thermal_management
- Added missing registrations in portmanteau __init__.py
- Verified all 26 tools are properly integrated with server startup

**Reorganization Completed**:
- Consolidated 26 overlapping tools → 16 functionality-based tools
- Eliminated category overlap (lighting, kitchen, camera functions)
- Improved user experience with clear tool boundaries
- Reduced maintenance complexity

### What it does:
- Checks that all 26 portmanteau tool files exist
- Verifies Python syntax in each tool file
- Ensures all tools are properly imported in `__init__.py`
- Confirms all tools are registered in the registration function
- Validates integration with the main tool system and server

### Usage:

```powershell
# Basic verification (read-only)
.\scripts\provision-portmanteau-tools.ps1

# Automatic repair mode (fixes missing imports/registrations)
.\scripts\provision-portmanteau-tools.ps1 -Force

# Verbose logging for debugging
.\scripts\provision-portmanteau-tools.ps1 -Verbose

# Skip Python dependency checks
.\scripts\provision-portmanteau-tools.ps1 -SkipDependencies
```

### Portmanteau Tools Verified (26 total):

**Core Tools (11)**:
- `tapo_control` - Unified Tapo camera operations
- `camera_management` - Camera configuration and control
- `ptz_management` - Pan-tilt-zoom operations
- `media_management` - Video/audio streaming
- `energy_management` - Power monitoring and control
- `lighting_management` - Smart lighting control
- `kitchen_management` - Kitchen appliance control
- `security_management` - Security system management
- `system_management` - System diagnostics and control
- `weather_management` - Weather data and forecasting
- `configuration_management` - Server configuration

**Extended Tools (6)**:
- `ring_management` - Ring doorbell integration
- `audio_management` - Audio processing and streaming
- `motion_management` - Motion detection and alerts
- `home_assistant_management` - Home Assistant integration
- `robotics_management` - Robotics control (Moorebot Scout)
- `ai_analysis` - AI-powered scene analysis

**Advanced Tools (5)**:
- `automation_management` - Smart home automation
- `analytics_management` - Performance analytics
- `grafana_management` - Grafana dashboard integration
- `medical_management` - Medical device integration
- `thermal_management` - Thermal imaging and monitoring

**Latest Additions (4)**:
- `alerts_management` - Alert system management
- `appliance_monitor_management` - Appliance power monitoring
- `messages_management` - Message and notification handling
- `shelly_management` - **DEPRECATED** - Shelly smart device integration (not needed - already have Hue, Ring, Nest, Tapo integrations)
- `ring_management` - **WORKING** - Ring doorbell integration (connected: 1 doorbell "Front Door")

### Exit Codes:
- `0`: All tools properly provisioned
- `1`: Provision issues detected (run with `-Force` to repair)

### Requirements:
- PowerShell 5.1+
- Python 3.8+ (for syntax validation)
- Access to project source files

### When to Run:
- After adding new portmanteau tools
- Before deployment to verify completeness
- During development to catch missing registrations
- As part of CI/CD pipeline for validation

## Other Scripts

See individual script files for documentation on other utilities in this directory.
