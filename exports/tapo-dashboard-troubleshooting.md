# Devices MCP Dashboard External Access Issue - Windows Firewall Blocking

**Type:** Troubleshooting
**Date:** 2025-10-20
**Permalink:** troubleshooting/devices-mcp-dashboard-external-access-issue-windows-firewall-blocking

**Tags:** networking, windows-firewall, devices-mcp, dashboard, troubleshooting, external-access, tailscale, fastapi, port-7777, system-administration

## Problem Description

The Devices MCP dashboard was accessible via Tailscale (`goliath:7777`) but not via external IP address (`213.47.34.131:7777`). The server was correctly configured to bind to `0.0.0.0:7777` but Windows Firewall was blocking incoming connections.

## Root Cause Analysis

- **Server Configuration**: ✅ Correctly configured to bind to `0.0.0.0:7777`
- **Network Binding**: ✅ Server listening on all interfaces (`netstat` confirmed `TCP 0.0.0.0:7777 LISTENING`)
- **Tailscale Access**: ✅ Working (bypasses local firewall via virtual network)
- **External IP Access**: ❌ Blocked by Windows Firewall

## Technical Details

- **Server**: Devices MCP FastAPI web server
- **Port**: 7777 (configurable)
- **Host Binding**: `0.0.0.0` (correct for external access)
- **Firewall Issue**: Windows Defender Firewall blocking TCP port 7777
- **Error**: No firewall rule existed for the application

## Configuration Files

- **Main Config**: `config.yaml` - `web.host: "0.0.0.0"` ✅
- **Model Config**: `src/devices_mcp/config/models.py` - `WebUISettings.host: "0.0.0.0"` ✅
- **Server Code**: `src/devices_mcp/web/server.py` - Uses config host setting ✅

## Solutions Provided

### Option 1: Add Windows Firewall Rule (Recommended)

```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="Devices MCP Dashboard" dir=in action=allow protocol=TCP localport=7777
```

### Option 2: Windows Firewall GUI

1. Windows Defender Firewall with Advanced Security
2. Inbound Rules → New Rule → Port → TCP → Specific ports: 7777
3. Allow connection → Apply to all profiles
4. Name: "Devices MCP Dashboard"

### Option 3: Temporarily Disable Firewall

Windows Security → Firewall & network protection → Turn off Windows Defender Firewall

### Option 4: Alternative Port

Try different ports that might already be open (e.g., 8080, 3000)

## Network Architecture

- **Tailscale**: Virtual network bypasses local firewall ✅
- **External IP**: Direct access through Windows Firewall ❌
- **Local Access**: Works via localhost/127.0.0.1 ✅

## Troubleshooting Commands Used

```powershell
# Check if server is listening
netstat -an | findstr :7777

# Check existing firewall rules
netsh advfirewall firewall show rule name="Devices MCP" dir=in

# Add firewall rule (requires admin)
netsh advfirewall firewall add rule name="Devices MCP Dashboard" dir=in action=allow protocol=TCP localport=7777
```

## Key Learning Points

1. **Tailscale vs External IP**: Tailscale creates a virtual network that bypasses local firewall rules
2. **Windows Firewall**: Blocks incoming connections by default, even when server binds to 0.0.0.0
3. **Server Configuration**: Was correct - the issue was purely firewall-related
4. **Network Debugging**: Always check both server binding AND firewall rules for external access issues

## Status

- ✅ **Root Cause Identified**: Windows Firewall blocking port 7777
- ✅ **Solution Provided**: Multiple firewall configuration options
- 🔄 **Action Required**: User needs to implement firewall rule (requires admin privileges)

## Related Files

- `start.py` - Dashboard startup script
- `src/devices_mcp/web/server.py` - Web server implementation
- `config.yaml` - Configuration file
- `src/devices_mcp/config/models.py` - Configuration models
