# schip-mcp-devices — MCP Server Capabilities

## Server Overview

Devices MCP is a universal home IoT and surveillance platform that consolidates smart home device management, media server integration, and AI-powered computer vision into a single MCP server. It provides unified control across camera systems (Tapo, Ring, RTSP), smart lighting (Tapo, Philips Hue), energy monitoring (Tapo P115 plugs, Shelly), security systems (Ring Alarm, Nest Protect), weather stations, kitchen appliances (iKettle, smart appliances), PTZ camera controls, motion detection, and Plex media server management. The server operates as a FastMCP service with stdio, HTTP, and SSE transport modes, exposing approximately 280 tools through portmanteau patterns for efficient discovery and reduced context consumption.

The server is organized into domain-specific portmanteau tools (camera_management, lighting_management, energy_management, security_management, etc.) that each expose an action-based interface. This means a single tool handles all operations within a domain — for example, camera_management handles list, add, remove, connect, disconnect, info, status, set_active, and manage_groups operations through a single entry point. The server also includes legacy individual tools for backward compatibility, Plex media server integration with full library management, and Ring device operations.

Configuration is handled through a config.yaml file, environment variables, and a Settings UI in the webapp. The server supports dynamic service discovery, health monitoring, and automated alerting.

The web dashboard provides a rich interface for device management with real-time camera feeds, lighting controls, energy usage graphs, security system status, weather information, and system health monitoring. The dashboard is built as a React SPA with TailwindCSS styling, featuring a retractable sidebar, fixed topbar with breadcrumbs and search, toast notifications for alerts, a global logger modal for MCP JSON-RPC logs, and a help modal with context-aware documentation. The dashboard automatically discovers camera streams and shows live thumbnails when available.

The Tauri desktop app wraps the full stack into a single NSIS installer. It embeds the PyInstaller-frozen Python backend and the built React frontend into a native Windows application with system tray support, automatic startup, and MCP client registration for Cursor and Claude Desktop. The installer is built with pre-install and pre-uninstall hooks that kill both the UI and backend processes to prevent file-lock issues during updates.

## Domain Architecture

The server's tool surface is organized into the following domains, each with its own portmanteau tool and supporting module:

**Camera Domain** — Handles IP cameras, USB cameras, RTSP streams, and cloud cameras. Supports Tapo/Kasa cameras through the Tapo cloud API, Ring cameras and doorbells through the Ring API, and generic RTSP/ONVIF cameras. Features include snapshot capture, continuous recording, motion-triggered recording, PTZ control, privacy modes, and camera grouping. The camera_manager module handles connection pooling, stream health monitoring, and automatic reconnection on network interruptions.

**Lighting Domain** — Controls smart lights from multiple ecosystems through a unified interface. Supports Tapo smart bulbs and plugs with color, brightness, and effects control. Philips Hue integration through the local Hue bridge API for more reliable and faster response times. Features include scene recall, dynamic animations (rainbow, sunset, ocean, fire, strobe, police, color cycle, candle, twinkle), scheduling, and group control.

**Energy Domain** — Monitors and controls smart plugs and energy-consuming devices. Supports Tapo P115 energy monitoring plugs for real-time power consumption, voltage, and current readings. Historical consumption tracking with configurable intervals. Cost calculation with configurable electricity rates. Supports devices like the Living Room TV P115, Kitchen Coffee Maker P115, Bedroom Lamp P115, Garage EV Charger P115, and Office Computer P115.

**Security Domain** — Manages alarm systems, motion sensors, and door/window sensors. Supports Ring Alarm with home, away, and disarmed modes. Nest Protect smoke and CO alarm monitoring with health checks and test capabilities. Motion detection configuration with sensitivity zones, schedules, and notification rules. Emergency response coordination that can trigger cameras, lighting, and alerts simultaneously.

**Weather Domain** — Provides local weather data from personal weather stations and online APIs. Current conditions including temperature, humidity, wind speed and direction, barometric pressure, UV index, and precipitation. Historical data for trend analysis. Severe weather alerts with automatic notification. Supports multiple stations for comparative readings.

**Plex Domain** — Full Plex Media Server management with library CRUD, scanning, optimization, metadata management, playlist and collection management, streaming control, user management, quality profiles, transcoding settings, bandwidth monitoring, and reporting. The Plex integration also includes RAG-powered semantic search across metadata and subtitles, external metadata enrichment from Wikipedia and TMDB, and Vienna-specific regional content recommendations.

**Ring Domain** — Ring device management including doorbells, cameras, and alarm systems. Features include live streaming, event history, motion detection, two-way audio, chime triggering, and alarm arm/disarm with configurable modes. Authentication uses OAuth2 with automatic token refresh.

**Automation Domain** — Create, manage, and trigger automations that span multiple device types. Supports time-based triggers (schedules, sunrise/sunset), event-based triggers (motion detected, door opened, camera motion), and device-state triggers. Actions can include lighting control, camera actions, security system changes, notifications, and webhooks.

**AI Vision Domain** — On-device computer vision using local processing. Supports scene analysis identifying objects, people, vehicles, and animals. Activity recognition for running, walking, fighting, and loitering detection. Scene classification for indoor/outdoor, day/night, and environment type. Object detection with configurable confidence thresholds. All processing is done locally without cloud dependencies, ensuring privacy.

**Kitchen Domain** — Smart kitchen appliance management. Supports iKettle with boil, keep warm, and temperature monitoring. Generic smart appliance control through Home Assistant bridge. Energy usage tracking per appliance.

**Configuration System** — The configuration management tool allows per-device settings, privacy controls, LED indicators, motion detection parameters, and privacy mode activation. Configuration is persisted across restarts and can be exported/imported. The config system supports device-specific override of global defaults.

## Tools

### Camera Management (camera_management)
Portmanteau tool for all camera operations:
- **action: "list"** — List all cameras with status info
- **action: "add"** — Add a new camera (rtsp_url, name, type, credentials)
- **action: "remove"** — Remove a camera (camera_id required)
- **action: "connect"** — Connect to a camera stream (camera_id required)
- **action: "disconnect"** — Disconnect from a camera (camera_id required)
- **action: "info"** — Detailed camera information (camera_id required)
- **action: "status"** — Camera current status (camera_id required)
- **action: "set_active"** — Set camera as active (camera_id required)
- **action: "manage_groups"** — Organize cameras into groups
**Returns:** Dict with success, message, and domain-specific data.

### Lighting Management (lighting_management)
Portmanteau for smart lighting across Tapo and Philips Hue:
- **action: "list"** — List all smart lights across all protocols
- **action: "status"** — Get light status (device_id required)
- **action: "control"** — Control light (device_id + power_state/brightness/hue/saturation/rgb/effect)
- **action: "effects"** — List available light effects and animations
**Parameters:** device_id (str), power_state ("on"/"off"/"toggle"), brightness_percent (0-100), hue (0-360), saturation (0-100), rgb (list of 3 ints), effect (str), animation_speed (1-100).

### Energy Management (energy_management)
Smart plug and energy monitoring:
- **action: "status"** — Get energy status for a device (device_id required)
- **action: "control"** — Turn device on/off (device_id + power_state required)
- **action: "consumption"** — Get energy consumption data (device_id required)
- **action: "cost"** — Calculate energy cost (device_id, rate_per_kwh optional)
**Returns:** Power consumption in watts, historical usage, cost estimates.

### Security Management (security_management)
Home security orchestration across Ring Alarm:
- **action: "status"** — Get security system status
- **action: "arm"** — Arm security system (mode: "home"/"away")
- **action: "disarm"** — Disarm security system (code required)
- **action: "history"** — Get security event history (limit, since)
- **action: "alerts"** — List recent security alerts

### AI Analysis (ai_analysis)
Computer vision and scene understanding:
- **action: "analyze_scene"** — Comprehensive scene analysis (camera_id required)
- **action: "detect_objects"** — Object detection (camera_id required)
- **action: "analyze_activity"** — Activity recognition (camera_id required)
- **action: "classify_scene"** — Scene classification (camera_id required)
**Parameters:** confidence_threshold (0.0-1.0, default 0.7), analysis_type ("comprehensive"/"quick"/"detailed").

### Weather Management (weather_management)
Local weather data:
- **action: "current"** — Current weather conditions
- **action: "historical"** — Historical weather data (date range)
- **action: "stations"** — List weather stations
- **action: "alerts"** — Weather alerts for the area
- **action: "health"** — Weather service health
- **action: "analyze"** — Weather trend analysis

### System Management (system_management)
Server and device system operations:
- **action: "info"** — System information
- **action: "status"** — Overall system health
- **action: "health"** — Detailed health check
- **action: "initialize"** — Initialize services
- **action: "reboot"** — Reboot system
- **action: "logs"** — Retrieve system logs

### Configuration Management (configuration_management)
- **action: "device_settings"** — Device configuration
- **action: "privacy_settings"** — Privacy and data handling
- **action: "led_control"** — LED indicator settings
- **action: "motion_detection"** — Motion detection options
- **action: "privacy_mode"** — Privacy mode toggle

### Plex Media Server Tools
Full Plex media server management:
- **plex_library** — Library CRUD, scan, optimize, analyze, trash, bundles
- **plex_media** — Browse, search, details, recent, update metadata
- **plex_search** — Text search, advanced filters, suggest, saved searches
- **plex_playlist** — List, create, update, delete, add/remove items, analytics
- **plex_collections** — List, get, create, update, delete, add/remove items
- **plex_streaming** — Sessions, clients, play, pause, seek, volume, quality
- **plex_server** — Status, info, health, maintenance, restart, update
- **plex_user** — CRUD users, permissions, password management
- **plex_performance** — Transcode settings, bandwidth, profiles, throttling
- **plex_metadata** — Refresh, update, fix match, organize
- **plex_organization** — Organize, analyze, clean bundles, optimize DB
- **plex_quality** — Quality profiles CRUD and default management
- **plex_reporting** — Library stats, usage, content, export
- **plex_audio_mgr** — Volume, mute, stream selection, handover
- **plex_ffmpeg_mgr** — Probe media, sync audio, extract subtitles
- **plex_rag** — Semantic search, metadata sync, subtitle indexing
- **plex_integration** — Vienna recommendations, European content, anime seasons
- **plex_media_enrichment** — Wikipedia, TMDB, TVDB metadata enrichment
- **plex_natural_assistant** — Single-turn natural language Plex help
- **agentic_plex_workflow** — Multi-step Plex workflows via sampling

### Ring Device Management (ring_management)
- **action: "devices"** — List all Ring devices
- **action: "device"** — Get specific device details
- **action: "events"** — Get device events
- **action: "stream"** — Get live stream URL
- **action: "arm"** — Arm/disarm security
- **action: "chime"** — Trigger doorbell chime
- **action: "system"** — Overall system status

### Other Portmanteau Tools
- **alerts_management** — Create, list, acknowledge, clear alerts
- **analytics_management** — Dashboard metrics, trends, reporting
- **appliance_monitor_management** — Monitor smart appliance status and control
- **audio_management** — Audio device management and streaming
- **automation_management** — Create, enable, disable, list automations
- **dymo_management** — Label printer (6mm/9mm/12mm/19mm/24mm)
- **grafana_management** — Grafana dashboard management
- **home_assistant_management** — Home Assistant entities, status, services
- **ikettle_management** — iKettle boil, keep warm, temperature
- **kitchen_management** — Smart kitchen appliance list, control, status
- **media_management** — Media device routing and control
- **medical_management** — Medical device monitoring
- **messages_management** — Notification and message delivery
- **motion_management** — Motion detection status, events, subscribe
- **ptz_management** — PTZ camera pan/tilt/zoom with prank modes
- **robotics_management** — Robot device management
- **shelly_management** — Shelly smart relay control
- **tapo_control** — Direct Tapo device operations
- **thermal_management** — Thermal camera/sensor operations

### Legacy Individual Tools
- health_check, get_cameras_status, get_recent_events, capture_snapshot
- get_metrics, list_cameras, test_connection, assess_home_safety
- coordinate_emergency_response, configure_auth, get_devices, get_device
- get_device_events, get_live_stream_url, set_arm_status, trigger_doorbell_chime
- get_system_status, list_connected_servers, connect_server, call_namespaced_tool

## Configuration

The server reads configuration from multiple sources in priority order: CLI arguments > environment variables > config.yaml > defaults. The config file path defaults to %USERPROFILE%\.config\devices-mcp\config.yaml with a template at config.example.yaml.

**Key Environment Variables:**
- TAPO_EMAIL, TAPO_PASSWORD — Tapo cloud credentials
- TAPO_MCP_LAZY_INIT — Skip hardware init on startup (default: false)
- RING_ACCESS_TOKEN, RING_REFRESH_TOKEN — Ring API tokens
- RING_2FA_TOKEN — Ring two-factor token
- NEST_PROTECT_ACCESS_TOKEN — Nest Protect credentials
- PLEX_URL, PLEX_TOKEN — Plex server connection
- PLEX_USERNAME, PLEX_PASSWORD — Plex authentication
- HA_URL, HA_TOKEN — Home Assistant connection
- GRAFANA_URL, GRAFANA_API_KEY — Grafana integration
- LOG_LEVEL — Logging verbosity (default: WARNING)
- PYTHONPATH — Must include src/ directory

**Config File (config.yaml):**
```yaml
tapo:
  email: "user@example.com"
  password: "secret"
nest_protect:
  access_token: "token"
ring:
  access_token: "token"
  refresh_token: "token"
plex:
  url: "http://localhost:32400"
  token: "token"
home_assistant:
  url: "http://localhost:8123"
  token: "token"
llm:
  providers:
    - type: ollama
      url: http://localhost:11434
    - type: lm_studio
      url: http://localhost:1234
logging:
  level: INFO
  file: "%USERPROFILE%\\.local\\share\\devices-mcp\\devices-mcp.log"
```

## Data Sources

- **Tapo Cloud API** — Camera streams, smart plugs, smart lights, PTZ control
- **Ring API** — Doorbells, cameras, alarm system, motion events
- **Nest Protect API** — Smoke/CO alarm status and health
- **Philips Hue Bridge** — Local Hue lighting control
- **Plex Media Server API** — Library, playlists, streaming, metadata
- **Home Assistant API** — Entity states, service calls, automations
- **Shelly API** — Smart relay and sensor data
- **OpenWeatherMap** — Local weather and forecasts
- **iKettle API** — Kettle temperature and boil control
- **Grafana API** — Dashboard and metric visualization
- **Dymo LabelWriter** — Label printing via local USB
- **USB/RTSP Cameras** — Direct camera feed access
- **Local config files** — Persistent settings and automation rules
- **SQLite database** — Event history, analytics cache, device registry

## Prompts

The server registers FastMCP 3.2 prompts for common workflows:
- **device_setup** — Guided setup for new devices
- **troubleshooting** — Common issue diagnosis
- **security_check** — Security system walkthrough

## Resources

Dynamic resources are exposed via MCP resource protocol:
- **device://cameras** — Live camera list and status
- **device://lights** — Smart light inventory and states
- **device://energy** — Energy consumption summaries
- **device://security** — Security system snapshot
- **device://weather** — Current weather conditions
- **logs://server** — Recent server log entries

## Deployment Modes

The server supports three deployment modes depending on use case:

**MCP Stdio Mode** — Fastest startup, used for Claude Desktop and Cursor integration. The server communicates over stdin/stdout with JSON-RPC messages. All tools are available including camera, lighting, energy, security, Plex, and Ring operations.

**MCP HTTP/SSE Mode** — Used for remote connections and web dashboard integration. The server binds to a configurable port (default 8000) and accepts MCP protocol over HTTP with SSE for server-sent events. Requires MCP_TRANSPORT=http or --http flag.

**Full Webapp Mode** — Runs both the FastAPI backend (port 10717) and React frontend (port 10716) with Vite HMR. The webapp provides a dashboard, device management UI, settings panel, LLM chat with local AI, and logging interface. The start.ps1 script handles both services and auto-opens the browser.

## Security Architecture

The server implements a layered security model. Device credentials are stored in the local config.yaml file and are never transmitted over the network. Camera streams use RTSP authentication. Ring API uses OAuth2 tokens with refresh token rotation. The server does not expose ports to the internet by default — it binds to 127.0.0.1. Privacy mode can disable all cameras with a single command. Motion detection events are processed locally and never sent to external services unless explicitly configured through the webhook system.

The config file supports multiple levels of access control. The `device_settings` action in configuration_management allows granular control over which features are enabled per device. LED controls can indicate recording status as a visual privacy indicator. Privacy mode disables both video streaming and audio capture on supported cameras.

## Performance Characteristics

The server is designed for local network operation with typical response times as follows:
- Camera management: 50-500ms (local cameras), 500-2000ms (cloud-dependent like Ring)
- Lighting control: 100-800ms depending on protocol (Tapo cloud vs Hue local)
- Energy monitoring: 200-1000ms for real-time data, 1-5s for historical queries
- Plex operations: 100-2000ms depending on library size
- AI analysis: 2-10s for comprehensive scene analysis
- Security system: 200-1000ms for arm/disarm operations
- Weather queries: 500-3000ms (external API call)

The server uses asyncio throughout for concurrent operations. Multiple tools can be called simultaneously without blocking. The polling_manager handles periodic updates for cameras and sensors in background tasks.

## Extensibility

The server architecture supports adding new device integrations through the portmanteau pattern. To add a new device type:
1. Create a Python module in tools/portmanteau/ following the existing pattern
2. Register the tool with @mcp.tool() using an action-based interface
3. Add configuration defaults to config/ models
4. The tool is automatically discoverable through MCP's tools/list

Current integration types supported:
- Cloud API devices (Tapo, Ring, Nest)
- Local network devices (Philips Hue, Shelly, weather stations)
- USB devices (Dymo printers, SDR receivers, thermal cameras)
- Standard protocol devices (RTSP cameras, ONVIF)
- Software services (Plex, Home Assistant, Grafana)
- Bridge integrations (MCP_BRIDGE_URLS for cross-server connectivity)

## Advanced Tool Details

### Energy Management Detailed Usage
The energy_management portmanteau tool provides comprehensive power monitoring across all Tapo P115 smart plugs. Each plug reports real-time metrics including current power consumption in watts, voltage in volts, current in amperes, and cumulative energy usage in kilowatt-hours. Historical consumption data is stored locally in the SQLite database with configurable retention periods. The cost calculation feature accepts a per-kWh rate and computes estimated costs for any time period. The tool supports named devices like Living Room TV, Kitchen Coffee Maker, Bedroom Lamp, Garage EV Charger, and Office Computer, each identified by its unique device_id from the Tapo cloud.

### Lighting Management Detailed Actions
The lighting_management tool supports multiple lighting ecosystems transparently. For Tapo smart bulbs, it uses the Tapo cloud API to control power state, brightness (0-100%), color temperature (2500K-6500K), and full RGB color through hue and saturation values. For Philips Hue bulbs, it communicates directly with the Hue bridge on the local network for faster response times and offline operation. Dynamic effects include rainbow, sunset, ocean, fire, strobe, police siren, color cycle, candle flicker, twinkle, and custom animations with configurable speed (1-100). Groups can be created to control multiple lights simultaneously.

### Plex Media Advanced Operations
The Plex integration goes beyond basic library management with advanced features. The RAG (Retrieval-Augmented Generation) system indexes Plex metadata including titles, plots, genres, actors, and directors into a local vector store for natural language semantic search. Subtitle content can also be indexed for dialogue-level search. External metadata enrichment pulls Wikipedia summaries, TMDB ratings, TVDB episode data, and OMDb details to augment the Plex data. The streaming control supports multi-client playback management including volume adjustment, audio stream switching, subtitle selection, seek operations, and quality preset changes. The reporting system generates library statistics, usage reports, content analysis, and exports to CSV, JSON, or HTML formats.

### AI Analysis Implementation
The ai_analysis tool uses OpenCV and locally hosted vision models for all processing. Scene analysis detects and classifies objects, identifies activities, determines scene type (indoor, outdoor, day, night, urban, natural), and generates contextual descriptions. Object detection supports common classes including person, vehicle, animal, package, and custom trained objects. Activity recognition identifies running, walking, fighting, loitering, and unusual behavior patterns. The analysis_type parameter controls processing depth: "quick" returns basic classifications, "comprehensive" includes object details and recommendations, and "detailed" returns exhaustive metadata including confidence scores, bounding boxes, and tracking IDs.

### Weather Data Processing
The weather_management tool aggregates data from multiple sources. Personal weather stations connected via USB or WiFi provide hyperlocal readings. The OpenWeatherMap API supplements with forecast data, severe weather alerts, and historical records. The stations action enumerates all configured weather sources with their current status and data freshness. The analyze action performs trend analysis over configurable time windows, detecting patterns like temperature anomalies, pressure drops preceding storms, and wind gust patterns. Weather alerts are aggregated from National Weather Service feeds and local station threshold crossings.

### Home Automation Engine
The automation system supports event-condition-action rules that span device domains. Triggers include scheduled times (absolute or relative to sunrise/sunset), device state changes, motion events, security system state changes, and sensor threshold crossings. Conditions can check time of day, home/away status, weather conditions, and device states before firing. Actions support any combination of device controls: turn lights on/off, arm/disarm security, capture camera snapshots, send notifications, change thermostat setpoints, and trigger webhooks. Automations are stored in the SQLite database and evaluated by the polling_manager background task.

### System Diagnostics and Monitoring
The system_management tool provides comprehensive server diagnostics. The health action checks all configured device integrations and reports per-service status with error messages for failed connections. The info action returns system metadata including server version, uptime, connected device counts, and Python version. The logs action retrieves recent log entries with level filtering and supports querying by time range. The initialize action performs a full service discovery and health check, reconnecting to all configured devices and services. The reboot action performs a graceful restart of the server process.

## Fleet Integration

The server participates in the fleet MCP ecosystem through the MCP_BRIDGE_URLS mechanism. When configured with comma-separated URLs of other MCP servers, it creates proxy providers that expose those servers' tools through the same FastMCP instance. This allows cross-server workflows like "arm security system and turn on all lights" from a single tool call. The server also auto-registers with the meta-mcp fleet registry for discovery by other fleet tools. The web dashboard includes an Apps Hub that scans for other active MCP webapps and populates cards for fleet-wide discovery.

## Logging and Observability

The server uses Python's logging module with rotating file handlers. Log files are stored at %USERPROFILE%\.local\share\devices-mcp\devices-mcp.log by default. The log level is configurable via the LOG_LEVEL environment variable or config.yaml setting. Each log entry includes timestamp, module name, log level, filename, line number, and message. The web dashboard includes a Logs page with real-time log streaming, level filtering, and search. Activity is also recorded in the SQLite database for historical query and export. The logs_query, logs_stats, logs_export, and logs_clear tools provide programmatic access to the log database.

## Integration Points

- **FastMCP 3.2+** — stdio, HTTP, SSE transports
- **MCP Bridge Proxy** — Connect to other fleet MCP servers via MCP_BRIDGE_URLS
- **Web Dashboard** — FastAPI backend :10717 + React SPA frontend :10716
- **Tauri Desktop App** — Native NSIS installer with embedded PyInstaller backend
- **Fleet Discovery** — Auto-register with meta-mcp fleet registry
