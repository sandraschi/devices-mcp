# schip-mcp-devices — User Guide

## Quick Start

### Prerequisites
- Python 3.10+ with `uv` package manager
- At least one smart home device (Tapo camera/plug/light, Ring doorbell, Hue light, etc.)
- For Plex integration: a running Plex Media Server

### Installation
```bash
git clone https://github.com/sandraschi/devices-mcp
cd devices-mcp
uv sync
cp config.example.yaml config.yaml
# Edit config.yaml with your device credentials
```

### Start the Server
```bash
# MCP stdio mode (for Claude Desktop / Cursor)
uv run python -m devices_mcp.server_v2

# MCP HTTP mode
uv run python -m devices_mcp.server_v2 --http --port 8000

# Full webapp (backend + frontend)
.\web-sota\start.ps1
# Opens http://localhost:10716 (frontend) proxied to :10717 (backend)
```

### Register with Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:/Dev/repos/devices-mcp", "python", "-m", "devices_mcp.server_v2"],
      "env": { "PYTHONPATH": "${workspaceFolder}/src" }
    }
  }
}
```

## Tutorials

### Tutorial 1: List and Monitor All Cameras
List all connected cameras and check their status:
```
camera_management(action="list")
```
Returns device IDs, names, connection status, and stream URLs. To get detailed info on a specific camera:
```
camera_management(action="info", camera_id="living_room")
```

### Tutorial 2: Control Smart Lighting
List available lights:
```
lighting_management(action="list")
```
Turn a light on with specific brightness and color:
```
lighting_management(action="control", device_id="lamp_desk", power_state="on", brightness_percent=80, rgb=[255, 200, 100])
```
Set a dynamic effect:
```
lighting_management(action="effects")
lighting_management(action="control", device_id="lamp_desk", effect="sunset", animation_speed=50)
```

### Tutorial 3: Monitor Energy Consumption
Check smart plug status and power usage:
```
energy_management(action="status", device_id="coffee_maker_plug")
```
Get consumption history:
```
energy_management(action="consumption", device_id="living_room_tv_plug")
```
Calculate cost:
```
energy_management(action="cost", device_id="ev_charger_plug", rate_per_kwh=0.30)
```

### Tutorial 4: Manage Plex Media Library
List all Plex libraries:
```
plex_library(operation="list")
```
Search for media:
```
plex_media(operation="search", query="Inception", library_id="1")
```
Browse recently added:
```
plex_media(operation="get_recent", library_id="1", limit=10)
```
Create a playlist:
```
plex_playlist(operation="create", title="Weekend Mix", items=["12345", "67890"])
```

### Tutorial 5: Plex Streaming Control
List active sessions:
```
plex_streaming(operation="list_sessions")
```
Play media on a client:
```
plex_streaming(operation="play", client_id="office-chrome", media_key="54321")
```
Adjust volume and seek:
```
plex_streaming(operation="set_volume", client_id="office-chrome", volume=50)
plex_streaming(operation="seek", client_id="office-chrome", seek_to=120000)
```

### Tutorial 6: Security System Management
Check alarm status:
```
security_management(action="status")
```
Arm the system:
```
security_management(action="arm", mode="away")
```
View event history:
```
security_management(action="history", limit=20)
```
Get active alerts:
```
security_management(action="alerts")
```

### Tutorial 7: Ring Device Operations
List all Ring devices:
```
ring_management(action="devices")
```
Get live stream from a Ring camera:
```
ring_management(action="stream", device_id="front_doorbell")
```
Trigger doorbell chime:
```
ring_management(action="chime", device_id="front_doorbell")
```
Check system status:
```
ring_management(action="system")
```

### Tutorial 8: AI-Powered Scene Analysis
Analyze a camera scene:
```
ai_analysis(action="analyze_scene", camera_id="front_yard", confidence_threshold=0.8, analysis_type="comprehensive")
```
Detect specific objects:
```
ai_analysis(action="detect_objects", camera_id="garage", confidence_threshold=0.6)
```
Classify the scene type:
```
ai_analysis(action="classify_scene", camera_id="living_room")
```

### Tutorial 9: Weather Monitoring
Get current weather:
```
weather_management(action="current")
```
View weather alerts:
```
weather_management(action="alerts")
```
Analyze recent trends:
```
weather_management(action="analyze")
```

### Tutorial 10: Home Automation
Schedule security modes:
```
automation_management(action="create", name="Night Mode", trigger="time", condition="22:00", actions=["security:arm:away", "lights:off:all"])
```
Create a motion-triggered automation:
```
automation_management(action="create", name="Porch Light", trigger="motion", device_id="front_door", actions=["lighting:on:porch"])
```
List and manage automations:
```
automation_management(action="list")
automation_management(action="enable", automation_id="1")
automation_management(action="disable", automation_id="2")
```

### Tutorial 11: Plex Library Health and Optimization
Analyze library for issues:
```
plex_organization(operation="organize", library_id="1", dry_run=True)
```
Empty trash and clean bundles:
```
plex_library(operation="empty_trash", library_id="1")
plex_library(operation="clean_bundles", library_id="1")
```
Optimize database:
```
plex_organization(operation="optimize_database", vacuum=True, reindex=True)
```

### Tutorial 12: Cross-Device Emergency Response
Assess home safety:
```
assess_home_safety()
```
Coordinate emergency response across devices:
```
coordinate_emergency_response()
```
Monitor real-time activity:
```
get_real_time_activity()
```

### Tutorial 13: Kitchen and Appliance Control
List smart kitchen appliances:
```
kitchen_management(action="list_appliances")
```
Control an appliance:
```
kitchen_management(action="control_appliance", device_id="coffee_maker", command="brew")
```
Boil the iKettle:
```
ikettle_management(action="status")
ikettle_management(action="boil", temperature=100)
ikettle_management(action="keep_warm", temperature=70, duration_minutes=30)
```

### Tutorial 14: System Diagnostics
Full system health check:
```
system_management(action="health")
```
View system logs:
```
system_management(action="logs", lines=50)
```
Get detailed system info:
```
system_management(action="info")
```

### Tutorial 15: Plex Agentic Workflows
Multi-step Plex operations:
```
agentic_plex_workflow(workflow_prompt="Find all unwatched sci-fi movies and create a playlist", available_tools=["plex_search", "plex_playlist", "plex_media"])
```
Natural language assistant:
```
plex_natural_assistant(user_query="What's new in my library this week?")
```

## API Reference

### REST Endpoints (Web Dashboard Backend)
The FastAPI backend runs on port 10717 with the following endpoints:

**GET /health** — Server health check
Response: `{"status": "healthy", "service": "devices-mcp", "version": "2.4.0"}`

**GET /api/devices** — List all devices
Response: Array of device objects with id, name, type, status, metadata

**GET /api/devices/{id}** — Get specific device details

**POST /api/devices/{id}/command** — Send command to device
Body: `{"command": "on", "params": {"brightness": 80}}`

**GET /api/events** — Get recent events (query: ?limit=50&since=2025-01-01)

**GET /api/automations** — List automations

**POST /api/automations** — Create automation

**GET /api/health/summary** — Overall system health summary

**GET /api/logs** — Recent log entries (query: ?lines=100&level=INFO)

**GET /api/config** — Current configuration

**PUT /api/config** — Update configuration

### MCP Tool Response Format
All portmanteau tools return a standardized response:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... },
  "action": "list"
}
```

On error:
```json
{
  "success": false,
  "error": "Device not found: camera_123",
  "error_type": "not_found"
}
```

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| Camera not connecting | Wrong credentials or network | Verify RTSP URL and credentials; check firewall |
| Tapo device offline | Cloud auth expired | Run `check_authentication_status()` and reconfigure |
| Plex not responding | Server down or token expired | Verify Plex URL and token in config |
| Ring integration failing | Token refresh needed | Use `configure_auth()` with new tokens |
| AI analysis returns empty | No camera feed | Check camera connectivity first |
| Lighting control fails | Hue bridge not on network | Verify Hue bridge IP and pairing |
| Server won't start | Port conflict | Check :10717 and :10716 are free |
| "config file not found" | Missing config.yaml | Copy config.example.yaml to config.yaml |
| Permission error on USB | No access to device | Run as administrator for Dymo/USB devices |
| Weather data stale | API key limit | Check OpenWeatherMap API key quota |
| Automation not firing | Service not initialized | Run `system_management(action="initialize")` |

## FAQ

**Q: Can I run the server without any smart home devices?**
A: Yes. The server starts without hardware and exposes system management tools. You can configure devices later through the API.

**Q: How do I add a new Tapo camera?**
A: Use camera_management(action="add", camera_id="new_cam", rtsp_url="rtsp://...", name="Backyard Cam", credentials={"user": "admin", "pass": "..."}).

**Q: Does this work with Home Assistant?**
A: Yes. Home Assistant can be configured as a data source for entity states and service calls.

**Q: How do I sync Plex with the server?**
A: Set PLEX_URL and PLEX_TOKEN in config.yaml or environment variables. The server auto-connects on startup.

**Q: Can I create automations across different device types?**
A: Yes. Automations can chain actions across cameras, lights, locks, and security systems.

**Q: What about privacy?**
A: All processing is local. Camera feeds stay on your network unless you explicitly configure external access. Privacy mode can disable cameras entirely.

**Q: How do I update the server?**
A: `git pull && uv sync` to update. Config is preserved.

**Q: Can I use this with Claude Desktop?**
A: Yes. Register as an MCP server in claude_desktop_config.json with stdio transport.

**Q: Does this work with the Tauri desktop app?**
A: Yes. Build the NSIS installer with `.\native\build.ps1` for a self-contained desktop application.

**Q: How do I get help for a specific tool?**
A: Use get_tool_help(tool_name="camera_management") or search_tools(query="lighting").

## Complete Device Integration Guide

### Adding a New Tapo Camera
The server supports Tapo/Kasa cameras through the Tapo cloud API. To add a new camera:
1. Ensure your Tapo credentials (email + password) are configured in config.yaml
2. Use camera_management(action="add", camera_id="garage", name="Garage Camera", camera_type="tapo", device_ip="192.168.1.100")
3. The server authenticates with the Tapo cloud, discovers the device, and adds it to the device registry
4. Verify with camera_management(action="status", camera_id="garage")
5. Test snapshot capture: capture_snapshot(camera_id="garage")
If the camera is not automatically discovered, ensure it is powered on and connected to the same network as the server. Some older Tapo firmware versions may require cloud-only mode.

### Adding a Ring Device
Ring devices require OAuth2 authentication. The first-time setup flow is:
1. Run configure_auth() to start the authentication process
2. Follow the OAuth2 URL returned by configure_auth to authorize the application
3. Copy the callback URL from your browser after authorization and paste it into the tool
4. The server stores the refresh token for automatic token renewal
5. Verify with ring_management(action="devices") to see your Ring devices
Ring devices include doorbells (video doorbell, pro, elite), security cameras (stick up cam, floodlight cam, indoor cam), and alarm systems (Ring Alarm base station, contact sensors, motion detectors, range extenders). Each device type has specific capabilities accessible through the ring_management portmanteau tool.

### Configuring Philips Hue Lights
Philips Hue lights are controlled locally through the Hue bridge:
1. Ensure your Hue bridge is powered on and connected to the same network as the server
2. If auto-discovery fails, set the bridge IP in config.yaml: hue.bridge_ip: "192.168.1.200"
3. The server automatically pairs with the Hue bridge on first startup
4. Verify with lighting_management(action="list") — Hue bulbs appear alongside Tapo devices
5. Hue-specific features like scenes, groups, and schedules are accessible through the same lighting_management portmanteau
Hue bulbs typically respond faster than cloud-dependent Tapo devices because all communication remains on the local network. The server supports all Hue bulb types including white, white ambiance, and full color (Play, Bloom, Go, Lightstrip, and standard bulbs).

### Integrating with Home Assistant
Home Assistant integration provides access to hundreds of additional device types:
1. Generate a Long-Lived Access Token in your Home Assistant profile page
2. Configure home_assistant.url and home_assistant.token in config.yaml
3. The server connects to Home Assistant's WebSocket API for real-time state updates
4. Use home_assistant_management(action="status") to verify connectivity
5. Use home_assistant_management(action="entities") to browse all available devices
6. Use home_assistant_management(action="call_service", domain="light", service="turn_on", service_data={"entity_id": "light.living_room"}) to control devices through HA
The Home Assistant bridge supports all domains: light, switch, sensor, binary_sensor, cover, lock, climate, fan, vacuum, media_player, alarm_control_panel, and more. Nest Protect status is also available through Home Assistant if the Nest integration is configured in HA.

### Setting Up iKettle
The iKettle smart kettle uses WiFi for direct control:
1. Configure the iKettle WiFi connection using the Smarter app (iOS/Android)
2. The kettle appears as a WiFi device on your network
3. Use ikettle_management(action="status") to detect the kettle
4. If not auto-detected, check that the kettle is on the same network as the server
5. Test with ikettle_management(action="boil", temperature=100)
The iKettle supports temperature settings from 40°C to 100°C, keep-warm mode for configurable durations, and real-time temperature monitoring. The server reports current water temperature, heating status, and keep-warm remaining time.

### Configuring Dymo Label Printer
Dymo LabelWriter printers are connected via USB:
1. Connect the Dymo printer via USB and install the Dymo software
2. The server auto-detects connected Dymo printers
3. Use dymo_management(action="print", text="Storage Box 3", width="12mm") to print a label
4. Supported widths: 6mm, 9mm, 12mm, 19mm, 24mm
5. The server handles label formatting, text truncation, and font sizing automatically
Labels can include text, barcodes, and basic formatting. The printer is accessible through the Dymo SDK which must be installed separately.

### Setting Up Weather Stations
The server supports multiple weather sources:
1. OpenWeatherMap: Configure weather.api_key and weather.latitude/weather.longitude in config.yaml
2. Personal weather stations: Connect a USB weather station or configure a WiFi-enabled station
3. Use weather_management(action="stations") to see all configured sources
4. Use weather_management(action="current") for consolidated conditions
5. Historical data: weather_management(action="historical", date_from="2025-01-01", date_to="2025-01-07")
Weather data is cached locally for 5 minutes to reduce API calls. Alerts from the National Weather Service are included where available.

### Configuring Plex Media Server
Full Plex integration requires:
1. Plex Media Server running and accessible on your network
2. Configure plex.url and plex.token in config.yaml or set PLEX_URL and PLEX_TOKEN environment variables
3. The Plex token can be obtained from your Plex web app: Settings > Plex Web > Show Advanced > Access Token
4. Verify with plex_server(operation="status")
5. All Plex tools are immediately available after connection
The Plex integration supports multiple servers through the MCP bridge proxy system if configured.

## Protocol Reference

### Tool Call Format
All MCP tool calls use JSON-RPC 2.0. The request format is:

### Config File Structure
The config.yaml file uses YAML with the following top-level sections. Each section can be omitted if the corresponding integration is not used.

```yaml
tapo:
  email: "user@example.com"
  password: "your_password"
  cloud_url: "https://eu.tapo.com"  # Regional endpoint
  device_refresh_interval: 300       # Seconds between device list refresh

ring:
  access_token: "token_from_oauth"
  refresh_token: "token_for_refresh"
  hardware_id: "unique_device_id"     # Required for 2FA
  two_factor_token: "2fa_code"        # Optional, if 2FA is enabled

nest_protect:
  access_token: "nest_access_token"
  issue_token: "nest_issue_token"
  cookies: "nest_cookies_string"

plex:
  url: "http://localhost:32400"
  token: "plex_x_token"
  timeout: 30                         # Request timeout in seconds
  verify_ssl: true                    # Disable for self-signed certs

home_assistant:
  url: "http://localhost:8123"
  token: "long_lived_access_token"
  websocket: true                     # Use WS for real-time updates

hue:
  bridge_ip: "192.168.1.100"         # Auto-discovered if empty
  username: "hue_api_username"

weather:
  provider: "openweathermap"
  api_key: "owm_api_key"
  latitude: 48.2082
  longitude: 16.3738
  units: "metric"

llm:
  providers:
    - type: ollama
      url: "http://localhost:11434"
      model: "gemma3:1b"             # Default model for analysis
    - type: lm_studio
      url: "http://localhost:1234/v1"
      model: "qwen2.5-7b-instruct"

logging:
  level: "INFO"                       # DEBUG, INFO, WARNING, ERROR
  file: "~/.local/share/devices-mcp/devices-mcp.log"
  max_size_mb: 50                     # Log rotation size
  backup_count: 5                     # Number of rotated logs to keep
```

### Camera RTSP Setup Guide
To add an RTSP camera that is not from Tapo or Ring, follow these steps:
1. Ensure the camera supports RTSP protocol (check camera documentation for the exact RTSP URL format)
2. Common RTSP URL patterns: rtsp://IP:554/stream1, rtsp://IP:554/live/ch00_0, rtsp://user:pass@IP:554/onvif/profile1
3. Add the camera using camera_management: `camera_management(action="add", camera_id="garage", rtsp_url="rtsp://192.168.1.50:554/stream1", name="Garage Camera", credentials={"username": "admin", "password": "secret"})`
4. Verify connectivity: `camera_management(action="status", camera_id="garage")`
5. Test snapshot: `capture_snapshot(camera_id="garage")`

### Multi-Service Integration
The server can simultaneously control devices from different ecosystems. For example, a "Good Night" routine might:
1. Turn off all lights via lighting_management
2. Arm the Ring security system via security_management
3. Verify all cameras are recording via camera_management
4. Check energy plugs are in night mode via energy_management
5. Disable motion notifications via motion_management
Each action uses a different backend service but is orchestrated through the single MCP server.

### Plex Library Optimization Schedule
For optimal Plex performance, schedule these maintenance tasks periodically:
- Weekly: `plex_library(operation="clean_bundles", library_id="1")` to remove orphaned bundle files
- Monthly: `plex_organization(operation="optimize_database", vacuum=True, reindex=True)` to defragment and optimize the database
- After large additions: `plex_library(operation="empty_trash", library_id="1")` to clear removed items
- Quarterly: `plex_reporting(operation="library_stats")` to review library health metrics
- As needed: `plex_metadata(operation="refresh_all")` to force metadata refresh from agents

### Home Assistant Bridge Configuration
When using Home Assistant as a device hub, configure the HA URL and long-lived access token in config.yaml. The Home Assistant integration exposes entity states for lights, switches, sensors, covers, locks, and climate devices. The home_assistant_management tool allows querying entity states, listing available entities, calling services (like turning on a switch or setting a thermostat), and monitoring Nest Protect status through the HA integration. This provides a bridge between the MCP server and any device connected to Home Assistant.

## Protocol Reference

### Tool Call Format
All MCP tool calls use JSON-RPC 2.0. The request format is:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "lighting_management",
    "arguments": {
      "action": "control",
      "device_id": "lamp_desk",
      "power_state": "on",
      "brightness_percent": 80
    }
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"message\": \"Light turned on with 80% brightness\", \"data\": {\"device_id\": \"lamp_desk\", \"power_state\": \"on\", \"brightness\": 80}}"
      }
    ]
  }
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "Device 'lamp_desk' not found or unreachable"
  }
}
```

## Complete Device Setup Reference

### Tapo Smart Plug Setup
Tapo P115 smart plugs provide energy monitoring in addition to on/off control. To set up a new plug: first ensure the plug is powered on and connected to your WiFi network through the Tapo app. The server discovers the plug automatically when Tapo credentials are configured. Each plug reports real-time power consumption in watts, voltage, current, and cumulative energy in kWh. Plugs can be controlled individually or grouped. The energy_management tool supports named devices which map friendly names to Tapo device IDs. Use energy_management(action="status", device_id="tv_plug") to check current power draw, energy_management(action="consumption", device_id="tv_plug") for historical data, and energy_management(action="control", device_id="tv_plug", power_state="off") to switch devices. The cost calculation feature multiplies consumption by your electricity rate: energy_management(action="cost", device_id="ev_charger", rate_per_kwh=0.30) estimates the cost of running the EV charger.

### Tapo Camera PTZ Control
PTZ (Pan-Tilt-Zoom) cameras support remote movement control through the ptz_management portmanteau tool. The tool supports absolute and relative positioning, speed control, and preset recall. Pan ranges from -180 to +180 degrees, tilt from -90 to +90 degrees, and zoom from 1x to 12x depending on camera model. The prank modes provide entertaining pre-programmed movement sequences: nod (gently nods the camera up and down), shake (rapidly shakes side to side as if saying no), dizzy (continuous slow rotation), and chaos (random movement pattern). These are accessible through the _ptz_prank operations and are intended for entertainment purposes only.

### Camera Stream Health Monitoring
The camera health monitoring system continuously checks all configured cameras for connectivity and stream availability. Each camera is polled every 60 seconds by default. If a camera becomes unreachable, the system logs the event and attempts automatic reconnection up to 3 times with 30-second intervals between attempts. After all reconnection attempts fail, the camera is marked as offline and an alert is generated. The system_management(action="health") call reports the status of all camera connections with individual error messages for failed cameras. The capture_snapshot tool attempts to grab a single frame from the camera stream, useful for quick visual checks without establishing a full streaming session.

### Plex Remote Streaming Optimization
For optimal Plex streaming performance, configure quality profiles based on your network conditions and client capabilities. The plex_quality tool manages profiles for different scenarios: a Remote profile with 4Mbps max bitrate for mobile streaming over cellular, a Local profile with 20Mbps for home network streaming, a 4K profile with 40Mbps for Ultra HD content on capable displays, and a Transcode profile that adjusts quality based on available bandwidth. The plex_performance tool monitors current transcoding activity showing active sessions, transcode reason (bandwidth, codec incompatibility, resolution mismatch), and hardware transcoding utilization. The plex_streaming tool provides per-session controls including quality override and bandwidth throttling to manage network load during peak usage.

### Ring Alarm System Management
The Ring Alarm integration supports multiple modes: disarmed (all sensors inactive), home (perimeter sensors active, interior delayed), and away (all sensors active, immediate alarm). The security_management tool provides mode switching with optional disarming code for security. The system supports multiple entry zones with configurable entry delays. The motion_management tool configures motion detection zones and sensitivity for Ring cameras, with options for people-only mode to reduce false alerts from animals or vehicles. The ring_management tool accesses live streams from Ring cameras with configurable resolution and bitrate settings for bandwidth management. Event history is stored locally with searchable metadata including event type, timestamp, and device ID.

### iKettle Advanced Features
The iKettle smart kettle provides precise temperature control for different beverage types. Temperature presets include: green tea (70-80°C), white tea (75-85°C), oolong tea (85-90°C), black tea (95-100°C), herbal tea (100°C), coffee (92-96°C), and baby formula (40-50°C). The keep_warm function maintains the target temperature for up to 2 hours. The ikettle_management(action="status") call reports current water temperature, heating status, and keep-warm remaining time. The kettle must have sufficient water to operate; the server checks for low water conditions before heating.

### Weather Alert Configuration
Weather alerts are sourced from the National Weather Service API and configured OpenWeatherMap alerts. Alert types include severe thunderstorm warnings, tornado warnings, flash flood warnings, winter storm warnings, extreme temperature warnings, and high wind warnings. The weather_management(action="alerts") call returns active alerts with severity, event type, onset time, expiration time, and detailed description. Alert notifications can be integrated with the automation system to trigger actions like closing windows, turning on lights, or sending notifications when severe weather is detected in the area.

### Automation Rule Syntax
Automation rules use a trigger-condition-action syntax. Triggers include: time (absolute HH:MM or relative to sunrise/sunset), device_state (specific device reports a state change), motion (motion detected by a specific camera or sensor), security (alarm armed or disarmed), weather (specific weather alert received), and schedule (recurring cron-like timing). Conditions include: time_of_day (check if current time is within a range), home_away (check if anyone is home based on presence sensors), device_is (check if a specific device is in a particular state), and weather_is (check current weather condition). Actions include: device_command (send any command to any device), notification (send push notification or webhook), automation (enable or disable another automation), and script (execute a predefined sequence of commands). Automation rules are evaluated by the polling_manager background task every 30 seconds.

### Built-in Emergency Protocols
The coordinate_emergency_response tool orchestrates a coordinated response across multiple device types when an emergency is detected. The protocol includes: verify alarm via multiple sensors (reduces false positives), activate all interior and exterior lights to maximum brightness, unlock designated emergency exit routes, capture snapshots from all cameras for evidence recording, send emergency notifications to configured contacts, and log all actions for post-event review. The assess_home_safety tool performs a comprehensive safety scan checking: all door/window sensor status, smoke/CO detector health, camera connectivity, system battery levels, and network connectivity for all devices.

### Multi-Device Scene Configuration
Scenes are predefined device configurations that can be activated with a single command. A typical "Movie Night" scene might: dim living room lights to 20% with warm color temperature, close motorized blinds, turn off kitchen and hallway lights, set the thermostat to 22°C, and enable do-not-disturb mode on the doorbell. A "Good Morning" scene might: gradually brighten bedroom lights from 0-80% over 15 minutes, start the kettle boiling, open motorized blinds, turn off security system (home mode), and provide a weather briefing. Scenes are created using the automation_management tool and can be triggered manually or on a schedule.

### Energy Usage Analytics
The energy_management tool provides comprehensive energy analytics including real-time power consumption for individual devices, daily/weekly/monthly consumption totals, cost projections based on current usage patterns, peak usage time identification, and device-level comparison charts. Historical data is retained in the SQLite database with configurable retention periods. Data can be exported for external analysis through the analytics_management tool. The energy data integrates with the weather system to correlate heating/cooling energy usage with outdoor temperature.

### Plex Library Metadata Management
The Plex metadata system supports comprehensive metadata operations. The plex_metadata tool provides operations for refreshing metadata from configured agents (The Movie Database, TheTVDB, Freebase), updating specific fields like title, year, summary, rating, and tags, fixing incorrect media matches by searching for alternative matches, organizing library content with configurable naming and grouping patterns, and analyzing library structure for issues. The plex_organization tool provides deeper library maintenance including analyzing library structure for issues, cleaning up orphaned bundle files, optimizing the SQLite database with VACUUM and REINDEX, and organizing content by folder structure. Regular metadata maintenance ensures accurate recommendations, proper sorting, and complete cast and crew information.

### Cross-Server Fleet Integration
The devices-mcp server participates in the fleet MCP ecosystem through the MCP_BRIDGE_URLS configuration option. When configured with comma-separated URLs of other fleet MCP servers (like meta-mcp, docker-mcp, or documentation-mcp), the server creates proxy providers that expose those servers' tools through the same FastMCP instance. This enables cross-server workflows like \"arm the security system and back up the Plex database\" from a single tool call. The web dashboard's Apps Hub automatically discovers other active MCP webapps on the local network and displays them as interactive cards for fleet-wide management.

## Complete Command Reference

### lighting_management Control Parameter Combinations
The lighting_management tool accepts various parameter combinations for different control scenarios. To turn a light on or off, provide device_id and power_state (on/off/toggle). To set brightness, add brightness_percent (0-100). To set color temperature, add color_temp (2500-6500 Kelvin) which produces warm to cool white light. To set RGB color, add an rgb array [red, green, blue] with values 0-255 each. To use the Hue/Saturation model, add hue (0-360) and saturation (0-100). To apply a dynamic effect, add effect (rainbow, sunset, ocean, fire, strobe, police, color_cycle, candle, twinkle) and animation_speed (1-100). Multiple parameters can be combined in a single call.

### energy_management Historical Data Resolution
Historical energy consumption data is stored at different resolutions: real-time (every 5 seconds, retained for 1 hour), high-resolution (every minute, retained for 24 hours), medium-resolution (every 15 minutes, retained for 30 days), and low-resolution (every hour, retained for 1 year). The consumption action automatically selects the appropriate resolution based on the requested time range. Short ranges (hours) return high-resolution data. Medium ranges (days) return medium-resolution. Long ranges (months) return low-resolution. Historical data can be queried with optional from_date and to_date parameters.

### camera_management Stream URL Formats
Camera stream URLs follow different formats depending on the camera type. Tapo cameras use RTSP URLs like rtsp://username:password@camera_ip:554/stream1 for the main stream and stream2 for the sub-stream. Ring cameras use HLS streaming URLs obtained from the Ring API. Generic RTSP cameras use the standard ONVIF profile URLs. The stream URL is returned by the info and status actions and can be used in external media players like VLC for viewing. The server does not transcode streams and passes through the original camera encoding.

### plex_streaming Client Control Details
The plex_streaming tool provides remote control of Plex clients. Each client is identified by a unique client_id which can be discovered using the list_sessions or list_clients operations. Volume control uses a 0-100 scale where 0 is muted and 100 is maximum volume. Seek operations accept position in milliseconds from the start of the media. Quality overrides accept preset names like Original, 1080p 20Mbps, 720p 4Mbps, 480p 1.5Mbps, or custom bitrate values in kbps. Audio and subtitle stream selection uses the stream index from the media's stream list. Multiple clients can be controlled simultaneously through separate tool calls.

### plex_rag Search Capabilities
The Plex RAG (Retrieval-Augmented Generation) system indexes media metadata for natural language search. The metadata index includes titles, plots, summaries, genre tags, actor names, director names, writer names, studio names, content ratings, and collection memberships. The subtitle index includes dialogue text from embedded subtitle tracks. The sync_metadata operation indexes all current library metadata into the vector store. The sync_subtitles operation downloads and indexes subtitle tracks. The semantic_search operation accepts natural language queries like "find movies where someone travels through time" and returns the most relevant media items. The search results include the media title, match score, and matched metadata fields.

### plex_integration Regional Content Discovery
The Plex integration provides regional content discovery for European and specifically Austrian/Vienna markets. The vienna_recommendations operation returns curated movie and TV show recommendations from Vienna-based cultural institutions and publications. The european_content operation filters content to European productions only, excluding Hollywood and other non-European media. The anime_season_info operation returns seasonal anime recommendations by year and season (winter, spring, summer, fall). These integrations use external APIs and web scraping to gather recommendations that complement the Plex library's native metadata.

### security_management Alarm Arm Modes
The security_management arm action supports two modes: home (stays) and away. Home mode arms perimeter sensors (doors, windows) while allowing interior movement detection to have a longer entry delay. Away mode arms all sensors with immediate alarm response. The disarm action requires the alarm code for security. The history action returns chronological events with type, location, timestamp, and status for each event. The alerts action returns currently active alarm alerts sorted by severity.

### audio_management Device Control
The audio_management tool controls audio devices including smart speakers, audio systems, and multi-room audio setups. Supported operations include listing available audio devices, setting volume, muting/unmuting, selecting input sources, and grouping devices for synchronized multi-room playback. Device compatibility depends on the specific audio hardware and protocol support.

### dymo_management Label Formatting
The dymo_management tool prints labels on Dymo LabelWriter printers. The text parameter supports automatic font sizing based on label width. Longer text is automatically truncated or font-reduced to fit the label width. Special characters and Unicode are supported within the font's character set. The width parameter accepts standard Dymo label widths: 6mm (address labels), 9mm, 12mm (shipping labels), 19mm, and 24mm (multi-purpose labels). The tool automatically selects the appropriate label template based on the width.

### grafana_management Dashboard Integration
The grafana_management tool connects to Grafana dashboards for visualization of metrics from various sources. The dashboards action lists available Grafana dashboards. Individual dashboard actions can open specific dashboards in the browser or return dashboard URLs for embedding. The integration requires Grafana URL and API key configuration.
