# Nest Protect Setup Guide

## Overview

Nest Protect smoke and CO detectors are integrated via **Home Assistant**, which acts as a bridge for Google OAuth authentication. This provides a secure, reliable connection without requiring direct Google API credentials.

## Configuration Status

Your Nest Protect integration is configured in `config.yaml`:

```yaml
security:
  integrations:
    homeassistant:
      enabled: true
      url: http://localhost:8123
      access_token: "your_long_lived_access_token"
      cache_ttl: 30
```

## Web Dashboard Setup

### Quick Start via Web UI

1. **Access Nest Dashboard**: Navigate to `http://localhost:7777/nest`
2. **Check Status**: The dashboard shows your connection status:
   - 🟢 **Green (Success)**: Connected with devices detected
   - 🟡 **Yellow (Warning)**: Enabled but no devices found
   - 🔴 **Red (Error)**: Disabled or configuration issue
3. **View Devices**: Once connected, all Nest Protect devices appear with:
   - Smoke status (OK/Warning/Emergency)
   - CO status (OK/Warning/Emergency)
   - Battery health
   - Location and model information
4. **Monitor Alerts**: Active alerts are displayed in a dedicated section with color-coded severity

### Web Dashboard Features

The Nest Protect dashboard (`/nest`) provides:

- **Status Card**: Real-time connection status with gradient indicators
- **Setup Instructions**: Step-by-step Home Assistant configuration guide
- **Device Cards**: Visual cards showing smoke/CO status, battery health, location
- **Alert Section**: Color-coded alerts (emergency = red, warning = yellow)
- **Auto-Refresh**: Status updates every 30 seconds
- **Toast Notifications**: User feedback for status changes

## Home Assistant Setup

### Step 1: Install Home Assistant

Ensure Home Assistant is running and accessible. The default URL is `http://localhost:8123`.

### Step 2: Create Long-Lived Access Token

1. Log into Home Assistant
2. Go to **Profile** → **Security** → **Long-Lived Access Tokens**
3. Click **Create Token**
4. Give it a name (e.g., "Devices MCP")
5. Copy the token and add it to `config.yaml`:

```yaml
security:
  integrations:
    homeassistant:
      access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Step 3: Enable Nest Integration in Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Nest**
4. Follow the OAuth flow to connect your Google account
5. Authorize Home Assistant to access your Nest devices

### Step 4: Verify Devices

Once configured, your Nest Protect devices should appear in Home Assistant under **Settings** → **Devices & Services** → **Nest**.

## Programmatic Access (MCP Tools)

### Check Status

```python
security_management(
    action="nest_status"
)
```

### Get All Devices

```python
security_management(
    action="nest_devices"
)
```

### Get Alerts

```python
security_management(
    action="nest_alerts"
)
```

### Get Battery Status

```python
security_management(
    action="nest_battery"
)
```

## Troubleshooting

### "Disabled" Status

If the dashboard shows "Disabled":
- Check that `security.integrations.homeassistant.enabled: true` in `config.yaml`
- Verify Home Assistant is running at the configured URL
- Check that the access token is valid

### "No Devices Found"

If enabled but no devices appear:
- Verify Nest integration is configured in Home Assistant
- Check that devices are visible in Home Assistant's device list
- Ensure the access token has proper permissions
- Check Home Assistant logs for Nest-related errors

### Connection Issues

- Verify Home Assistant URL is correct (default: `http://localhost:8123`)
- Test the access token by visiting `http://localhost:8123/api/` with the token
- Check firewall settings if Home Assistant is on a different machine
- Ensure Home Assistant is accessible from the Devices MCP server

## Integration with Other Systems

Nest Protect integrates with:

- **Security Management**: Comprehensive safety (fire + CO + burglar + water + emergency)
- **Ring Doorbell**: Unified security dashboard
- **Camera Management**: Correlate smoke/CO alerts with camera events
- **Alerts Dashboard**: Centralized alert management

Your Austrian smart home setup now supports comprehensive fire and CO detection! 🔥🚨
