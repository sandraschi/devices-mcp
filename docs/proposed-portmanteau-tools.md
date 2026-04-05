# Proposed Functionality-Based Portmanteau Tools

## Overview

Reorganize from **brand-based** to **functionality-based** tools. **TARGET: 16 core tools** (down from 26).

## Current vs Proposed Organization

### **Current (26 tools - Too Many):**
```
Brand-based with massive overlap:
- tapo_control: Tapo cams/plugs/lights/kitchen (overlaps with 4+ other tools)
- lighting_management: Hue lights (overlaps with tapo_control)
- Multiple redundant tools for same functions
- 26 tools total = overwhelming for users
```

### **Proposed (16 Core Tools - Consolidated):**
```
Functionality-based (no overlap, max 20 total):
1. lighting_management:     ALL lights (Hue + Tapo + future)
2. camera_management:       ALL cameras (Tapo + Ring + webcams)
3. energy_management:       ALL energy devices (plugs + monitors)
4. kitchen_management:      ALL kitchen appliances
5. security_management:     ALL security & safety systems
6. climate_management:      ALL climate/temperature control
7. automation_management:   Scenes, schedules, rules
8. system_management:       System control + configuration + analytics
9. media_management:        ALL streaming/recording
10. communication_management: Alerts + messages + notifications
11. robotics_management:    Robot control systems
12. medical_management:     Health monitoring devices
13. ai_analysis:            Computer vision & AI analysis
14. emergency_management:   Emergency response & panic systems
15. access_management:      Door locks & access control
16. maintenance_management: Device maintenance & diagnostics
```

---

## Core Functionality Tools (1-7)

## 1. lighting_management (All Lights)

**Purpose:** Unified control of all smart lighting regardless of brand.

**Supported Devices:**
- Philips Hue bulbs, strips, lamps
- Tapo lightstrips, smart bulbs
- Any future smart lighting brands

**Actions:**
```python
LIGHTING_ACTIONS = {
    "list_lights": "List all lights across all brands",
    "list_brand_lights": "List lights for specific brand (hue/tapo)",
    "turn_on_light": "Turn on specific light by ID",
    "turn_off_light": "Turn off specific light by ID",
    "set_brightness": "Set brightness (0-100%)",
    "set_color": "Set RGB color",
    "set_temperature": "Set color temperature (Kelvin)",
    "set_effect": "Set lighting effects (rainbow, strobe, etc.)",
    "list_groups": "List lighting groups/rooms",
    "list_scenes": "List available scenes",
    "activate_scene": "Activate lighting scene",
    "create_scene": "Create custom scene",
    "prank_mode": "Fun lighting effects (chaos, wave, disco)"
}
```

**Brands Supported:** Hue, Tapo, future additions

---

## 2. camera_management (All Cameras)

**Purpose:** Unified control of all cameras and video devices.

**Supported Devices:**
- Tapo cameras, doorbells, floodlights
- Ring cameras, doorbells
- Webcams, IP cameras
- Any RTSP/ONVIF cameras

**Actions:**
```python
CAMERA_ACTIONS = {
    "list_cameras": "List all cameras across all brands",
    "list_brand_cameras": "List cameras for specific brand",
    "get_snapshot": "Take photo from camera",
    "start_stream": "Start video stream",
    "stop_stream": "Stop video stream",
    "get_stream_url": "Get RTSP/stream URL",
    "set_quality": "Set video quality/resolution",
    "detect_motion": "Enable/disable motion detection",
    "get_motion_events": "Get recent motion events",
    "night_vision": "Enable/disable night vision",
    "ptz_control": "Pan-tilt-zoom control",
    "two_way_audio": "Enable two-way audio",
    "record_video": "Start/stop video recording"
}
```

**Brands Supported:** Tapo, Ring, future IP camera brands

---

## 3. energy_management (All Energy Devices)

**Purpose:** Monitor and control all energy-consuming devices.

**Supported Devices:**
- Tapo P115 smart plugs
- Shelly smart plugs (if used)
- Energy monitoring sensors
- Smart outlets, switches

**Actions:**
```python
ENERGY_ACTIONS = {
    "list_devices": "List all energy devices",
    "get_power_usage": "Get current power consumption",
    "get_energy_history": "Get energy usage over time",
    "turn_on_device": "Turn on smart plug/device",
    "turn_off_device": "Turn off smart plug/device",
    "set_schedule": "Schedule device on/off times",
    "get_efficiency": "Get energy efficiency metrics",
    "detect_anomalies": "Detect unusual power usage",
    "cost_analysis": "Calculate energy costs",
    "standby_detection": "Detect vampire power usage"
}
```

**Brands Supported:** Tapo, Shelly, future smart plug brands

---

## 4. kitchen_management (All Kitchen Appliances)

**Purpose:** Control smart kitchen appliances and monitoring.

**Supported Devices:**
- Zojirushi kettles, rice cookers
- Smart coffee makers
- Refrigerator temperature monitors
- Smart ovens, dishwashers
- Any IoT kitchen devices

**Actions:**
```python
KITCHEN_ACTIONS = {
    "list_appliances": "List all kitchen appliances",
    "turn_on_appliance": "Turn on specific appliance",
    "turn_off_appliance": "Turn off specific appliance",
    "get_status": "Get appliance status/temperature",
    "set_temperature": "Set target temperature",
    "set_timer": "Set cooking/heating timer",
    "get_energy_usage": "Monitor appliance energy consumption",
    "maintenance_alerts": "Get maintenance reminders",
    "recipe_integration": "Smart recipe timing",
    "food_safety": "Temperature monitoring for food safety"
}
```

**Brands Supported:** Zojirushi, future smart kitchen brands

---

## 5. security_management (All Security & Safety Systems)

**Purpose:** Comprehensive home security and safety system management.

**Supported Devices:**
- **Visual Security:** Cameras, doorbells, floodlights (Tapo, Ring, others)
- **Entry Protection:** Door/window sensors, smart locks, glass break sensors
- **Intrusion Detection:** Motion detectors, burglar alarms, perimeter sensors
- **Fire Safety:** Smoke detectors, fire alarms, heat sensors (Nest Protect, etc.)
- **Gas Safety:** Gas leak detectors, CO alarms
- **Water Safety:** Flood sensors, water leak detectors
- **Emergency Systems:** Panic buttons, medical alerts

**Actions:**
```python
SECURITY_ACTIONS = {
    # System Control
    "list_devices": "List all security and safety devices",
    "arm_system": "Arm security system (burglar mode)",
    "disarm_system": "Disarm security system",
    "get_system_status": "Get current security system status",

    # Alerts & Events
    "get_alerts": "Get recent security/safety alerts",
    "get_fire_alerts": "Get fire/smoke/gas alerts",
    "get_water_alerts": "Get water leak/flood alerts",
    "get_burglar_alerts": "Get intrusion/burglar alerts",
    "clear_alerts": "Clear active alerts",

    # Camera & Visual
    "live_view": "Start live camera view",
    "motion_zones": "Configure motion detection zones",
    "night_vision": "Enable/disable night vision on cameras",

    # Sensors & Detectors
    "test_detectors": "Test smoke/CO/gas detectors",
    "calibrate_sensors": "Calibrate sensors",
    "battery_status": "Check device battery levels",

    # Emergency & Safety
    "emergency_panic": "Trigger emergency alarm/panic button",
    "evacuation_alert": "Trigger evacuation alert",
    "silence_alarms": "Silence active alarms",

    # Access Control
    "lock_doors": "Lock all smart doors",
    "unlock_doors": "Unlock all smart doors",
    "access_logs": "View access/security logs",

    # Settings
    "alert_settings": "Configure alert preferences",
    "sensitivity_settings": "Configure sensor sensitivity",
    "schedule_settings": "Set arm/disarm schedules"
}
```

**Safety Categories:**
- 🏠 **Burglar Protection:** Cameras, motion sensors, door sensors, alarms
- 🔥 **Fire Protection:** Smoke detectors, fire alarms, heat sensors
- 💨 **Gas Protection:** Gas leak detectors, CO monitors
- 💧 **Water Protection:** Flood sensors, leak detectors
- 🚨 **Emergency:** Panic buttons, medical alerts, evacuation systems

**Brands Supported:** Tapo, Ring, Nest Protect, Netatmo, future security/safety brands

---

## 6. climate_management (All Climate Control)

**Purpose:** Temperature, humidity, and climate control.

**Supported Devices:**
- Temperature sensors (Shelly, Netatmo)
- Humidity sensors
- Thermostats, HVAC controls
- Weather stations
- Ventilation systems

**Actions:**
```python
CLIMATE_ACTIONS = {
    "list_sensors": "List all climate sensors",
    "get_temperature": "Get current temperature readings",
    "get_humidity": "Get current humidity levels",
    "set_target_temp": "Set target temperature",
    "climate_schedule": "Set heating/cooling schedules",
    "air_quality": "Monitor air quality metrics",
    "ventilation_control": "Control ventilation systems",
    "weather_integration": "Integrate weather station data",
    "comfort_profiles": "Create comfort/temperature profiles",
    "energy_saving": "Optimize for energy efficiency"
}
```

**Brands Supported:** Netatmo, Shelly (if used), future climate brands

---

## 7. automation_management (Smart Home Automation)

**Purpose:** Scenes, schedules, and smart home rules.

**Supported Devices:**
- Lighting scenes across brands
- Scheduled automation
- Voice assistant integration
- Smart home rules engine

**Actions:**
```python
AUTOMATION_ACTIONS = {
    "list_scenes": "List all automation scenes",
    "create_scene": "Create new automation scene",
    "activate_scene": "Activate specific scene",
    "schedule_scene": "Schedule scene activation",
    "create_rule": "Create automation rule",
    "list_rules": "List automation rules",
    "enable_rule": "Enable/disable automation rule",
    "voice_commands": "Voice assistant integration",
    "geo_fencing": "Location-based automation",
    "sunrise_sunset": "Time-based solar automation"
}
```

**Brands Supported:** Cross-brand scene management

---

## Extended Functionality Tools (8-10)

## 8. system_management (System Control & Analytics)

**Purpose:** Comprehensive system management, configuration, and analytics.

**Supported Systems:**
- System diagnostics and health monitoring
- Configuration management and settings
- Performance analytics and reporting
- System maintenance and updates
- Network monitoring and connectivity

**Actions:**
```python
SYSTEM_ACTIONS = {
    "get_system_status": "Get overall system health",
    "get_system_config": "Get current system configuration",
    "update_system_config": "Update system settings",
    "get_system_logs": "Retrieve system logs",
    "get_performance_metrics": "Get system performance data",
    "run_system_diagnostics": "Run comprehensive diagnostics",
    "get_network_status": "Check network connectivity",
    "manage_system_backups": "Manage system backups",
    "update_system_firmware": "Update system firmware",
    "reboot_system": "Reboot system components"
}
```

**Systems Supported:** All MCP components, network devices, system services

## 9. media_management (All Media & Streaming)

**Purpose:** Unified media streaming, recording, and content management.

**Supported Media:**
- Video streaming from all cameras
- Audio streaming and recording
- Screen recording and capture
- Media file management
- Live streaming controls

**Actions:**
```python
MEDIA_ACTIONS = {
    "start_stream": "Start media streaming",
    "stop_stream": "Stop media streaming",
    "record_media": "Start/stop media recording",
    "get_stream_url": "Get streaming URLs",
    "manage_recordings": "Manage recorded media files",
    "stream_to_device": "Stream to specific devices",
    "adjust_stream_quality": "Change stream quality/settings",
    "schedule_recording": "Schedule automated recordings",
    "manage_media_storage": "Manage media storage space",
    "share_media": "Share media streams/recordings"
}
```

**Media Types:** Video, audio, screen capture, streaming services

## 10. communication_management (Alerts & Messages)

**Purpose:** Unified communication, alerts, and notification management.

**Supported Communication:**
- System alerts and notifications
- User messages and announcements
- Emergency communications
- Status updates and reports
- Multi-channel delivery (dashboard, email, SMS, push)

**Actions:**
```python
COMMUNICATION_ACTIONS = {
    "send_alert": "Send system alerts",
    "send_message": "Send user messages",
    "get_alerts": "Retrieve active alerts",
    "get_messages": "Retrieve messages",
    "configure_notifications": "Configure notification preferences",
    "set_alert_rules": "Configure alert rules and thresholds",
    "manage_alert_history": "Manage alert/message history",
    "send_emergency_alert": "Send emergency notifications",
    "schedule_messages": "Schedule automated messages",
    "manage_communication_channels": "Manage delivery channels"
}
```

**Channels Supported:** Dashboard, email, SMS, push notifications, voice alerts

---

## Specialized Tools (11-16)

## 11. robotics_management (Robot Control)

**Purpose:** Control and management of robotic systems and automation.

**Supported Robots:**
- Moorebot Scout and similar robotic platforms
- Robotic arms and manipulators
- Autonomous mobile robots
- Robotic process automation systems

**Actions:**
```python
ROBOTICS_ACTIONS = {
    "connect_robot": "Connect to robotic systems",
    "get_robot_status": "Get robot status and telemetry",
    "send_robot_command": "Send movement/navigation commands",
    "start_autonomous_mode": "Start autonomous operation",
    "stop_robot": "Stop robot operation",
    "get_robot_sensors": "Retrieve sensor data",
    "update_robot_firmware": "Update robot firmware",
    "configure_robot_settings": "Configure robot parameters",
    "monitor_robot_health": "Monitor robot system health",
    "emergency_stop": "Emergency stop all robot functions"
}
```

**Robots Supported:** Moorebot Scout, industrial robots, service robots

## 12. medical_management (Health Monitoring)

**Purpose:** Health monitoring devices and medical system integration.

**Supported Devices:**
- Medical sensors and wearables
- Health monitoring equipment
- Medical alert systems
- Telemedicine integration
- Health data management

**Actions:**
```python
MEDICAL_ACTIONS = {
    "get_health_status": "Get health monitoring status",
    "monitor_vitals": "Monitor vital signs",
    "send_medical_alert": "Send medical emergency alerts",
    "manage_health_data": "Manage health records",
    "configure_health_alerts": "Configure health alert thresholds",
    "integrate_medical_devices": "Integrate medical devices",
    "get_medical_history": "Retrieve medical history",
    "schedule_health_checks": "Schedule health monitoring",
    "manage_medical_contacts": "Manage emergency contacts",
    "privacy_controls": "Manage health data privacy"
}
```

**Devices Supported:** Wearables, vital sign monitors, medical IoT devices

## 13. ai_analysis (Computer Vision & AI)

**Purpose:** AI-powered analysis, computer vision, and intelligent processing.

**Supported Analysis:**
- Computer vision and object detection
- Image and video analysis
- Pattern recognition and anomaly detection
- AI-powered automation and insights
- Machine learning model management

**Actions:**
```python
AI_ANALYSIS_ACTIONS = {
    "analyze_image": "Analyze images with AI",
    "analyze_video": "Analyze video streams",
    "detect_objects": "Object detection in media",
    "recognize_patterns": "Pattern recognition and analysis",
    "detect_anomalies": "Anomaly detection in data",
    "generate_insights": "Generate AI-powered insights",
    "train_models": "Train/update AI models",
    "manage_ai_models": "Manage AI model lifecycle",
    "process_natural_language": "Natural language processing",
    "automate_decisions": "AI-powered decision automation"
}
```

**AI Capabilities:** Computer vision, NLP, anomaly detection, predictive analytics

## 14. emergency_management (Emergency Response)

**Purpose:** Emergency response, crisis management, and safety protocols.

**Supported Scenarios:**
- Fire emergencies and evacuation
- Medical emergencies
- Security breaches and lockdowns
- Natural disasters and alerts
- Emergency communication and coordination

**Actions:**
```python
EMERGENCY_ACTIONS = {
    "activate_emergency_mode": "Activate emergency response mode",
    "trigger_evacuation": "Trigger evacuation procedures",
    "send_emergency_alerts": "Send emergency notifications",
    "coordinate_response": "Coordinate emergency response",
    "lockdown_system": "Initiate system lockdown",
    "emergency_communication": "Emergency communication channels",
    "first_aid_guidance": "Provide first aid instructions",
    "emergency_contacts": "Contact emergency services",
    "monitor_emergency_status": "Monitor emergency situation",
    "deactivate_emergency": "Deactivate emergency mode"
}
```

**Emergency Types:** Fire, medical, security, natural disasters

## 15. access_management (Door Locks & Access)

**Purpose:** Access control, door locks, and security entry management.

**Supported Systems:**
- Smart door locks and deadbolts
- Access control systems
- Keypad and card readers
- Biometric access systems
- Remote access management

**Actions:**
```python
ACCESS_ACTIONS = {
    "unlock_door": "Unlock specific doors",
    "lock_door": "Lock specific doors",
    "grant_access": "Grant temporary access",
    "revoke_access": "Revoke access permissions",
    "manage_access_codes": "Manage access codes and keys",
    "get_access_logs": "Retrieve access logs",
    "configure_auto_lock": "Configure auto-lock settings",
    "manage_users": "Manage user access permissions",
    "schedule_access": "Schedule access permissions",
    "emergency_access": "Emergency access override"
}
```

**Access Systems:** Smart locks, keypads, biometric readers, access cards

## 16. maintenance_management (Device Maintenance)

**Purpose:** Device maintenance, diagnostics, and lifecycle management.

**Supported Maintenance:**
- Device health monitoring
- Firmware updates and patches
- Battery management and replacement
- Sensor calibration and testing
- Preventive maintenance scheduling

**Actions:**
```python
MAINTENANCE_ACTIONS = {
    "check_device_health": "Check device health status",
    "schedule_maintenance": "Schedule maintenance tasks",
    "update_firmware": "Update device firmware",
    "calibrate_devices": "Calibrate sensors and devices",
    "replace_batteries": "Battery replacement alerts",
    "run_diagnostics": "Run device diagnostics",
    "manage_warranties": "Manage device warranties",
    "predict_failures": "Predict device failures",
    "generate_reports": "Generate maintenance reports",
    "manage_spare_parts": "Manage spare parts inventory"
}
```

**Maintenance Types:** Firmware, batteries, calibration, diagnostics, preventive care

---

## Implementation Benefits

### **User Experience:**
- **One Tool Per Function**: "lights" controls ALL lights
- **Brand Agnostic**: Users don't need to know device brands
- **Complete Coverage**: All devices of same type in one place

### **Developer Experience:**
- **Clear Boundaries**: One responsibility per tool
- **Consistent APIs**: Similar patterns across brands
- **Easy Extension**: Add new brands without changing tools

### **Maintenance:**
- **No Overlap**: Clear separation prevents confusion
- **Unified Updates**: Feature updates apply to all brands
- **Simplified Testing**: Test functionality, not brands
