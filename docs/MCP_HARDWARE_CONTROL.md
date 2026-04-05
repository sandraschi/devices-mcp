# MCP Hardware Control Guide

**Last Updated:** November 26, 2025

This document outlines all hardware that can be controlled and queried via the MCP server.

---

## 🎯 Available Hardware Control Tools

### 1. **Lighting Management** (`lighting_management`)

**Philips Hue Integration** - Full control of all Hue lights, groups, and scenes.

**Actions:**
- `list_lights` - List all Philips Hue lights
- `get_light` - Get specific light status (requires: `light_id`)
- `control_light` - Control a light (requires: `light_id`, optional: `on`, `brightness_percent`, `color_temp_kelvin`)
- `list_groups` - List all Hue groups/rooms
- `control_group` - Control all lights in a group (requires: `group_id`, optional: `on`, `brightness_percent`)
- `list_scenes` - List all available scenes (filtered to unique predefined scenes)
- `activate_scene` - Activate a lighting scene (requires: `scene_id`, optional: `group_id`)
- `status` - Get Hue Bridge connection status

**Example MCP Calls:**
```
# List all lights
lighting_management(action="list_lights")

# Turn on bathroom light at 80% brightness
lighting_management(action="control_light", light_id="3", on=True, brightness_percent=80)

# Activate "Relax" scene
lighting_management(action="activate_scene", scene_id="abc123")

# Turn on all lights in living room
lighting_management(action="control_group", group_id="1", on=True)
```

**Hardware:**
- ✅ 16 Philips Hue lights
- ✅ 6 groups/rooms
- ✅ 10 unique predefined scenes (Arctic aurora, Bright, Concentrate, Dimmed, Energize, Nightlight, Read, Relax, Savanna sunset, Spring blossom, Tropical twilight)

---

### 2. **Energy Management** (`energy_management`)

**Tapo P115 Smart Plugs** - Monitor and control smart plugs for energy management.

**Actions:**
- `status` - Get smart plug status (optional: `device_id` for specific device)
- `control` - Control smart plug power (requires: `device_id`, `power_state`: "on"/"off"/"toggle")
- `consumption` - Get energy consumption data (optional: `device_id`, `time_range`)
- `cost` - Get energy cost analysis (optional: `device_id`, `time_range`)

**Example MCP Calls:**
```
# Get status of all smart plugs
energy_management(action="status")

# Turn on Aircon plug
energy_management(action="control", device_id="tapo_aircon", power_state="on")

# Get energy consumption for last 7 days
energy_management(action="consumption", time_range="7d")
```

**Hardware:**
- ✅ 3 Tapo P115 smart plugs (Aircon, Kitchen Zojirushi, Server)
- ✅ Real-time power monitoring (wattage, voltage, current)
- ✅ Energy consumption tracking
- ✅ Cost analysis

---

### 3. **Kitchen Management** (`kitchen_management`)

**Kitchen Appliances** - Control appliances connected via smart plugs.

**Actions:**
- `list_appliances` - List all kitchen appliances (connected via smart plugs)
- `control_appliance` - Control appliance power (requires: `device_id`, `power_state`)
- `get_appliance_status` - Get appliance status and power consumption (requires: `device_id`)
- `get_energy_usage` - Get energy usage data (optional: `device_id`, `time_range`)

**Example MCP Calls:**
```
# List all kitchen appliances
kitchen_management(action="list_appliances")

# Turn on Zojirushi kettle
kitchen_management(action="control_appliance", device_id="kitchen_zojirushi", power_state="on")

# Get Tefal Optigrill status
kitchen_management(action="get_appliance_status", device_id="kitchen_optigrill")
```

**Hardware:**
- ✅ Zojirushi Water Boiler & Warmer (via Tapo P115 - on/off control, energy monitoring)
- ✅ Tefal Optigrill (via smart plug - on/off control only, no temperature control)
- ⚠️ **Limitations:** No remote temperature control or advanced settings (must be set manually on device)

---

### 4. **Camera Management** (`camera_management`)

**Security Cameras** - Control and monitor security cameras.

**Actions:**
- `list` - List all cameras
- `status` - Get camera status
- `start_stream` - Start video streaming
- `stop_stream` - Stop video streaming
- `capture` - Capture snapshot
- `info` - Get camera information

**Hardware:**
- ✅ USB Webcams (auto-detected)
- ⚠️ Tapo Cameras (authentication issues - in progress)
- ⚠️ Ring Cameras (OAuth setup needed)
- ⚠️ Nest Protect (OAuth setup needed)

---

### 5. **PTZ Management** (`ptz_management`)

**Camera PTZ Control** - Pan, tilt, zoom controls for cameras.

**Actions:**
- `move` - Move PTZ camera
- `position` - Get current PTZ position
- `stop` - Stop PTZ movement
- `save_preset` - Save current position as preset
- `recall_preset` - Move to saved preset
- `list_presets` - List all saved presets
- `delete_preset` - Delete a preset
- `home` - Move to home position

**Hardware:**
- ✅ PTZ-capable cameras (when available)

---

### 6. **Media Management** (`media_management`)

**Camera Media** - Capture and record media from cameras.

**Actions:**
- `capture` - Capture image
- `capture_still` - Capture still image
- `analyze` - Analyze captured image
- `start_recording` - Start video recording
- `stop_recording` - Stop video recording
- `get_stream_url` - Get stream URL

**Hardware:**
- ✅ All connected cameras

---

### 7. **Security Management** (`security_management`)

**Security Systems** - Monitor and control security devices.

**Actions:**
- `nest_status` - Get Nest Protect status
- `nest_alerts` - Get Nest Protect alerts
- `nest_battery` - Get Nest Protect battery status
- `test_nest` - Test Nest Protect device
- `correlate_events` - Correlate Nest camera events
- `security_scan` - Perform security scan
- `analyze_scene` - Analyze camera scene

**Hardware:**
- ⚠️ Nest Protect (OAuth setup needed)
- ⚠️ Ring Alarms (OAuth setup needed)

---

### 8. **Weather Management** (`weather_management`)

**Weather Stations** - Monitor weather data.

**Actions:**
- `current` - Get current weather data
- `historical` - Get historical weather data
- `stations` - List weather stations
- `alerts` - Configure weather alerts
- `health` - Get weather station health
- `analyze` - Analyze weather patterns

**Hardware:**
- ⚠️ Netatmo Weather Station (OAuth setup needed)

---

### 9. **System Management** (`system_management`)

**System Control** - Monitor and control the MCP server system.

**Actions:**
- `info` - Get system information
- `status` - Get system status
- `health` - Perform health check
- `reboot` - Reboot camera
- `logs` - Get system logs

---

### 10. **Configuration Management** (`configuration_management`)

**Device Settings** - Configure device settings and privacy.

**Actions:**
- `device_settings` - Manage device settings
- `privacy_settings` - Manage privacy settings
- `led_control` - Control LED
- `motion_detection` - Configure motion detection
- `privacy_mode` - Configure privacy mode

---

## 📊 Hardware Status Summary

| Hardware Type | Device | Status | MCP Control | Notes |
|--------------|--------|--------|-------------|-------|
| **Lighting** | Philips Hue (16 lights) | ✅ Working | ✅ Full | Lights, groups, scenes |
| **Energy** | Tapo P115 (3 plugs) | ✅ Working | ✅ Full | On/off, monitoring, cost |
| **Kitchen** | Zojirushi Kettle | ✅ Working | ✅ Partial | On/off via smart plug only |
| **Kitchen** | Tefal Optigrill | ✅ Working | ✅ Partial | On/off via smart plug only |
| **Robots** | Roomba | ⚠️ Planned | ❌ None | Integration in development |
| **Robots** | Unitree Go2 | ⚠️ Planned | ❌ None | Spring 2025 purchase |
| **Cameras** | USB Webcams | ✅ Working | ✅ Full | Auto-detected |
| **Cameras** | Tapo Cameras | ⚠️ Auth Issues | ⚠️ Partial | Authentication problems |
| **Security** | Nest Protect | ⚠️ OAuth Needed | ⚠️ Partial | OAuth setup required |
| **Security** | Ring Cameras | ⚠️ OAuth Needed | ⚠️ Partial | OAuth setup required |
| **Weather** | Netatmo | ⚠️ OAuth Needed | ⚠️ Partial | OAuth setup required |

---

## 🚀 Quick Start Examples

### Control All Hardware via MCP

```python
# Turn on all lights in living room
lighting_management(action="control_group", group_id="1", on=True)

# Activate "Relax" scene for evening
lighting_management(action="activate_scene", scene_id="relax_scene_id")

# Turn on Zojirushi kettle for tea
kitchen_management(action="control_appliance", device_id="kitchen_zojirushi", power_state="on")

# Check energy usage for kitchen appliances
kitchen_management(action="get_energy_usage", time_range="24h")

# Monitor all smart plugs
energy_management(action="status")

# Turn off Aircon when leaving
energy_management(action="control", device_id="tapo_aircon", power_state="off")
```

---

## 📝 Notes

- **Kitchen Appliances:** Limited to on/off control via smart plugs. Temperature and advanced settings must be set manually on devices.
- **Scenes:** Only unique predefined scenes are shown (10 scenes instead of 52 duplicates).
- **Energy Monitoring:** Real-time power consumption tracking available for all Tapo P115 devices.
- **Lighting:** Full control including brightness, color temperature, and scene activation.

---

*For detailed API documentation, see individual tool docstrings in the codebase.*
