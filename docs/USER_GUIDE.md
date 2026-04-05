# Devices MCP - User Guide

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Getting Started](#2-getting-started)
  - [2.1 Prerequisites](#21-prerequisites)
  - [2.2 Installation](#22-installation)
  - [2.3 Configuration](#23-configuration)
- [3. Web Interface](#3-web-interface)
- [4. Camera Management](#4-camera-management)
  - [4.1 Adding Cameras](#41-adding-cameras)
  - [4.2 Camera Groups](#42-camera-groups)
  - [4.3 Multiple Camera Types](#43-multiple-camera-types)
  - [4.4 Speakerphone & Audio Features](#44-speakerphone--audio-features)
- [5. Streaming](#5-streaming)
  - [5.1 Web Streaming](#51-web-streaming)
  - [5.2 VLC Streaming](#52-vlc-streaming)
  - [5.3 Multi-View Layouts](#53-multi-view-layouts)
- [6. Advanced Features](#6-advanced-features)
  - [6.1 Motion Detection](#61-motion-detection)
  - [6.2 PTZ Controls](#62-ptz-controls)
  - [6.3 Recording](#63-recording)
  - [6.4 Plex Media Server Integration](#64-plex-media-server-integration)
- [7. Troubleshooting](#7-troubleshooting)

## 1. Introduction

Devices MCP is a powerful server for managing multiple IP cameras with support for various brands including TP-Link Tapo, Ring, and Petcube. This guide covers all aspects of setting up and using the server.

**Note:** Furbo cameras are not supported due to their intentional API restrictions. Use Petcube cameras instead for API-accessible pet monitoring.

## 2. Getting Started

### 2.1 Prerequisites
- Python 3.8+
- pip package manager
- Network access to your cameras
- Camera credentials

### 2.2 Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/devices-mcp.git
cd devices-mcp

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .
```

### 2.3 Configuration
Edit `config.yaml` to set up your cameras and server settings. See the example configuration below:

```yaml
# Server settings
web_enabled: true
web_host: "0.0.0.0"
web_port: 7777
web_username: "admin"
web_password: "change_me"

# Camera configurations
cameras:
  - name: "living_room"
    type: "tapo"
    params:
      host: "192.168.1.100"
      username: "your_email@example.com"
      password: "your_secure_password"
    stream_quality: "hd"
    enabled: true
    motion_detection: true
    recording: false

# More configurations...
```

## 3. Web Interface

Access the web interface at `http://localhost:7777` (or your server's IP address).

![Web Interface](docs/images/web-interface.png)

### 3.1 Interface Features

The web interface features a modern, responsive design with full light/dark theme support and optimized readability across all devices.

**Key Features:**
- **Theme Support**: Automatic light/dark mode switching with consistent styling
- **Responsive Design**: Optimized layouts for desktop, tablet, and mobile devices
- **Real-time Updates**: Live status indicators and automatic data refresh
- **Modular CSS**: External stylesheets for maintainability and performance
- **Accessibility**: High contrast ratios and keyboard navigation support

**Recent Improvements (v1.19.0):**
- **USB Camera Server**: Integrated a dedicated local capture server on port 10705.
- **CSS Cleanup**: Migrated all inline styles to external CSS files for better maintainability.
- **Theme Variables**: Replaced hardcoded colors with CSS custom properties for consistent theming.
- **Readability Fixes**: Resolved "white on white" text issues across all dashboard pages.
- **Linting Cleanup**: Massive 160+ file cleanup for industrial-grade code quality.
- **Hardware Research**: Added support and research docs for Insta360 X5 and Pavo35 platforms.

### 3.2 Security Dashboards

The platform includes dedicated dashboards for security devices:

#### Ring Doorbell Dashboard (`/ring`)

Access at `http://localhost:7777/ring` to manage your Ring doorbell and alarm system.

**Features:**
- **Status Card**: Real-time connection status with color-coded indicators
  - 🟢 Green: Connected and ready
  - 🟡 Yellow: Needs initialization or 2FA
  - 🔴 Red: Configuration issue
- **One-Click Initialization**: "Initialize Connection" button for easy setup
- **2FA Support**: In-page form for submitting verification codes
- **Device Cards**: Visual display of battery, WiFi signal, model, firmware
- **Live View**: Direct WebRTC streaming (no subscription required)
- **Alarm Controls**: Disarm, Home, and Away mode buttons
- **Recent Events**: Timeline of motion and doorbell events
- **Toast Notifications**: User feedback for all actions

**Setup:**
1. Configure Ring credentials in `config.yaml`
2. Navigate to `/ring` dashboard
3. Click "Initialize Connection" if not connected
4. Submit 2FA code if prompted
5. Devices appear automatically once connected

See [Ring Setup Guide](ring-setup-guide.md) for detailed instructions.

#### Nest Protect Dashboard (`/nest`)

Access at `http://localhost:7777/nest` to monitor your Nest Protect smoke and CO detectors.

**Features:**
- **Status Card**: Connection status via Home Assistant integration
- **Device Cards**: Visual display of smoke/CO status, battery health, location
- **Alert Section**: Color-coded alerts (emergency = red, warning = yellow)
- **Auto-Refresh**: Status updates every 30 seconds
- **Setup Instructions**: Step-by-step Home Assistant configuration guide

**Setup:**
1. Ensure Home Assistant is running (`http://localhost:8123`)
2. Create a long-lived access token in Home Assistant
3. Configure Nest integration in Home Assistant (Settings → Devices & Services)
4. Add Home Assistant settings to `config.yaml`:
   ```yaml
   security:
     integrations:
       homeassistant:
         enabled: true
         url: http://localhost:8123
         access_token: "your_token_here"
   ```
5. Navigate to `/nest` dashboard to view devices

See [Nest Protect Setup Guide](nest-protect-setup-guide.md) for detailed instructions.

## 4. Camera Management

### 4.1 Adding Cameras
Add cameras through the web interface or config file. Supported parameters:
- `name`: Unique identifier
- `type`: Camera type (tapo, ring)
- `params`: Connection parameters
- `stream_quality`: hd or sd
- `enabled`: true/false

### 4.2 Camera Groups
Group cameras for batch operations:
```yaml
camera_groups:
  outdoor: ["front_door", "backyard"]
  all: ["living_room", "front_door", "backyard"]
```

### 4.3 Multiple Camera Types
Supported camera types and their requirements:

| Type  | Required Parameters           | Notes                          |
|-------|------------------------------|--------------------------------|
| Tapo  | host, username, password     | Uses Tapo API                  |
| Ring  | email, password, 2FA token   | Requires Ring account          |
| Petcube | email, password, device_id   | Petcube pet camera with treats |
| RTSP  | rtsp_url                     | Generic RTSP camera support    |

**Note:** Furbo cameras are not supported due to API restrictions. Use Petcube instead.

### 4.4 Speakerphone & Audio Features

**Speakerphone support varies by camera type:**

| Camera Type | Speakerphone | Microphone | Doorbell Detection | Notes |
|-------------|--------------|------------|-------------------|-------|
| **Ring Video Doorbell** | ✅ Yes | ✅ Yes | ✅ Yes | WebRTC two-way audio |
| **Tapo C200/C210** | ✅ Yes | ✅ Yes | ❌ No | Tinny speaker quality |
| **USB Webcams (Logitech)** | ❌ No | ✅ Yes | ❌ No | Microphone only |
| **USB Microscopes** | ❌ No | ✅ Yes | ❌ No | Specialized camera |
| **Petcube** | ✅ Yes | ✅ Yes | ❌ No | Treat dispensing audio |

#### **🔔 Ring Doorbell Integration**
- **Real-time doorbell detection** from Ring's event history
- **Event notifications** with timestamps and answered status
- **Recording links** to Ring cloud storage when available
- **Doorbell events panel** in web interface for recent activity

#### **📢 Speakerphone Controls**
- **Two-way audio** for compatible cameras (Ring, Tapo)
- **Enable/disable controls** in camera interface
- **Status indicators** showing speakerphone state
- **Quality notes** for different camera types

#### **🎤 Audio Capabilities**
- **Microphone input** for all cameras with audio hardware
- **Speaker output** only for cameras with built-in speakers
- **WebRTC streaming** for Ring cameras
- **RTSP audio** for Tapo cameras

### 4.5 Petcube Camera Setup

**Petcube Bites 2 Lite** is the recommended pet camera for MCP integration.

#### **🎯 Getting Started:**
1. **Purchase:** Buy Petcube Bites 2 Lite ($199-249)
2. **Setup:** Use Petcube app to configure camera
3. **Account:** Create Petcube account (email/password)
4. **MCP Config:** Add camera to your `config.yaml`

#### **🔧 Configuration:**
```yaml
cameras:
  my_petcube:
    type: petcube
    params:
      email: "your_petcube_account@example.com"
      password: "your_petcube_password"
      # device_id: optional - auto-detected if not specified
```

#### **🎮 MCP Features:**
- **Live streaming** through web interface
- **Remote treat dispensing** (up to 2 compartments)
- **Motion/sound alerts** with notifications
- **Battery monitoring** and status tracking
- **Automated pet care** schedules

#### **📱 Petcube Advantages over Furbo:**
- ✅ **Official API** (Furbo blocks third-party access)
- ✅ **Dual treat compartments** (vs Furbo's single)
- ✅ **Interactive toys** (laser pointer, auto-play)
- ✅ **Better price** ($199-249 vs Furbo's $249-349)
- ✅ **Full MCP integration** possible

## 5. Streaming

### 5.1 Web Streaming
Access live streams through the web interface. Supports:
- Individual camera views
- Multi-view layouts (1x1, 2x2, 3x3)
- Fullscreen mode

### 5.2 VLC Streaming
To view streams in VLC:
1. Get the RTSP URL from the web interface
2. Open VLC
3. Media > Open Network Stream
4. Enter URL: `rtsp://your-server:8554/stream/camera_name`

### 5.3 Multi-View Layouts
Create custom layouts in the web interface:
1. Go to Settings > Layouts
2. Create a new layout
3. Drag and drop camera streams
4. Save the layout

## 6. Advanced Features

### 6.1 Motion Detection
Configure motion detection per camera:
```yaml
motion_detection:
  enabled: true
  sensitivity: 0.7  # 0.1 to 1.0
  zones:             # Optional motion zones
    - name: "front_door"
      coordinates: [0,0, 100,0, 100,100, 0,100]  # x1,y1,x2,y2,...
  notifications: true
  snapshot: true
```

### 6.2 PTZ Controls
For PTZ-enabled cameras:
- Pan/Tilt: Click and drag the video
- Zoom: Mouse wheel or +/- buttons
- Presets: Save/recall camera positions

### 6.3 Recording
Configure automatic recording:
```yaml
recording:
  enabled: true
  mode: "motion"  # or "continuous"
  pre_buffer: 5   # seconds before motion
  post_buffer: 10  # seconds after motion
  path: "/path/to/recordings"
```

### 6.4 Plex Media Server Integration

Track media activity from your Plex server in the security dashboard.

#### **Setup Instructions:**
1. **Enable Webhooks in Plex:**
   - Open Plex Web app
   - Go to Settings → General → Webhooks
   - Add webhook URL: `http://your-server:7777/api/plex/webhook`

2. **Configure Events:**
   - Enable events: `media.play`, `media.pause`, `media.stop`, `media.resume`
   - All media activity will be logged and displayed in the dashboard

#### **Features:**
- **Real-time Activity**: See who's watching what on which device
- **Event Timeline**: Media events appear in the security dashboard timeline
- **Status Display**: Current playback status at `/plex` page
- **API Access**: Query current activity via `/api/plex/now-playing`

#### **Plex Page (`/plex`):**
- Browse your media library
- View "Continue Watching" progress
- See recently added content
- Monitor active playback sessions
  retention_days: 30
```

## 7. Troubleshooting

### Common Issues
1. **Can't connect to camera**
   - Verify network connectivity
   - Check camera credentials
   - Ensure the camera is online

2. **Stream is laggy**
   - Reduce stream quality in settings
   - Check network bandwidth
   - Increase buffer size in config

3. **Web interface is slow**
   - Reduce number of concurrent streams
   - Enable hardware acceleration
   - Check server resources

### Viewing Logs
Server logs are stored in `logs/devices_mcp.log` by default. Enable debug logging for more detailed information:

```yaml
log_level: "DEBUG"
log_file: "/path/to/logs/devices_mcp.log"
```

## Support
For additional help, please open an issue on [GitHub](https://github.com/yourusername/devices-mcp/issues).
