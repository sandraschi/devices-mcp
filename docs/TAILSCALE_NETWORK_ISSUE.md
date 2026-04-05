# Tailscale (Tailnet) and Local Network Access

## Potential Issue: Tailscale Routing Local Traffic

If Tailscale is routing local network traffic through the VPN instead of using the local network directly, this could cause connection issues.

## Your Network Setup

**Your Computer IPs:**
- `10.2.4.197` - Tailscale VPN IP
- `192.168.0.81` - Local network IP ✅
- `100.118.171.110` - Tailscale
- Multiple other interfaces

**Tapo Devices:**
- Kitchen Camera: `192.168.0.164`
- Living Room Camera: `192.168.0.206`
- P115 Plug: `192.168.0.17`

## Good News: P115 Connection Works!

✅ **P115 plug connection succeeded** - This confirms:
- Local network access works
- Tailscale is NOT blocking local traffic
- Devices are accessible on 192.168.0.x network

## Why Cameras Might Be Failing

Since P115 works via Tapo API but cameras don't, the issue is likely:
1. **Authentication method** - Different for cameras vs plugs
2. **pytapo library** - May have compatibility issues with C200
3. **Camera-specific authentication** - Not router/network related

## Tailscale Configuration Check

### 1. **Check Route Table Priority**
Tailscale should NOT route 192.168.0.x through VPN - it should use local network.

### 2. **Allow Local Network Access**
In Tailscale settings:
- Ensure "Allow local network access" is enabled
- Or "Route local traffic" is set appropriately

### 3. **Check Split Tunneling**
If Tailscale is intercepting ALL traffic:
- Configure split tunneling
- Exclude 192.168.0.0/24 from Tailscale routing

## Quick Test: Disable Tailscale Temporarily

To test if Tailscale is the issue:
1. Disconnect from Tailscale temporarily
2. Test camera connection
3. If it works, Tailscale routing is the problem
4. If still fails, it's authentication (not network)

## Current Status

- ✅ **P115 Plug**: Works (confirms network access OK)
- ❌ **Cameras**: Authentication failing (likely not network issue)

Since P115 works, **Tailscale is probably NOT the problem**. The camera authentication issue is likely:
- pytapo library compatibility
- Camera authentication method difference
- Not router/Tailscale related

## Recommendation

**No router/Tailscale changes needed** if:
- ✅ P115 plug works (proves local network access)
- ✅ Can ping camera IPs
- ✅ Port 443 is reachable on cameras

The issue is likely **pytapo authentication**, not network/routing.
