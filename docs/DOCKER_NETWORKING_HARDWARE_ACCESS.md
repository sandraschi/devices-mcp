# Docker Networking for Hardware Access

## Overview

This document explains how the dockerized Devices MCP platform accesses hardware devices (cameras, Hue lights, weather stations, smart plugs) on the local network.

## Network Architecture

### Device Locations
- **Cameras**: ONVIF cameras on `192.168.0.x` network (e.g., `192.168.0.164`, `192.168.0.206`)
- **Hue Bridge**: `192.168.0.83`
- **Tapo P115 Plugs**: `192.168.0.17`, `192.168.0.137`, `192.168.0.38`
- **Netatmo Weather**: Cloud API (no local IP needed)
- **Ring Doorbell**: Cloud API (no local IP needed)

### Docker Network Configuration

The container uses a **bridge network** that allows access to the host's local network:

```yaml
networks:
  myhomecontrol:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "true"      # Inter-container communication
      com.docker.network.bridge.enable_ip_masquerade: "true"  # NAT for external access
    ipam:
      config:
        - subnet: 172.20.0.0/16  # Custom subnet
```

## How It Works

### Windows Docker Desktop

On Windows Docker Desktop, containers in bridge networks **can access the host network** by default:

1. **Bridge Network**: Container gets IP in `172.20.0.0/16` subnet
2. **Host Gateway**: `host.docker.internal` resolves to host machine
3. **LAN Access**: Container can reach `192.168.0.x` devices through host's network gateway
4. **NAT**: Docker Desktop handles NAT translation automatically

### Linux Docker

On Linux, containers can access host network devices through:
- Bridge network (default) - works like Windows
- Host network mode (`network_mode: host`) - direct access (not available on Windows)

## Configuration

### DNS Resolution

The container uses multiple DNS servers for reliable device resolution:

```yaml
dns:
  - 8.8.8.8   # Google DNS
  - 1.1.1.1   # Cloudflare DNS
```

### Extra Hosts

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"  # Access to host machine
```

## Connectivity Testing

The hardware initialization module automatically tests network connectivity when running in Docker:

```
[NETWORK] Testing connectivity to 5 device(s)...
[NETWORK] ✅ Kitchen Cam (camera): Port 2020 reachable
[NETWORK] ✅ Living Room Cam (camera): Port 2020 reachable
[NETWORK] ✅ Hue Bridge (hue_bridge): Port 80 reachable
[NETWORK] ✅ Aircon (tapo_plug): Port 443 reachable
[NETWORK] ✅ Kitchen Zojirushi (tapo_plug): Port 443 reachable
[NETWORK] All 5 device(s) reachable from container
```

## Troubleshooting

### Issue: Devices Not Reachable from Container

**Symptoms:**
- Hardware initialization shows "No devices reachable"
- Camera connections fail
- Hue bridge not found

**Solutions:**

1. **Check Docker Network Configuration**
   ```powershell
   docker network inspect myhomecontrol
   ```
   Verify `enable_ip_masquerade` is `true`

2. **Test Connectivity from Container**
   ```powershell
   docker exec -it myhomecontrol-app ping 192.168.0.83
   docker exec -it myhomecontrol-app curl http://192.168.0.83/api/config
   ```

3. **Check Windows Firewall**
   - Ensure Docker Desktop is allowed through firewall
   - Check if firewall is blocking container → host network traffic

4. **Verify Router Settings**
   - Ensure AP isolation is disabled
   - Check if router blocks inter-device communication
   - Verify devices are on same subnet (192.168.0.x)

5. **Check DNS Resolution**
   ```powershell
   docker exec -it myhomecontrol-app nslookup 192.168.0.83
   ```

### Issue: USB Webcam Not Accessible

**Problem:** USB webcams don't work in Docker on Windows.

**Solution:**
- Use network cameras (Tapo/Ring/Nest) instead
- On Linux, map USB device: `devices: ["/dev/video0:/dev/video0"]`
- Windows Docker Desktop doesn't support USB passthrough

### Issue: Port Conflicts

**Problem:** Container can't bind to port 7777.

**Solution:**
```yaml
ports:
  - "7778:7777"  # Use different host port
```

## Network Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Host Network                          │
│                  192.168.0.0/24                         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Camera   │  │  Hue     │  │  Tapo    │             │
│  │ 192.168. │  │  Bridge  │  │  Plugs   │             │
│  │ 0.164    │  │ 192.168. │  │ 192.168. │             │
│  └──────────┘  │ 0.83     │  │ 0.17/137 │             │
│                └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                        ▲
                        │ (NAT/Routing)
                        │
┌─────────────────────────────────────────────────────────┐
│              Docker Bridge Network                       │
│                 172.20.0.0/16                           │
│                                                          │
│  ┌──────────────────────────────────────┐              │
│  │  myhomecontrol-app (Container)       │              │
│  │  IP: 172.20.0.2                      │              │
│  │                                      │              │
│  │  • Camera Manager                    │              │
│  │  • Hue Client                        │              │
│  │  • Tapo Plug Manager                 │              │
│  │  • Netatmo Client                    │              │
│  └──────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

## Best Practices

1. **Use Static IPs**: Configure devices with static IPs in router for reliability
2. **Test Connectivity**: Check hardware initialization logs for connectivity status
3. **Monitor Logs**: Watch for network errors in container logs
4. **Firewall Rules**: Ensure Docker Desktop has firewall exceptions
5. **Network Isolation**: Don't enable AP isolation on router

## Verification Commands

```powershell
# Check container network
docker network inspect myhomecontrol

# Test device connectivity from container
docker exec myhomecontrol-app python -c "import socket; s=socket.socket(); s.settimeout(2); print('OK' if s.connect_ex(('192.168.0.83', 80)) == 0 else 'FAIL'); s.close()"

# Check container IP
docker exec myhomecontrol-app hostname -I

# View network connectivity test results
docker logs myhomecontrol-app | Select-String "NETWORK"
```

## Cloud Services

For cloud-based services (Netatmo, Ring, Nest via Home Assistant), see:
- **[Docker Cloud Services Access Guide](DOCKER_CLOUD_SERVICES.md)** - Complete guide for Netatmo, Ring, and Nest

**Quick Summary:**
- ✅ **Netatmo**: Works out of box (cloud API)
- ✅ **Ring**: Token caching configured (cloud API)
- ✅ **Nest (via HA)**: URL auto-detection for Docker

## References

- [Docker Networking Documentation](https://docs.docker.com/network/)
- [Windows Docker Desktop Networking](https://docs.docker.com/desktop/networking/)
- [Bridge Network Driver](https://docs.docker.com/network/drivers/bridge/)
- [Docker Cloud Services Access](DOCKER_CLOUD_SERVICES.md) - Netatmo, Ring, Nest configuration
