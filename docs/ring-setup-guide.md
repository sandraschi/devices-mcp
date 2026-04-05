# Ring Doorbell Setup Guide

## Configuration Status ✅ **WORKING**

Your Ring integration is configured and **successfully tested**:

```yaml
ring:
  enabled: true
  email: sandraschipal@hotmail.com
  password: "Sec1000ri#"
  token_file: ring_token.cache
  cache_ttl: 60
```

**Status**: ✅ Connected - 1 doorbell detected ("Front Door", ID: 52772421)

## Web Dashboard Setup

### Quick Start via Web UI

The easiest way to set up Ring is through the web dashboard:

1. **Access Ring Dashboard**: Navigate to `http://localhost:7777/ring`
2. **Check Status**: The dashboard shows your connection status with color-coded cards:
   - 🟢 **Green (Success)**: Connected and ready
   - 🟡 **Yellow (Warning)**: Needs initialization or 2FA
   - 🔴 **Red (Error)**: Configuration issue or disabled
3. **Initialize Connection**: Click the "Initialize Connection" button if not connected
4. **Submit 2FA**: If prompted, enter your 2FA code in the form and click "Submit Code"
5. **View Devices**: Once connected, your Ring doorbells and alarm system will appear automatically

### Web Dashboard Features

The Ring dashboard (`/ring`) provides:

- **Status Card**: Real-time connection status with gradient indicators
- **Setup Instructions**: Step-by-step guidance when not connected
- **2FA Form**: In-page authentication code submission
- **Device Cards**: Visual cards showing battery, WiFi signal, model, firmware
- **Live View**: Direct access to WebRTC live streaming
- **Alarm Controls**: Disarm, Home, and Away mode buttons
- **Recent Events**: Timeline of motion and doorbell events
- **Toast Notifications**: User feedback for all actions

## Programmatic Setup (MCP Tools)

### Step 1: Initialize Ring Client

Use the `ring_management` tool with action `initialize`:

```
ring_management(
    action="initialize",
    email="sandraschipal@hotmail.com",
    password="Sec1000ri#"
)
```

### Step 2: Submit 2FA Code (if required)

If initialization returns `needs_2fa: true`, submit your verification code:

```
ring_management(
    action="2fa",
    code="629622"
)
```

### Step 3: Verify Connection

Check that Ring is working:

```
ring_management(action="status")
```

### Step 4: List Your Doorbells

See your Ring devices:

```
ring_management(action="doorbells")
```

## Available Ring Features

Once connected, you can use:

- **Live View**: `ring_management(action="live_view", device_id="your_doorbell_id")`
- **Recent Events**: `ring_management(action="events", limit=20)`
- **Snapshots**: `ring_management(action="snapshot", device_id="your_doorbell_id")` *(requires Ring Protect subscription)*
- **Alarm Control**: Arm/disarm Ring alarm system
- **Siren Control**: Trigger emergency siren

## Troubleshooting

### If 2FA fails:
- Codes expire quickly - get a fresh code from Ring app
- Make sure you're submitting the code immediately after getting it
- Check that the email/password are correct in config.yaml

### If connection fails:
- Verify your Ring account credentials
- Check if you have Ring Protect subscription (needed for snapshots)
- Try re-initializing: `ring_management(action="initialize")`

### Getting Device IDs:
```python
# List all doorbells to get device_id
result = ring_management(action="doorbells")
# Use the device_id from the response for other commands
```

## Integration with Other Systems

Ring integrates with:
- **Camera Management**: Unified camera control across Tapo + Ring
- **Security Management**: Comprehensive safety (burglar + fire + gas + water + emergency)
- **Home Assistant**: Nest Protect smoke detectors
- **Energy Management**: Smart plugs and power monitoring

Your Austrian smart home setup now supports the most popular security devices! 🏠🔒
