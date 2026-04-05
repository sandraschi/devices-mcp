# MCP Server Configuration & Authentication Guide

## Overview

The Devices MCP server supports comprehensive hardware integration with multiple authentication methods. This guide documents how the server obtains IP addresses, usernames, passwords, and authentication credentials for various devices and services.

## Configuration Sources (Hierarchical Priority)

### 1. Primary: YAML Configuration Files
**Location**: `config.yaml` (highest priority)
**Search Order**:
- `/app/config.yaml` (Docker container)
- `~/.config/devices-mcp/config.yaml` (user home directory)
- Repository root `config.yaml`
- Current directory

### 2. Secondary: Environment Variables
**Fallback when config file doesn't specify**:
```bash
# Tapo Account (for plugs and lighting)
TAPO_ACCOUNT_EMAIL=your_email@example.com
TAPO_ACCOUNT_PASSWORD=your_password
TAPO_P115_HOSTS=192.168.1.120,192.168.1.121,192.168.1.122

# MCP Server Control
TAPO_MCP_SKIP_HARDWARE_INIT=true
TAPO_MCP_LAZY_INIT=true
TAPO_MCP_TOOL_MODE=production
```

### 3. Tertiary: Token/Cache Files
**Persistent OAuth authentication**:
- `ring_token.cache` - Ring doorbell OAuth tokens
- `nest_token.cache` - Nest Protect OAuth tokens

### 4. Built-in Defaults
**Minimal fallback configuration** when nothing else is found.

## Current Working Configuration (January 2026)

### Cameras (4 configured)
```yaml
cameras:
  # ONVIF-based Tapo cameras
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

  # USB cameras (no auth required)
  usb_camera_1:
    type: microscope
    device_id: 0
    resolution: "640x480"
    fps: 30

  usb_camera_2:
    type: webcam
    device_id: 1
    resolution: "1920x1080"
    fps: 30
```

### Energy Devices (3 Tapo P115 Smart Plugs)
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
        location: Living Room
      - host: 192.168.0.137
        device_id: tapo_p115_kitchen
        name: Kitchen Zojirushi
        location: Kitchen
      - host: 192.168.0.38
        device_id: tapo_p115_server
        name: Server
        location: Server Room
```

### Lighting Systems
```yaml
lighting:
  # Philips Hue Bridge
  philips_hue:
    bridge_ip: 192.168.0.83
    username: J1A3OQ1OMzJDtidSNQWWGmCBuAxZC3lxEjT9qnVc

  # Tapo Lighting
  tapo_lighting:
    account:
      email: sandraschipal@hotmail.com
      password: Sec1060ta#
    devices:
      - host: 192.168.0.174
        device_id: tapo_l900_lightstrip
        name: Lightstrip L900
        location: Living Room
```

### External Services
```yaml
# Ring Doorbell
ring:
  enabled: true
  email: sandraschipal@hotmail.com
  password: Sec1000ri#
  token_file: ring_token.cache

# Netatmo Weather Station
weather:
  integrations:
    netatmo:
      enabled: true
      client_id: 6939e5b98080806f1c003668
      client_secret: IyWYPAE9cq28N6HQNHWp3XDdbz
      refresh_token: 5ca3ae420ec7040a008b57dd|a289c1f0899232016582aa5cf52940f9

# Home Assistant Integration
security_integrations:
  homeassistant:
    enabled: true
    url: http://localhost:8123
    access_token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmZjZhNzU4NTE5ODk0OWRhYTNlNWQzNzcxYjE4MzA5NCIsImlhdCI6MTc2NDM3NDYxMiwiZXhwIjoyMDc5NzM0NjEyfQ.sbpnoqFypKnt7hYB-FHHrFxVVTrekacJvYcXGF1nqnY
```

## Authentication Methods by Service

| Service Type | Authentication Method | Credentials From | Status |
|--------------|----------------------|------------------|---------|
| **Tapo Cameras** | ONVIF Protocol | Config file (local admin) | ✅ Working |
| **Tapo Smart Plugs** | Cloud Account API | Config file + Env vars | ✅ Working |
| **Philips Hue** | Bridge API Key | Config file | ✅ Working |
| **Tapo Lighting** | Cloud Account API | Config file | ✅ Working |
| **Ring Doorbell** | OAuth + Token Cache | Config + Cache file | ✅ Working |
| **Netatmo Weather** | OAuth2 Refresh Token | Config file | ✅ Working |
| **Home Assistant** | Long-lived Access Token | Config file | ✅ Working |
| **USB Cameras** | Direct Device Access | No authentication | ✅ Working |

## Configuration Loading Priority

1. **YAML config file** (highest priority - recommended)
2. **Environment variables** (fallback)
3. **Token cache files** (OAuth persistence)
4. **Built-in defaults** (minimal fallback)

## Security Considerations

- **Local Storage**: All credentials stored in local `config.yaml`
- **OAuth Tokens**: Cached securely in token files (not in config)
- **Log Safety**: No credentials transmitted in logs
- **Environment Variables**: Used for sensitive fallbacks
- **Version Control**: Configuration files excluded from Git

## Service-Specific Authentication Details

### Tapo Cameras (ONVIF)
- **Local Admin Account**: Separate from cloud account
- **Default Username**: `admin`
- **Password**: Set during initial setup or reset
- **Protocol**: ONVIF over HTTP/HTTPS

### Tapo Smart Plugs & Lighting
- **Cloud Account**: Uses Tapo app account
- **API Access**: Requires cloud authentication
- **Device Discovery**: Automatic via cloud API

### Ring Doorbell
- **OAuth Flow**: Initial email/password → OAuth token
- **Token Persistence**: Cached in `ring_token.cache`
- **2FA Support**: Handles two-factor authentication

### Netatmo Weather
- **OAuth2**: Client ID/Secret + Refresh Token
- **Token Refresh**: Automatic renewal
- **Home ID**: Links to specific weather station

### Home Assistant
- **Long-lived Token**: Generated in HA web interface
- **Bearer Authentication**: HTTP Authorization header
- **API Access**: Full REST API access

## Configuration File Structure

The `config.yaml` follows a hierarchical structure:

```yaml
# Server configuration
host: 0.0.0.0
port: 8080
debug: false

# Device sections
cameras: {...}
energy: {...}
lighting: {...}

# External integrations
ring: {...}
weather: {...}
security_integrations: {...}

# System settings
logging: {...}
storage: {...}
```

## Troubleshooting Configuration Issues

### Common Issues
1. **"No cameras configured"**: Check `cameras` section in config.yaml
2. **"Authentication failed"**: Verify credentials match device settings
3. **"Connection timeout"**: Check IP addresses and network connectivity
4. **"Token expired"**: OAuth tokens may need refresh

### Debug Commands
```bash
# Check current configuration
python -c "from devices_mcp.config import get_config; import json; print(json.dumps(get_config(), indent=2))"

# Test MCP server startup
python -m devices_mcp.cli_v2 --debug
```

### Configuration Validation
- Use `python -c "from devices_mcp.config import get_model; print('Config loaded successfully')"` to test
- Check logs for configuration errors during startup
- Verify network connectivity to configured devices

## Multi-Source Configuration Benefits

This hierarchical approach provides:
- **Flexibility**: Multiple ways to provide credentials
- **Security**: Sensitive data can be sourced from secure locations
- **Deployment Options**: Environment-specific configurations
- **Fallback Safety**: System continues working if primary config unavailable
