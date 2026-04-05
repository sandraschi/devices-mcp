# MCP Server Status & Authentication Configuration

## Current Status (January 2026)

MCP Server: Fully operational with Cursor IDE integration
FastMCP Version: 3.1 (latest)
Hardware Integration: 8 different device types configured
Authentication: Multiple auth methods working simultaneously

## Server Configuration Sources

The MCP server gets IP addresses, usernames, passwords, and authentication credentials from multiple hierarchical sources:

### 1. Primary: YAML Configuration Files
Location: config.yaml (highest priority)
Search Order:
- /app/config.yaml (Docker container)
- ~/.config/devices-mcp/config.yaml (user home)
- Repository config.yaml
- Current directory

### 2. Secondary: Environment Variables
Fallback when config missing:
TAPO_ACCOUNT_EMAIL=sandraschipal@hotmail.com
TAPO_ACCOUNT_PASSWORD=Sec1060ta#
TAPO_P115_HOSTS=192.168.0.17,192.168.0.137,192.168.0.38

MCP Control
TAPO_MCP_SKIP_HARDWARE_INIT=true
TAPO_MCP_LAZY_INIT=true

### 3. Tertiary: Token/Cache Files
OAuth persistence:
- ring_token.cache - Ring OAuth tokens
- nest_token.cache - Nest OAuth tokens

## Current Authentication Configuration

### Cameras (4 configured)
cameras:
  tapo_kitchen:
    type: onvif
    host: 192.168.0.164
    auth_method: ONVIF
    credentials: Configured

  tapo_living_room:
    type: onvif
    host: 192.168.0.206
    auth_method: ONVIF
    credentials: Configured

  usb_camera_1:
    type: microscope
    auth_method: Direct device access
    credentials: Not required

  usb_camera_2_microscope:
    type: webcam
    auth_method: Direct device access
    credentials: Not required

### Energy Devices (3 Tapo P115 plugs)
energy:
  tapo_p115:
    account:
      email: sandraschipal@hotmail.com
      password: Configured
    devices:
      - host: 192.168.0.17 (Aircon)
      - host: 192.168.0.137 (Kitchen Zojirushi)
      - host: 192.168.0.38 (Server)

### Lighting Systems
lighting:
  philips_hue:
    bridge_ip: 192.168.0.83
    username: API Key configured
    # HomeAware motion detection available with Bridge Pro (BSB002)
    # Automatically enabled when Bridge Pro is detected

  tapo_lighting:
    account:
      email: sandraschipal@hotmail.com
      password: Configured
    devices:
      - host: 192.168.0.174 (Lightstrip L900)

### External Services
ring:
  enabled: true
  email: sandraschipal@hotmail.com
  password: Configured
  token_file: ring_token.cache

netatmo:
  enabled: true
  client_id: Configured
  client_secret: Configured
  refresh_token: OAuth token

home_assistant:
  enabled: true
  url: http://localhost:8123
  access_token: Long-lived token

## Authentication Methods by Service

| Service | Auth Method | Credentials From | Status |
|---------|-------------|------------------|---------|
| Tapo Cameras | ONVIF Protocol | Config file | Working |
| Tapo Plugs | Tapo Account API | Config + Env vars | Working |
| Hue Bridge | Philips Hue API | Config file | Working |
| Tapo Lighting | Tapo Account API | Config file | Working |
| Ring Doorbell | OAuth + Cache | Config + Token file | Working |
| Netatmo Weather | OAuth2 Refresh Token | Config file | Working |
| Home Assistant | Long-lived Access Token | Config file | Working |
| USB Cameras | Direct Device Access | No auth required | Working |

## Configuration Loading Priority

1. YAML config file (highest - current working method)
2. Environment variables (fallback)
3. Token cache files (OAuth persistence)
4. Built-in defaults (minimal fallback)

## MCP Server Operational Status

- Hardware Types: 8 different integrations active
- Cameras: 4 configured (2 ONVIF, 2 USB)
- Smart Devices: 4 Tapo plugs + 1 Tapo lightstrip
- External APIs: Ring, Netatmo, Home Assistant all connected
- Cursor IDE: Fully integrated
- Web Dashboard: Operational at localhost:7777

## Security Notes

- All credentials stored in local config.yaml
- OAuth tokens cached securely in token files
- No credentials transmitted in logs
- Environment variables used for sensitive fallbacks
- Configuration files excluded from version control

## Configuration File Structure

The config.yaml follows a hierarchical structure:
- Server settings: host, port, logging, storage
- Device sections: cameras, energy, lighting, etc.
- Integration settings: external service configurations
- Security settings: authentication and access control

This multi-source configuration system provides flexibility while maintaining security and ease of management.
