# Home Security MCP Platform

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

## Quick Start

```powershell
git clone https://github.com/sandraschi/devices-mcp
cd devices-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

**Web dashboard (web-sota):** Vite frontend on **10716**, FastAPI backend on **10717**, USB camera helper on **10715**. Open `http://localhost:10717/app/` (production) or `http://localhost:10716` (Vite dev). **Desktop (Tauri):** `native\` — `npm run dev` or `native\build.ps1` for a Windows installer. Legacy single-port `devices_mcp.web` on 7777 is still available via `start_dashboard.ps1`.

### Manual Setup

If you don't have `just` installed:

##  **DUAL-NATURE ARCHITECTURE**

This repository serves **two complementary roles** in the smart home ecosystem:

### ** ROLE 1: Individual MCP Servers**
Standalone MCP servers for specific device types, each providing specialized functionality:
- **Devices MCP**: TP-Link camera control with PTZ and streaming
- **USB Webcam MCP**: Direct webcam capture and management
- **Ring MCP**: Doorbell integration with WebRTC streaming
- **Nest Protect MCP**: Smoke/CO monitoring via Home Assistant
- **Lighting MCP**: Philips Hue control with scenes, groups, and HomeAware motion detection
- **Energy MCP**: Smart plug monitoring and appliance control
- **Weather MCP**: Environmental sensors and forecasts

### ** ROLE 2: Unified Dashboard Platform**
Complete orchestration platform that unifies all MCP servers into a single interface:
- **Single Dashboard**: Monitor and control all devices from one place
- **Cross-System Integration**: Event correlation and unified alerts
- **Real-time Monitoring**: Live status updates and health checks with circuit breaker protection
- **HomeAware Motion Detection**: Zigbee mesh signal strength monitoring (Bridge Pro)
- **Robust Error Handling**: Timeouts, graceful degradation, and crash prevention
- **AI Integration**: Claude Desktop MCP tools for natural language control
- **Multi-Protocol Support**: ONVIF, WebRTC, RTSP, Zigbee, and more

**Status: Beta - Active Development** | **Version: 1.20.0**
 
  **CURSOR IDE MCP INTEGRATION**: Full compatibility with Cursor IDE for AI-assisted smart home control.
  **ROBOTICS INTEGRATION**: Dreame D20 Pro (Cloud) and Yahboom ROS 2 (Mock) functional in dashboard.
  **FLEET EXPANSION**: Multi-camera support now standard (Kitchen + Living Room).
  **ROBUST ERROR HANDLING**: Circuit breakers, timeouts, and graceful degradation prevent system hangs/crashes
 **USB CAMERA SERVER**: Dedicated local capture server integrated into global startup flow on port 10715.

> ** REPOSITORY STRUCTURE FIXED**: Refactored to separate MCP server (`src/devices_mcp/`) from web dashboard (`web-sota/`). All .exe files properly organized in `integrations/` folder.
>
> **See: [EXE_FILES_ANALYSIS.md](EXE_FILES_ANALYSIS.md)** for detailed breakdown of all 50+ critical executables.
>
> ** Beta Status Notice**: This project is in active beta development. Features are working but may have bugs, APIs may change between versions, and some integrations are experimental. Not recommended for critical production use. Active development - contributions welcome.

##  **WHEN TO USE EACH ROLE**

### ** Use Individual MCP Servers When:**
- You need **specialized control** for specific device types
- You want **lightweight, focused functionality** for one system
- You're building **custom integrations** or automation scripts
- You need **direct API access** to device-specific features
- You're developing **device drivers** or extending functionality

### ** Use Unified Dashboard When:**
- You want **complete home automation** across multiple systems
- You need **single interface** to monitor and control everything
- You want **AI-powered control** through Claude Desktop natural language
- You need **cross-system automation** and event correlation
- You want **comprehensive monitoring** with health dashboards and alerts
- You need **remote access** and unified security monitoring

** Pro Tip**: Most users will want the **unified dashboard** for complete smart home control, while developers may use individual MCP servers for specialized integrations.

##  **MCP SERVER CONFIGURATION & AUTHENTICATION**

### **Configuration Sources (Hierarchical Priority)**

The MCP server loads IP addresses, usernames, passwords, and authentication credentials from multiple sources:

#### **1. Primary: YAML Configuration Files**
**Location**: `config.yaml` (highest priority)
**Search Order**:
- `/app/config.yaml` (Docker container)
- `~/.config/devices-mcp/config.yaml` (user home directory)
- Repository root `config.yaml`
- Current directory

#### **2. Secondary: Environment Variables**
**Fallback when config file missing**:
```bash
# Tapo Plugs
TAPO_ACCOUNT_EMAIL=your_email@example.com
TAPO_ACCOUNT_PASSWORD=your_password
TAPO_P115_HOSTS=192.168.1.120,192.168.1.121

# MCP Control
TAPO_MCP_SKIP_HARDWARE_INIT=true
TAPO_MCP_LAZY_INIT=true
```

#### **3. Tertiary: Token/Cache Files**
**OAuth persistence**:
- `ring_token.cache` - Ring OAuth tokens
- `nest_token.cache` - Nest OAuth tokens

### **Current Authentication Configuration**

#### **Cameras** (4 configured)
```yaml
cameras:
  tapo_kitchen:
    type: onvif
    host: 192.168.0.164
    username: sandraschi
    password: Sec1060ta
    rtsp_port: 554
    onvif_port: 2020

  tapo_living_room:
    type: onvif
    host: 192.168.0.206
    username: sandraschi
    password: Sec1000living
    rtsp_port: 554
    onvif_port: 2020

  usb_camera_1:
    type: microscope
    device_id: 0

  usb_camera_2:
    type: webcam
    device_id: 1
```

#### **Energy Devices** (3 Tapo P115 plugs)
```yaml
energy:
  tapo_p115:
    account:
      email: sandraschipal@hotmail.com
      password: Sec1060ta#
    devices:
      - host: 192.168.0.17
        device_id: tapo_p115_aircon
        name: Aircon
      - host: 192.168.0.137
        device_id: tapo_p115_kitchen
        name: Kitchen Zojirushi
      - host: 192.168.0.38
        device_id: tapo_p115_server
        name: Server
```

#### **Lighting Systems**
```yaml
lighting:
  philips_hue:
    bridge_ip: 192.168.0.83
    username: J1A3OQ1OMzJDtidSNQWWGmCBuAxZC3lxEjT9qnVc
    # HomeAware motion detection available with Bridge Pro (BSB002)
    # Automatically enabled when Bridge Pro is detected

  tapo_lighting:
    account:
      email: sandraschipal@hotmail.com
      password: Sec1060ta#
    devices:
      - host: 192.168.0.174
        device_id: tapo_l900_lightstrip
        name: Lightstrip L900
```

#### **External Services**
```yaml
ring:
  enabled: true
  email: sandraschipal@hotmail.com
  password: Sec1000ri#
  token_file: ring_token.cache

netatmo:
  enabled: true
  client_id: 6939e5b98080806f1c003668
  client_secret: IyWYPAE9cq28N6HQNHWp3XDdbz
  refresh_token: 5ca3ae420ec7040a008b57dd|a289c1f0899232016582aa5cf52940f9

security_integrations:
  homeassistant:
    enabled: true
    url: http://localhost:8123
    access_token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### **Authentication Methods by Service**

| Service | Auth Method | Credentials From | Status |
|---------|-------------|------------------|---------|
| **Tapo Cameras** | ONVIF Protocol | Config file | Working |
| **Tapo Plugs** | Tapo Account API | Config + Env vars | Working |
| **Hue Bridge** | Philips Hue API | Config file | Working |
| **Tapo Lighting** | Tapo Account API | Config file | Working |
| **Ring Doorbell** | OAuth + Cache | Config + Token file | Working |
| **Netatmo Weather** | OAuth2 Refresh Token | Config file | Working |
| **Home Assistant** | Long-lived Access Token | Config file | Working |
| **USB Cameras** | Direct Device Access | No auth required | Working |

### **Configuration Loading Priority**
1. **YAML config file** (highest - current working method)
2. **Environment variables** (fallback)
3. **Token cache files** (OAuth persistence)
4. **Built-in defaults** (minimal fallback)

### **Security Notes**
- All credentials stored in local `config.yaml`
- OAuth tokens cached securely in token files
- No credentials transmitted in logs
- Environment variables used for sensitive fallbacks
- Configuration files excluded from version control

##  **DUAL ARCHITECTURE OVERVIEW**

**This repository has evolved into a comprehensive home security platform with dual-role architecture:**

### ** Role 1: Individual Security Device MCP Servers**
**Standalone MCP servers** for specific security device types that can run independently:
- **Devices MCP**: TP-Link camera control and monitoring
- **USB Webcam MCP**: Direct webcam management
- **Ring MCP**: Doorbell and security camera integration
- **Nest Protect MCP**: Smoke/CO detector monitoring
- **Plex MCP**: Media server integration and webhook handling

### ** Role 2: Unified Security Dashboard**
**Multi-MCP orchestration platform** that coordinates multiple MCP servers:
- **Single Interface**: Monitor all cameras + sensors + alarms + media in one dashboard
- **Cross-System Integration**: Correlate events across different security systems
- **Real-time Monitoring**: Live status updates from all integrated devices
- **Media Integration**: Plex media server webhook support for activity tracking
- **Remote Access**: Mobile monitoring via Tailscale VPN

**The platform serves as the "conductor" that brings together multiple specialized security devices (MCP servers) into a cohesive home surveillance ecosystem.**

##  **v1.17.1 RELEASE - CURSOR IDE MCP INTEGRATION FIXED**  (January 2026)

** BETA STATUS - Active Development:**
- ** Dependency Validator**: Checks all libraries on EVERY startup - no more "it worked yesterday"!
- ** Connection Supervisor**: Polls ALL devices every 60s with auto-reconnect
- ** 3-Level Messaging**: Info/Warning/Alarm system with acknowledgement tracking
- ** Health Dashboard**: Real-time device status at `/health-dashboard`
- ** Alerts Dashboard**: Message center at `/alerts`
- ** Prometheus Integration**: Metrics endpoint for Grafana monitoring
- ** Loki-Compatible Logs**: Structured JSON logging for Promtail/Loki
- ** Dual-Line Weather Graphs**: Compare main station + bathroom + outdoor modules
- ** Tapo P115 Fixed**: Smart plugs now showing real-time power data
- ** Plex Integration**: Media server webhook support with activity tracking
- ** Complete Routing**: All 25+ webapp pages now functional (no more 404s!)
- ** Enhanced Theming**: Camera cards and status indicators fully theme-aware

**v1.7.0:**
- ** Session-Based Auth**: Complete authentication system with secure password hashing
- ** Global Lighting Controls**: All On/Off, 50%, 100%, Disco mode buttons
- ** Color Controls**: Full RGB color picker for color-capable Hue bulbs
- ** Performance**: Near-instant light changes (optimized API calls)
- ** Auto-Refresh**: Periodic device rescan to catch wall switch/remote changes
- ** User Menu**: Dropdown with Settings and Sign Out in topbar

**v1.6.1:**
- ** SOTA Voice Stack**: Faster-Whisper  Vosk  Whisper (STT), Piper  Edge-TTS  pyttsx3 (TTS)
- ** Always-On Wake Word**: OpenWakeWord/Vosk background listener ("hey tapo")
- ** Real Nest OAuth**: Direct Google Nest API integration (no Home Assistant needed!)
- ** Prank Modes**: Hue light chaos/wave/disco/sos + PTZ camera nod/shake/dizzy
- ** Fully Offline**: Zero network traffic for voice - all local processing

**v1.6.0:**
- ** TTS/STT**: speak, announce, listen, voice_command actions
- ** Alarm Sounds**: 10 built-in types (siren, beep, doorbell, etc.)
- ** PTZ Pranks**: Camera movement fun modes

##  **v1.5.0 RELEASE - RING & NEST INTEGRATION**

** PREVIOUS:
- ** Ring Doorbell WebRTC**: Live video streaming + push-to-talk (NO subscription required!)
- ** Ring Alerts**: Full-screen DING popup + motion toast notifications on dashboard
- ** Plex Media Server**: Webhook integration for media activity tracking
- ** Nest Protect Setup**: Home Assistant bridge for smoke/CO detector integration
- ** Two-Way Talk**: WebRTC audio for speaking to visitors at door
- ** Ring Tests**: Comprehensive pytest suite for Ring client and API
- ** Ring Docs**: Full integration guide with subscription comparison
- ** Enhanced UI**: Modern gradient status cards, setup instructions, one-click initialization
- ** Ring Dashboard**: Dedicated `/ring` page with device cards, alarm controls, event timeline
- ** Nest Dashboard**: Dedicated `/nest` page with device status, alerts, and Home Assistant integration

**Previous v1.4.0:**
- ** Philips Hue Lighting**: 18 lights, 6 groups, 11 predefined scenes, cached device lists
- ** Netatmo Weather**: Live indoor weather from your station (pyatmo 8.x OAuth)
- ** Vienna External Weather**: Open-Meteo API (free, no key) with 5-day forecast
- ** Kitchen Dashboard**: Tefal Optigrill, Zojirushi water boiler integration
- ** Robots Dashboard**: Roomba, Unitree Go2 planned integrations

** Current Status**: Beta - Full smart home platform with Ring doorbell, lighting, weather, kitchen, and robots dashboards. **Active development - features may change.**

##  **DUAL ARCHITECTURE CAPABILITIES** (November 2025)

### ** ASPECT 1: INDIVIDUAL MCP SERVERS**

####  **WORKING NOW**
- ** Devices MCP**: TP-Link Tapo camera control and monitoring
- ** USB Webcam MCP**: Auto-detection and management
- ** Cursor IDE Integration**:  WORKING - Full MCP protocol compliance for Cursor IDE
- ** Claude Desktop Integration**: MCP protocol compliance for AI assistants
- ** Camera Management Tools**: Add, configure, and control cameras
- ** Real-time Status**: Camera connection health and diagnostics

####  **CORE MCP FEATURES**
- **MCP 3.1 Protocol**: Full Model Context Protocol compliance (FastMCP 3.2.0)
- **Modular Camera Types**: Extensible architecture for new camera brands
- **Asynchronous Operations**: High-performance async I/O
- **Type-Safe APIs**: Full type hints and Pydantic validation

### ** ASPECT 2: UNIFIED SECURITY DASHBOARD**

####  **WORKING NOW**
- ** Live Security Dashboard**: Single interface at `localhost:7777`
- ** Multi-MCP Integration**: Connect multiple security MCP servers
- ** Real-time Monitoring**: Cameras + sensors + alarms in one view
- ** Alert Aggregation**: Unified security event display
- ** Mobile Access**: Works on iPad/iPhone via Tailscale

####  **CORE DASHBOARD FEATURES**
- **Multi-Server Coordination**: Nest Protect, Ring, and other MCPs
- **Security Event Correlation**: Cross-system alert analysis
- **Professional UI/UX**: Responsive design with real-time updates
- **Remote Monitoring**: Access anywhere via secure VPN

###  **SUPPORTED CAMERA TYPES**
- ** USB Webcams**: Auto-detected with live thumbnails (WORKING)
- ** Tapo Cameras**: TP-Link Tapo series with full control
- ** Ring Cameras**: Ring doorbell and security cameras
- ** Petcube Cameras**: Petcube pet cameras with full API access (READY)

###  **LLM INTEGRATION** (NEW in v1.3.0)
- **Ollama**: Local LLM support with model management
- **LM Studio**: Desktop LLM integration
- **OpenAI**: Cloud-based AI capabilities
- **Chatbot UI**: Floating chat interface with streaming support
- **API Access**: Complete REST API for LLM operations

###  **DOCKER DEPLOYMENT** (NEW in v1.3.0)
- **MyHomeControl Stack**: Complete Docker Compose setup
- **Production Builds**: Optimized images with minimal dependencies
- **Health Monitoring**: Container health checks and monitoring
- **Network Integration**: Unified Docker network for all services

##  **MCP CLIENT ARCHITECTURE** (v1.17.0)

### ** Unified Communication Layer**

**All web API endpoints now use MCP client architecture** instead of direct manager calls, providing:

- ** Standardized Protocol**: Consistent MCP stdio communication across all APIs
- ** Enhanced Testability**: Comprehensive mocking and integration testing
- ** Better Performance**: Async connection pooling and optimized tool calls
- ** Improved Maintainability**: Clean separation between web and business logic
- ** Future-Proof**: Extensible architecture for new MCP integrations

### ** MCP Tool Integration**

#### **Portmanteau Tools** - Consolidated Operations
- `energy_management` - Smart plug and energy monitoring
- `motion_management` - Motion detection and camera events
- `camera_management` - Camera control and streaming
- `ptz_management` - Pan-Tilt-Zoom operations
- `media_management` - Media capture and streaming
- `system_management` - System operations and logging
- `medical_management` - Medical device control
- `security_management` - Security system integration
- `lighting_management` - Lighting control systems

#### **Migration Benefits**
```python
# Before (Direct Manager Calls)
from ...tools.energy.tapo_plug_tools import tapo_plug_manager
devices = await tapo_plug_manager.get_all_devices()

# After (MCP Client)
result = await call_mcp_tool("energy_management", {"action": "status"})
devices = result.get("data", {}).get("devices", [])
```

### ** Enterprise Testing Infrastructure**

#### **Comprehensive Test Coverage** (120+ test methods)
- **Unit Tests**: 92% coverage with isolated component testing
- **Integration Tests**: Full MCP client-server interaction validation
- **Performance Tests**: Automated benchmarking and regression detection
- **API Contract Tests**: OpenAPI specification validation
- **Windows Testing**: Windows compatibility validation

#### **Advanced Testing Features**
- **Mock MCP Server**: Configurable mock server for realistic testing
- **Test Data Factories**: Consistent, realistic test data generation
- **Performance Timers**: Built-in response time validation
- **Async Testing Support**: Comprehensive asyncio testing utilities
- **CI/CD Integration**: Automated testing pipeline with artifact generation

### ** Production-Ready CI/CD**

#### **10 Comprehensive Pipeline Jobs**
1. **Quality Checks**: Linting, type checking, security scanning
2. **Unit Tests**: Multi-version Python testing with coverage
3. **Integration Tests**: MCP protocol and component interaction testing
4. **API Contract Tests**: Live server API validation
5. **Performance Tests**: Benchmarking and load testing
6. **Security Tests**: Vulnerability scanning and dependency analysis
7. **Windows Tests**: Windows compatibility validation
8. **Container Tests**: Docker image validation and health checks
9. **Deployment Tests**: Production deployment validation
10. **Test Reporting**: Comprehensive results and artifact generation

###  **UNSUPPORTED CAMERAS**
- ** Furbo Cameras**: **NOT SUPPORTED** - Furbo intentionally blocks third-party API access. Use official Furbo app only.

###  **PETCUBE INTEGRATION** 

**Petcube Bites 2 Lite** is now fully supported as an excellent Furbo replacement!

#### ** Camera Features:**
- **1080p Full HD** video with night vision
- **160 wide-angle** lens
- **Two-way audio** with noise cancellation
- **Motion detection** with smart alerts
- **Cloud storage** (30 days free)

#### ** Smart Features:**
- **Dual treat compartments** (vs Furbo's single)
- **Laser pointer** for interactive play
- **Auto-play** mode with built-in toys
- **Custom feeding schedules**
- **Medication dispensing** capability

#### ** Battery & Connectivity:**
- **12-hour battery life** (rechargeable)
- **WiFi + Bluetooth** connectivity
- **Mobile app** for iOS/Android
- **Alexa/Google Home** integration

#### ** Pricing & Value:**
- **Price:** $199-249 (vs Furbo's $249-349)
- **Better value:** More features, lower price
- **API access:** Full third-party integration
- **Where to buy:** Amazon, Petcube website, pet stores

#### ** MCP Configuration:**
```yaml
cameras:
  my_petcube:
    type: petcube
    params:
      email: "your_petcube_account@example.com"
      password: "your_password"
      device_id: "optional_device_id"  # Auto-detected if not specified
```

#### ** MCP Features:**
-  **Live video streaming**
-  **Remote treat dispensing**
-  **Motion/sound alerts**
-  **Battery monitoring**
-  **Status tracking**
-  **Automated pet care**

#### ** Why Petcube Over Furbo:**
| Feature | Furbo  | Petcube  |
|---------|----------|------------|
| **API Access** | Blocked |  Official API |
| **Treat Compartments** | 1 | 2 |
| **Interactive Toys** | Limited | Laser + Auto-play |
| **Third-party Apps** | Forbidden |  Allowed |
| **Price** | $249-349 | $199-249 |
| **MCP Integration** |  Impossible |  Full support |

**Petcube is the clear winner for API-accessible pet cameras!** 

###  **CAMERA CONTROLS** (Next Phase)
- **Live Streaming**: RTSP, RTMP, and HLS streaming support
- **PTZ Control**: Pan, tilt, and zoom (where supported)
- **Motion Detection**: Configurable motion detection settings
- **Snapshot Capture**: Capture still images from video streams
- **Audio Support**: Two-way audio where available

###  **INTEGRATIONS**

#### ** MCP SERVER ECOSYSTEM** (Dual Role)
**This repository serves dual purposes:**
1. ** Individual MCP Servers**: Standalone camera control (Tapo, USB, Ring)
2. ** Unified Security Dashboard**: Multi-MCP orchestration platform

#### ** Multi-MCP Coordination** (Dashboard Role)
- **Nest Protect MCP**: Real-time smoke/CO detector monitoring
- **Ring MCP**: Doorbell and security camera integration
- **Unified Dashboard**: Single interface for all security devices
- **Cross-System Alerts**: Correlated security events and notifications
- **Health Monitoring**: Real-time status of all integrated MCP servers

#### ** Claude Desktop Integration** (MCP Server Role)
- ** MCP 3.1 Protocol**: Seamless Claude Desktop & Cursor IDE integration (WORKING)
- ** Cursor IDE**:  WORKING - Full camera control through Cursor MCP tools
- ** Camera Management Tools**: Add, configure, and control cameras
- ** Real-time Status**: Camera connection health and diagnostics
- ** AI Assistant Ready**: Full MCP compliance for intelligent camera control

#### ** Web & API Interfaces** (Dashboard Role)
- ** Live Security Dashboard**: Real-time monitoring at `localhost:7777`
- ** REST API**: HTTP endpoints for remote control and monitoring
- ** Grafana Dashboards**: Real-time monitoring and visualization (planned)
- ** Mobile Access**: Works on iPad/iPhone via Tailscale

###  **VIDEO STREAMING DASHBOARD** (Next Phase)
- **Live Video Streams**: Real-time MJPEG streaming from USB webcams
- **RTSP Integration**: Direct streaming from Tapo cameras
- **Dynamic Camera Management**: Add/remove cameras on the fly

###  **DEVICE ONBOARDING SYSTEM** (NEW - January 2025)
- **Progressive Discovery**: Automatic scanning for Tapo P115, Nest Protect, Ring devices, and USB webcams
- **Smart Configuration**: User-friendly device naming, location assignment, and settings
- **Authentication Integration**: OAuth setup for Nest Protect and Ring devices
- **Cross-Device Integration**: Intelligent recommendations for device combinations
- **Beautiful Progressive UI**: Step-by-step onboarding with real-time progress tracking
- **Error Recovery**: Comprehensive error handling with user guidance
- **API-First Design**: Full programmatic access to onboarding functionality

###  **STABILITY & MONITORING SYSTEM** (NEW - December 2025)

####  **Beta Reliability Features**
- **Dependency Validator**: Checks all 20+ libraries on every startup - prevents "it worked yesterday" failures
- **Connection Supervisor**: Polls ALL devices every 60s with automatic reconnection
- **3-Level Alerting**: Info () / Warning () / Alarm () system with escalation
- **Health Dashboard**: Real-time device status at `/health-dashboard`
- **Alerts Dashboard**: Message center with acknowledgement at `/alerts`
- **Demo-Proof**: No silent failures during demonstrations!

####  **Monitoring Stack Integration**
- **Prometheus Metrics**: `/api/messages/prometheus` endpoint ready for scraping
- **Loki Logs**: Structured JSON logging compatible with Promtail ingestion
- **Grafana Ready**: Dashboards for device uptime, alert timelines, power consumption
- **Alert Escalation**: 1 failure  WARNING, 3 failures (180s)  ALARM
- **Auto-Recovery**: Supervisor attempts reconnection on device failures

**Prometheus Scrape Config:**
```yaml
scrape_configs:
  - job_name: 'tapo_home'
    static_configs:
      - targets: ['localhost:7777']
    metrics_path: '/api/messages/prometheus'
    scrape_interval: 30s
```

###  **ADVANCED FEATURES** (NEW - January 2025)

####  **Energy Management Dashboard**
- **Tapo P115 Smart Plugs**: Energy monitoring and control (REAL DATA!)
- **Real-time Power Consumption**: Live wattage, voltage, and current monitoring
- **Cost Analysis**: Daily, monthly, and annual energy cost tracking
- **Smart Scheduling**: Automated power management based on usage patterns
- **Energy Saving Mode**: Intelligent power optimization
- **Historical Data**: Limited to current day (P115 limitation) with Home Assistant integration recommended

####  **Lighting Control Dashboard** (ENHANCED in v1.7.0)
- **Philips Hue Integration**: Full support for Hue Bridge and lights
- **Light Discovery**: Automatic discovery (18 lights, 6 groups detected)
- **Light Control**: On/off toggle and brightness adjustment (instant response)
- **Color Controls**: Full RGB color picker for color-capable bulbs
- **Global Controls**: Quick action buttons (All On/Off, 50%, 100%, Disco mode)
- **Group Management**: Support for Hue groups/rooms with bulk control
- **Scene Activation**: 11 predefined scenes (Sunset, Aurora, Energize, etc.)
- **Performance Caching**: Device lists cached on startup for instant page loads
- **Auto-Refresh**: Periodic rescan every 2 minutes to catch wall switch changes
- **Rescan Button**: Manual refresh of lights/groups/scenes with last scan timestamp
- **Settings Integration**: Bridge IP and username configuration via settings page

####  **Weather Dashboard** (ENHANCED v1.8.0)
- **Multi-Module Netatmo**: Main station + bathroom module (NAModule4 support)
- **Dual-Line Graphs**: Compare main (red) vs bathroom (orange) vs outdoor (teal)
- **Real-Time Data**: 26.8C main, 26.6C bathroom - see room differences!
- **Vienna External Weather**: Open-Meteo API (5.5C, slight rain)
- **Dynamic Station Cards**: Auto-loads YOUR real devices (70:ee:50:3a:0e:dc @ Stroheckgasse)
- **5-Day Forecast**: Daily forecast with weather icons
- **Historical Charts**: 4 metrics  3 time ranges, auto-refresh every 30s
- **CO2 Monitoring**: Threshold warnings (800 ppm yellow, 1000 ppm red)
- **Battery Indicators**: Shows battery level for wireless modules ( 60%)
- **Outdoor Sensor Ready**: Automatic detection when NAModule1 installed

####  **Kitchen Dashboard** (NEW in v1.4.0)
- **Tefal Optigrill**: Smart grill status and control
- **Zojirushi Water Boiler**: On/off via Tapo P115 smart plug
- **Smarter iKettle**: Alternative smart kettle research

####  **Robots Dashboard** (NEW in v1.4.0)
- **Roomba**: Coming soon integration
- **Unitree Go2**: Planned purchase with specs
- **Pilot Labs Moorebot Scout**: AI home patrol robot (arriving Jan 2025)

####  **Alarm System Integration**
- **Nest Protect**: Smoke and CO detector monitoring
- **Ring Alarms**: Door/window sensors and motion detectors
- **Alert Correlation**: Cross-system event analysis with camera feeds
- **Battery Monitoring**: Device health and maintenance alerts
- **Test Scheduling**: Automated device testing and validation

####  **AI-Powered Analytics**
- **Scene Analysis**: Computer vision-based scene understanding
- **Object Detection**: People, vehicles, and activity recognition
- **Performance Analytics**: System health and optimization recommendations
- **Smart Automation**: Intelligent scheduling and predictive maintenance
- **Pattern Recognition**: Usage pattern analysis and optimization

####  **Advanced Dashboard Components**
- **Energy Charts**: Lightweight Chart.js-based energy consumption visualization
- **Real-time Updates**: Live data refresh every minute
- **Interactive Controls**: Device management and automation configuration
- **Mobile Responsive**: Optimized for tablet and smartphone access
- **Export Capabilities**: Chart and data export functionality

##  **QUICK START** (What Works Now)

### **1. Start the Web Dashboard**
```bash
# Start dashboard with auto-USB webcam detection
python start.py dashboard
```
**Result**: Dashboard at `http://localhost:7777` with USB webcam monitoring

### **2. Check Claude Desktop Integration**
```bash
# MCP server should load automatically in Claude Desktop
# Look for Tapo Camera tools in Claude
```

### **3. Current Working Features**
-  **USB Webcam Detection**: Auto-discovered on dashboard load
-  **Real-time Status**: Camera connection monitoring
-  **Professional UI**: Clean, responsive dashboard interface
-  **MCP Tools**: 30+ tools available in Claude Desktop (FastMCP 3.2.0 compliant)
  - **Device Onboarding**: Progressive discovery and configuration tools
  - **Energy Management**: Tapo P115 smart plug control and monitoring
  - **Lighting Control**: Philips Hue Bridge integration (18 lights, 11 scenes)
  - **Weather Integration**: Netatmo indoor + Vienna external weather
  - **Security Integration**: Nest Protect and Ring device management
  - **AI Analytics**: Performance monitoring and intelligent automation

### **4. Next Steps** (Tapo Camera Integration)
```bash
# Once we resolve authentication:
# Add your C200 cameras with correct credentials
# Enable live video streaming in dashboard
# Full camera control through Claude
```
- **Stream Controls**: Start/stop streaming per camera
- **Responsive Design**: Works on desktop and mobile browsers
- **Real-time Status**: Live camera status and health monitoring
- **Snapshot Capture**: Instant image capture from any camera
- **Multi-camera View**: Grid layout for multiple camera feeds

###  Development Tools
- **CLI Interface**: Command-line tools for administration
- **Mock Camera**: Simulated camera for testing
- **Comprehensive Logging**: Structured logging throughout codebase
- **Unit Tests**: Complete test suite with 100% pass rate
- **CI/CD Pipeline**: GitHub Actions with modern ruff linting, caching, and Python 3.10-3.12 testing
- **Security Scanning**: Automated vulnerability and dependency scanning
- **Code Quality**: Ruff linting and formatting, mypy type checking, pylint linting

##  Getting Started

###  **Device Onboarding** (NEW!)

**Progressive device setup for any combination of devices:**

```bash
# Start the server
python -m devices_mcp.web.server

# Open the onboarding dashboard
open http://localhost:7777/onboarding
```

**Supported Device Types:**
- **Tapo P115 Smart Plugs**: Energy monitoring and control
- **Nest Protect Devices**: Smoke and CO detector monitoring
- **Ring Devices**: Doorbell, motion sensors, and contact sensors
- **USB Webcams**: Video streaming and capture

**Features:**
- **Automatic Discovery**: Network scanning for all supported devices
- **Smart Configuration**: User-friendly naming and location assignment
- **Cross-Device Integration**: Intelligent automation recommendations
- **Progressive UI**: Step-by-step guided setup process

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx devices-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "devices-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "devices-mcp"]
  }
}
```
#### Option 1: MCPB Package (Recommended for Claude Desktop)

**One-click installation** for Claude Desktop users:

1. Download the latest `.mcpb` package from [GitHub Releases](https://github.com/sandraschi/devices-mcp/releases)
2. Drag the `.mcpb` file to Claude Desktop
3. Configure camera settings when prompted:
   - Tapo Camera IP Address (optional)
   - Tapo Camera Username (optional)
   - Tapo Camera Password (optional)
   - Web Dashboard Port (default: 7777)
4. Restart Claude Desktop
5. All 26+ tools are now available!

**Quick Start with MCPB:**
```
"Connect to my USB webcam using add_camera tool"
"Start the dashboard and show me the camera feed"
```

**See [MCPB Quick Start Guide](docs/MCPB_QUICKSTART.md) for detailed instructions.**

###  **Advanced Documentation**
- **[HomeAware Motion Detection](docs/HOMEAWARE_MOTION_DETECTION.md)**: Zigbee mesh signal strength monitoring for motion detection
- **[Error Handling Guide](docs/ERROR_HANDLING.md)**: Circuit breakers, timeouts, and crash prevention
- **[MCP Production Checklist](docs/MCP_PRODUCTION_CHECKLIST.md)**: Audit checklist for production readiness

---

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx devices-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "devices-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "devices-mcp"]
  }
}
```
### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- OpenCV (for webcam support)
- TP-Link Tapo camera(s), Ring doorbell, or USB webcam

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx devices-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "devices-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "devices-mcp"]
  }
}
```
#### Python Version Management with uv (or pyenv)

**uv** is a fast Python package installer and resolver (similar to nvm for Node.js). Alternatively, you can use **pyenv** for Python version management:

```powershell
# Windows (PowerShell)
# Install uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install Python 3.11 (or 3.10, 3.12)
uv python install 3.11

# Create virtual environment with specific Python version
uv venv --python 3.11

# Activate virtual environment
.\venv\Scripts\activate

# Install project dependencies
uv pip install -e ".[dev]"
```

```bash
# macOS/Linux
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11 (or 3.10, 3.12)
uv python install 3.11

# Create virtual environment with specific Python version
uv venv --python 3.11

# Activate virtual environment
source .venv/bin/activate

# Install project dependencies
uv pip install -e ".[dev]"
```

**Alternative: Using pyenv for Python version management:**

```bash
# macOS/Linux
# Install pyenv
curl https://pyenv.run | bash

# Add to shell configuration
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.0
pyenv local 3.11.0

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install project dependencies
pip install -e ".[dev]"
```

#### Node.js Version Management with nvm or nvx (Optional)

If you need Node.js for Grafana plugins or other frontend components:

**Option 1: Using nvm (Node Version Manager)**

```powershell
# Windows (PowerShell)
# Install nvm-windows from: https://github.com/coreybutler/nvm-windows/releases
# Or use Chocolatey:
choco install nvm

# Install Node.js 20 LTS
nvm install 20
nvm use 20

# Verify installation
node --version
npm --version
```

```bash
# macOS/Linux
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc

# Install Node.js 20 LTS
nvm install 20
nvm use 20

# Verify installation
node --version
npm --version
```

**Option 2: Using nvx (Universal NVM - Cross-platform)**

nvx is a universal Node.js version manager that works on both Unix and Windows:

```bash
# Install nvx via npm (requires npm 5.2.0+)
npm install -g nvx

# Run commands with specific Node.js version
nvx 20 node --version

# Or install and use a specific version
nvx install 20
nvx use 20

# Verify installation
node --version
npm --version
```

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx devices-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "devices-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "devices-mcp"]
  }
}
```
### Configuration

1. Copy the example configuration file:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` with your camera details:
   ```yaml
   cameras:
     living_room:
       type: tapo
       host: 192.168.1.100
       username: your_username
       password: your_password
     webcam:
       type: webcam
       device_id: 0

   # Authentication (optional - disabled by default)
   auth:
     enabled: false  # Set to true to require login
     users:
       admin:
         password: admin123  # Change this!
         role: admin
   ```

###  **Authentication** (NEW in v1.7.0)

The dashboard supports optional session-based authentication:

**Enable Authentication:**
1. Edit `config.yaml` and set `auth.enabled: true`
2. Configure users with passwords
3. Restart the server
4. Access dashboard at `http://localhost:7777` - you'll be redirected to login

**Features:**
- **Secure Password Hashing**: PBKDF2-SHA256 with salt
- **Session Management**: 24-hour sessions (30 days with "remember me")
- **User Menu**: Dropdown in topbar with Settings and Sign Out
- **Auto-Redirect**: Logged-in users can't access login page
- **Public Paths**: Login, static files, and API endpoints remain accessible

**Default User:**
When auth is first enabled, a default admin user is created with a random password (printed to console). Change it immediately in `config.yaml`!

---

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx devices-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "devices-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/devices-mcp", "run", "devices-mcp"]
  }
}
```
##  **CURSOR IDE MCP INTEGRATION WORKING**

**Cursor IDE Configuration** -  WORKING:

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "python",
      "args": ["-m", "devices_mcp.server_v2", "--direct"],
      "cwd": "D:/Dev/repos/devices-mcp",
      "env": {
        "PYTHONPATH": "D:/Dev/repos/devices-mcp",
        "TAPO_MCP_SKIP_HARDWARE_INIT": "true"
      }
    }
  }
}
```

**Fast Startup Option:**

If the server takes too long to start (>1 minute), add `TAPO_MCP_SKIP_HARDWARE_INIT=true` to the `env` section. This skips hardware initialization during startup - hardware will initialize automatically on first use. This reduces startup time from 30-60 seconds to <5 seconds.

**Without fast startup:** Server initializes all hardware (cameras, Hue, Netatmo, Ring, etc.) during startup (10s timeout)
**With fast startup:** Server starts immediately, hardware initializes on-demand when tools are used

**Cursor IDE Configuration:**

**Option 1: Copy the configuration file**

A ready-to-use configuration file is provided: `mcp-config.json`. Copy this file to:

- **Cursor**: `~/.cursor/mcp.json` (or use Cursor Settings  MCP tab)
- **Claude Desktop**: `%APPDATA%\Claude\claude_desktop_config.json`

**Option 2: Manual configuration**

Edit Cursor settings (Cmd+, on Mac or Ctrl+, on Windows)  MCP tab, or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "D:/Dev/repos/devices-mcp/venv/Scripts/python.exe",
      "args": ["-m", "devices_mcp.cli_v2"],
      "cwd": "D:/Dev/repos/devices-mcp",
      "env": {
        "PYTHONPATH": "D:/Dev/repos/devices-mcp/src",
        "TAPO_MCP_SKIP_HARDWARE_INIT": "true"
      }
    }
  }
}
```

**Alternative Configuration (if cli_v2 doesn't work):**

```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "D:/Dev/repos/devices-mcp/venv/Scripts/python.exe",
      "args": ["-m", "devices_mcp.server_v2", "--direct"],
      "cwd": "D:/Dev/repos/devices-mcp",
      "env": {
        "PYTHONPATH": "D:/Dev/repos/devices-mcp/src",
        "TAPO_MCP_SKIP_HARDWARE_INIT": "true"
      }
    }
  }
}
```

**Important Notes:**
- Replace `D:/Dev/repos/devices-mcp` with your actual repository path
- Use absolute paths (not relative)
- Ensure Python 3.10+ is in your PATH
- Restart Claude Desktop or Cursor after configuration
- Verify installation by asking Claude/Cursor: "List available camera tools"
-  **Cursor IDE**: All Tapo MCP tools should now be available in Cursor

**Troubleshooting JSON Config:**
- Check Python path: `python --version` or `python3 --version`
- Verify module exists: `python -m devices_mcp.cli_v2 --help`
- Check logs: `%APPDATA%\Claude\logs\` (Windows) or Cursor logs
-  **Cursor IDE**: If tools don't appear, check Cursor MCP settings and restart Cursor

**Fast Startup (Skip Hardware Init):**

If the server takes more than 1 minute to start, add `TAPO_MCP_SKIP_HARDWARE_INIT=true` to the `env` section:

```json
{
  "mcpServers": {
    "devices-mcp": {
      "command": "python",
      "args": ["-m", "devices_mcp.server_v2", "--direct"],
      "cwd": "D:/Dev/repos/devices-mcp",
      "env": {
        "PYTHONPATH": "D:/Dev/repos/devices-mcp",
        "TAPO_MCP_SKIP_HARDWARE_INIT": "true"
      }
    }
  }
}
```

This skips hardware initialization during startup (reduces startup from 30-60s to <5s). Hardware will initialize automatically when tools are first used.

---

##  Usage

### Starting the MCP Server

```bash
# Start MCP server for Claude Desktop integration
python -m devices_mcp.server_v2 --direct

# Start with debug logging
python -m devices_mcp.server_v2 --direct --debug
```

### Starting the Web Dashboard

```bash
# Start the web dashboard (separate terminal)
python -m devices_mcp.web.server

# Dashboard will be available at: http://localhost:7777
```

### Quick Start Script

```bash
# Check dependencies
python start.py check

# Test webcam
python start.py test

# Start MCP server only
python start.py mcp

# Start dual interface server (MCP + REST API)
python start.py dual

# Start web dashboard only
python start.py dashboard

# Start both services
python start.py both

# Test webcam and start dashboard
python start.py webcam
```

### Using the CLI

```bash
# List all available commands
devices-mcp --help

# Camera Management
devices-mcp camera list                   # List all cameras
devices-mcp camera status <camera_name>   # Get camera status
devices-mcp camera info <camera_name>     # Get detailed camera info

# PTZ Controls
devices-mcp camera ptz move --direction up --speed 0.5
devices-mcp camera ptz preset save --name "Home"
devices-mcp camera ptz preset goto --name "Home"

# Media Controls
devices-mcp camera snapshot               # Take a snapshot
devices-mcp camera record start           # Start recording
devices-mcp camera record stop            # Stop recording

# System Management
devices-mcp system status                # Check system status
devices-mcp system restart               # Restart the server
devices-mcp system update                # Update to the latest version
```

## API Reference

### Web Dashboard Endpoints

- `GET /` - Main dashboard page
- `GET /api/cameras` - Get list of all cameras
- `GET /api/cameras/{camera_id}/stream` - Get video stream (MJPEG/RTSP)
- `GET /api/cameras/{camera_id}/snapshot` - Get camera snapshot
- `GET /api/status` - Get server status

### MCP Tools

#### Camera Management
- `list_cameras` - List all registered cameras
- `add_camera` - Add a new camera to the system
- `connect_camera` - Connect to a specific camera
- `disconnect_camera` - Disconnect from camera
- `get_camera_info` - Get detailed camera information
- `get_camera_status` - Get camera status and health

#### PTZ Controls
- `move_ptz` - Move PTZ camera (pan, tilt, zoom)
- `get_ptz_position` - Get current PTZ position
- `save_ptz_preset` - Save current position as preset
- `recall_ptz_preset` - Move to saved preset position
- `go_to_home_ptz` - Return to home position
- `stop_ptz` - Stop PTZ movement

#### Media Operations
- `capture_image` - Capture still image from camera
- `start_recording` - Start video recording
- `stop_recording` - Stop video recording
- `get_recording_status` - Get recording status

#### System Management
- `get_system_info` - Get camera system information
- `reboot_camera` - Reboot the camera
- `get_logs` - Get system logs
- `set_motion_detection` - Configure motion detection
- `set_led_enabled` - Control LED status
- `set_privacy_mode` - Enable/disable privacy mode

##  Development

### Project Structure

```
src/devices_mcp/
 core/               # Core server implementation
 camera/             # Camera implementations
    base.py         # Base camera class
    tapo.py         # Tapo camera implementation
    ...
 api/                # API endpoints
    v1/             # API version 1
 tools/              # MCP tools
    camera/         # Camera-related tools
    ptz/            # PTZ controls
    system/         # System tools
 web-sota/           # Web dashboard (Vite frontend + FastAPI backend)
 cli_v2.py           # Command-line interface
```

### Setting Up Development Environment

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/devices-mcp.git
   cd devices-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   pre-commit install
   ```

### Building MCPB Package

To build an MCPB package for distribution:

```powershell
# Windows (PowerShell)
.\scripts\build-mcpb-package.ps1 -NoSign

# Or build manually
mcpb pack . dist/devices-mcp.mcpb
```

The package will be created in `dist/devices-mcp.mcpb` (approximately 280KB).

**For automated builds**: Push a version tag to trigger GitHub Actions:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Running Tests

```bash
# Run unit tests with coverage
pytest tests/unit/ --cov=devices_mcp --cov-report=html

# Run all tests
pytest tests/ -v

# Run MCP protocol tests
pytest tests/test_mcp_protocol.py

# Run with specific Python version (in CI/CD)
python -m pytest --cov=devices_mcp --cov-report=xml
```

### Code Style

This project uses `ruff` for code linting and formatting. Before committing, run:

```bash
ruff check src/ tests/
ruff format src/ tests/
pylint devices_mcp/
```

##  MCPB Packaging

This project supports **MCPB (MCP Bundle)** packaging for one-click installation in Claude Desktop.

**For Users:**
- Download `.mcpb` file from [Releases](https://github.com/sandraschi/devices-mcp/releases)
- Drag to Claude Desktop
- Configure and enjoy!

**For Developers:**
- See [MCPB Quick Start](docs/MCPB_QUICKSTART.md)
- Build with `.\scripts\build-mcpb-package.ps1 -NoSign`
- Full guide in [docs/mcpb-packaging/](docs/mcpb-packaging/)

---


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [TP-Link](https://www.tp-link.com/) for their Tapo camera products
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- [Anthropic](https://www.anthropic.com/) for Claude Desktop and MCPB toolkit
- [Ring](https://ring.com/) for Ring doorbell integration
- [Home Assistant](https://www.home-assistant.io/) - The weird, wonderful smart home platform that inspired this entire ecosystem

**Note:** Furbo cameras are not supported due to their intentional API restrictions. Use the official Furbo app for Furbo camera access.
- [aiohttp](https://docs.aiohttp.org/) for the async HTTP client/server
- [ONVIF](https://www.onvif.org/) for the camera control protocol

##  **Home Assistant Integration**

This project is designed to complement [Home Assistant](https://www.home-assistant.io/) - the "weird" but wonderful open-source smart home platform with 3400+ integrations.

### **Why the Container Approach?**

Home Assistant runs in VirtualBox containers on Windows for:
- **Stability**: Isolation prevents conflicts with host system
- **Consistency**: Same environment across all platforms
- **Security**: Sandboxed execution model
- **Dependency Management**: Clean Python environment

### **MCP Integration with Home Assistant**

#### **Automated HA Setup**
Use the `virtualization-mcp` to automate Home Assistant deployment:

```python
# Via MCP tool - complete HA setup in one command
result = await home_assistant_setup(
    vm_name="home-assistant",
    config_preset="recommended",
    ha_version="latest"
)
```

#### **Device Integration**
Configure cameras in HA for unified control:

```yaml
# HA configuration.yaml
camera:
  - platform: generic
    name: "Tapo Camera"
    still_image_url: "http://localhost:7777/api/cameras/tapo_001/snapshot"
    stream_source: "http://localhost:7777/api/cameras/tapo_001/stream"
```

### **The Community Factor**

Home Assistant's "soldering iron brigade" - hardware enthusiasts who:
- **DIY First**: Build before buying
- **Open Standards**: Zigbee/Z-Wave over proprietary
- **Local Control**: Data stays on your network
- **Privacy Focus**: No cloud dependencies

### **Complete Integration Guide**

 **[Home Assistant Integration Guide](../../mcp-central-docs/integrations/home-assistant/HOME_ASSISTANT_INTEGRATION_GUIDE.md)**

Covers:
- HA's unique "weird" architecture and philosophy
- Complete setup automation with virtualization MCP
- Hardware integration for the tinkerer community
- Camera and device integration patterns
- Community resources and troubleshooting

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
# Trigger workflow test
# Trigger CI
