# Router Requirements for Tapo Devices

## Quick Answer: **Usually NO router changes needed** for local network access

If devices are on the **same local network** as your computer, router changes are typically **NOT required**. However, there are some exceptions.

## When Router Changes ARE Needed

### 1. **Network Segmentation / VLANs**
- **Problem**: Devices isolated on different VLANs/subnets
- **Solution**:
  - Ensure cameras/plugs are on same network as your computer
  - Allow inter-VLAN communication if using VLANs
  - Check subnet: `ipconfig` (Windows) or `ip addr` (Linux)

### 2. **Firewall Blocking Local Traffic**
- **Problem**: Router firewall blocking device communication
- **Solution**:
  - Allow local network traffic (LAN-to-LAN)
  - Don't block ports: 443 (cameras), 9999 (plugs - Kasa), 2020 (ONVIF)
  - Some routers have "AP isolation" - disable it

### 3. **Port Blocking**
- **Problem**: Router blocking specific ports
- **Ports Used**:
  - **Tapo Cameras**: Port 443 (HTTPS)
  - **Tapo Plugs (Kasa)**: Port 9999 (Kasa protocol)
  - **Tapo Plugs (Tapo API)**: Uses HTTPS (port 443)
  - **ONVIF**: Port 2020 (if enabled)
- **Solution**: Ensure these ports are not blocked for local traffic

### 4. **AP Isolation / Client Isolation**
- **Problem**: Router setting preventing devices from talking to each other
- **Solution**:
  - Disable "AP Isolation" or "Client Isolation" in router settings
  - This allows devices on Wi-Fi to communicate with each other

### 5. **mDNS / Bonjour Not Working**
- **Problem**: Device discovery not working
- **Solution**:
  - Enable mDNS/Bonjour in router (usually enabled by default)
  - Some routers call this "mDNS reflection" or "Bonjour"

## When Router Changes are NOT Needed

### ✅ Local Network Access
- Devices on same network/subnet (e.g., all on 192.168.0.x or 10.2.4.x)
- Router allows local traffic (default behavior)
- No firewall blocking local communication

### ✅ Static IP Assignment
- You've already set static IPs (good!)
- Router accepts static IP assignments (most do)

### ✅ Third-Party Compatibility
- This is a **camera/app setting**, not router setting
- Enabled in Tapo app (already done)

## Current Status Check

### Your Network:
- **Kitchen Camera**: 192.168.0.164 (static IP enabled)
- **Living Room Camera**: 192.168.0.206 (static IP enabled)
- **P115 Plug**: 192.168.0.17 (static IP enabled)

### Network Analysis:
If devices are on **192.168.0.x** but your computer is on a **different subnet** (like 10.2.4.x), that's the problem!

**Check your computer's IP:**
```powershell
ipconfig
```

Look for "IPv4 Address" - it should be on same network as devices (192.168.0.x)

## Common Router Settings to Check

### 1. **Client Isolation / AP Isolation**
- **Location**: Router settings → Wireless → Advanced
- **Action**: **DISABLE** if you want devices to communicate locally

### 2. **Firewall Rules**
- **Location**: Router settings → Firewall
- **Action**: Ensure "Allow Local Traffic" or similar is enabled

### 3. **Port Forwarding**
- **NOT needed** for local access (only for remote/internet access)

### 4. **UPnP / mDNS**
- **Location**: Router settings → Advanced → UPnP/mDNS
- **Action**: **ENABLE** for better device discovery

## What to Check First

1. **Same Network?**
   ```powershell
   ipconfig
   ```
   - Your computer's IP should match device network (192.168.0.x)

2. **Can You Ping?**
   ```powershell
   ping 192.168.0.164
   ping 192.168.0.206
   ping 192.168.0.17
   ```
   - All should respond if devices are online

3. **Port Accessible?**
   - Camera port 443: Should be open if camera is online
   - Plug port 9999: Might be closed if using Tapo API instead

## Summary

**Most likely: NO router changes needed** if:
- ✅ All devices on same network
- ✅ Can ping the devices
- ✅ Router allows local traffic (default)

**Router changes needed if:**
- ❌ Devices on different subnets/VLANs
- ❌ AP Isolation enabled
- ❌ Firewall blocking local ports
- ❌ Can't ping devices from your computer

## Next Steps

1. Check your computer's IP address (should match device network)
2. Verify you can ping the devices
3. Check router for AP Isolation setting
4. If still failing, router firewall might be blocking
