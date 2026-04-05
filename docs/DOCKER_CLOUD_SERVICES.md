# Docker Cloud Services Access (Netatmo, Ring, Nest)

## Overview

This document explains how cloud-accessed services (Netatmo, Ring, Nest via Home Assistant) work in Docker and how to configure them properly.

**Note:** Netatmo is a **local weather station** with physical modules, but data access is via **cloud API** (no direct local network access).

## Cloud Services

### ✅ Netatmo Weather Station

**Type:** Local hardware with cloud API access (OAuth-based)
**Status:** ✅ Works in Docker (no special configuration needed)

**Hardware:**
- **Main Indoor Module (NAMain)**: Temperature, humidity, CO₂, noise, pressure
- **Outdoor Module (NAModule1)**: Temperature, humidity (battery-powered)
- **Additional Indoor Modules (NAModule4)**: Extra sensors (e.g., bathroom module)
- Modules communicate wirelessly with main station
- Main station connects to WiFi and uploads to Netatmo cloud

**How it works:**
- Physical modules are **local devices** in your home
- Main station uploads data to Netatmo cloud via WiFi
- Access data through **cloud API** (`api.netatmo.com`) with OAuth 2.0
- Uses refresh tokens for authentication
- No direct local network access to modules (they use Netatmo cloud)
- Token stored in memory (no file needed)

**Important:**
- Physical modules are **local devices** in your home (main station + outdoor module + bathroom module)
- Modules communicate wirelessly with main station
- Main station uploads data to Netatmo cloud via WiFi
- You **must use the cloud API** to access data - modules don't expose a local HTTP/API interface
- No Docker network configuration needed - works via cloud API from any network

**Your Setup:**
- Main Station (NAMain): Indoor module at Stroheckgasse
- Bathroom Module (NAModule4): Additional indoor sensor
- Outdoor Module (NAModule1): If installed

**Configuration:**
```yaml
weather:
  integrations:
    netatmo:
      enabled: true
      client_id: 'your-client-id'
      client_secret: 'your-client-secret'
      refresh_token: 'your-refresh-token'
```

**Architecture:**
```
Physical Hardware (Local):
  ┌─────────────────┐
  │ Main Module     │ (NAMain - Indoor: temp, humidity, CO₂, pressure)
  │ (WiFi)          │
  └────────┬────────┘
           │ Wireless
  ┌────────┴────────┐
  │ Outdoor Module  │ (NAModule1 - Battery-powered)
  │ Bathroom Module │ (NAModule4 - Additional indoor sensor)
  └─────────────────┘
           │
           ▼
  Netatmo Cloud API (api.netatmo.com)
           │
           ▼
  Your Application (via OAuth)
```

**Docker Notes:**
- ✅ Works out of the box - no Docker-specific configuration needed
- ✅ Cloud API accessible from any network (no local network access needed)
- ✅ Refresh token handles authentication automatically
- ✅ Physical modules are local, but data access is via cloud API

---

### ✅ Ring Doorbell

**Type:** Cloud API (email/password auth)
**Status:** ✅ Works in Docker (token caching configured)

**How it works:**
- Uses email/password authentication
- Token cached to file for persistence
- Connects to Ring cloud API (external)
- No local network access required

**Configuration:**
```yaml
ring:
  enabled: true
  email: your-email@example.com
  password: "your-password"
  token_file: ring_token.cache  # Auto-adjusted to /app/tokens in Docker
  cache_ttl: 60
```

**Docker Notes:**
- ✅ Token file automatically stored in `/app/tokens` volume
- ✅ Token persists across container restarts
- ✅ Cloud API accessible from any network

**Token File Location:**
- **Host:** `ring_token.cache` (current directory)
- **Docker:** `/app/tokens/ring_token.cache` (mounted volume)

---

### ✅ Nest Protect (via Home Assistant)

**Type:** Cloud API via Home Assistant bridge
**Status:** ✅ Works in Docker (URL auto-detection)

**Why Home Assistant?**
- Google blocks direct OAuth for third-party apps
- Home Assistant has verified Google OAuth application
- HA acts as a bridge to Nest API

**How it works:**
1. Home Assistant authenticates with Google (verified OAuth)
2. HA exposes Nest devices via REST API
3. Devices MCP connects to HA API
4. HA proxies requests to Nest cloud API

**Configuration:**
```yaml
security:
  integrations:
    homeassistant:
      enabled: true
      url: http://localhost:8123  # Auto-adjusted in Docker
      access_token: "your-long-lived-token"
      cache_ttl: 30
```

**Docker URL Auto-Detection:**

The Home Assistant client automatically detects Docker and adjusts URLs:

1. **If Home Assistant is on host:**
   - Config: `http://localhost:8123`
   - Docker uses: `http://host.docker.internal:8123`
   - ✅ Works automatically

2. **If Home Assistant is in Docker (same network):**
   - Set environment variable: `HOMEASSISTANT_SERVICE_NAME=homeassistant`
   - Config: `http://localhost:8123`
   - Docker uses: `http://homeassistant:8123`
   - ✅ Works via Docker service name

3. **If Home Assistant is in Docker (different network):**
   - Config: `http://homeassistant:8123` (service name)
   - Or: `http://host.docker.internal:8123` (if HA exposes port to host)
   - ✅ Works with explicit service name

**Docker Compose Configuration:**

**Option 1: Home Assistant on Host**
```yaml
# No changes needed - auto-detects and uses host.docker.internal
environment:
  - CONTAINER=yes
```

**Option 2: Home Assistant in Docker (Same Network)**
```yaml
networks:
  - myhomecontrol
  - homeassistant  # Connect to HA network

environment:
  - CONTAINER=yes
  - HOMEASSISTANT_SERVICE_NAME=homeassistant
```

**Option 3: Home Assistant in Docker (Different Network)**
```yaml
# In config.yaml, use service name directly:
security:
  integrations:
    homeassistant:
      url: http://homeassistant:8123  # Docker service name
```

**Getting Home Assistant Access Token:**

1. Open Home Assistant: `http://localhost:8123`
2. Click your profile icon (bottom left)
3. Go to **Security** tab
4. Scroll to **Long-Lived Access Tokens**
5. Click **Create Token**
6. Name it "devices-mcp"
7. **Copy token immediately** (won't be shown again!)

---

## Network Connectivity

### Cloud Services (Netatmo, Ring)

✅ **No special network configuration needed**
- Cloud APIs accessible from any network
- Docker containers can reach internet by default
- No firewall rules needed

### Home Assistant (Nest Bridge)

**If HA is on host:**
- Container uses `host.docker.internal:8123`
- ✅ Works automatically with current configuration

**If HA is in Docker:**
- Option 1: Connect to same Docker network
- Option 2: Use service name in config URL
- Option 3: Expose HA port to host, use `host.docker.internal`

---

## Token Persistence

### Ring Token

**Location:**
- Host: `ring_token.cache` (current directory)
- Docker: `/app/tokens/ring_token.cache` (mounted volume)

**Persistence:**
- ✅ Token persists across container restarts
- ✅ Volume mounted in docker-compose.yml
- ✅ Auto-created if doesn't exist

### Nest Token (via Home Assistant)

**Type:** Long-lived access token (stored in config.yaml)
- ✅ Persists in mounted config file
- ✅ No separate token file needed
- ✅ Token valid for 10 years (default HA token expiry)

---

## Troubleshooting

### Netatmo: "Authentication failed"

**Check:**
- Refresh token is valid (not expired)
- Client ID and secret are correct
- Network connectivity to `api.netatmo.com`

**Fix:**
- Re-authenticate to get new refresh token
- Check firewall allows HTTPS (port 443)

### Ring: "Token file not found" or "Authentication failed"

**Check:**
```powershell
# In Docker, check token file exists
docker exec myhomecontrol-app ls -la /app/tokens/

# Check token file permissions
docker exec myhomecontrol-app cat /app/tokens/ring_token.cache
```

**Fix:**
- Token file auto-created on first authentication
- Ensure `/app/tokens` volume is mounted
- Check volume permissions

### Home Assistant: "Cannot connect to Home Assistant"

**Check:**
```powershell
# Test connectivity from container
docker exec myhomecontrol-app curl http://host.docker.internal:8123/api/

# Or if using service name
docker exec myhomecontrol-app curl http://homeassistant:8123/api/
```

**Fix:**

1. **If HA is on host:**
   - Verify HA is running: `Get-NetTCPConnection -LocalPort 8123`
   - Check URL in config: should be `http://localhost:8123` (auto-adjusted)
   - Verify `host.docker.internal` resolves in container

2. **If HA is in Docker:**
   - Ensure both containers on same network
   - Set `HOMEASSISTANT_SERVICE_NAME` environment variable
   - Or use service name directly in config URL

3. **Check access token:**
   - Verify token is valid in HA
   - Token should start with `eyJ...` (JWT format)
   - Create new token if expired

### Home Assistant: "401 Unauthorized"

**Check:**
- Access token is correct in config.yaml
- Token hasn't been revoked in HA
- Token format is correct (no extra spaces)

**Fix:**
- Create new long-lived access token in HA
- Update config.yaml with new token
- Restart container

---

## Configuration Examples

### Complete Docker Setup (HA on Host)

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - CONTAINER=yes
    volumes:
      - app_tokens:/app/tokens
```

```yaml
# config.yaml
ring:
  enabled: true
  email: your-email@example.com
  password: "your-password"
  token_file: ring_token.cache  # Auto → /app/tokens/ring_token.cache

weather:
  integrations:
    netatmo:
      enabled: true
      refresh_token: "your-refresh-token"

security:
  integrations:
    homeassistant:
      enabled: true
      url: http://localhost:8123  # Auto → host.docker.internal:8123
      access_token: "your-ha-token"
```

### Complete Docker Setup (HA in Docker)

```yaml
# docker-compose.yml
services:
  app:
    networks:
      - myhomecontrol
      - homeassistant
    environment:
      - CONTAINER=yes
      - HOMEASSISTANT_SERVICE_NAME=homeassistant
```

```yaml
# config.yaml
security:
  integrations:
    homeassistant:
      enabled: true
      url: http://localhost:8123  # Auto → homeassistant:8123
      access_token: "your-ha-token"
```

---

## Summary

| Service | Type | Docker Config | Notes |
|---------|------|---------------|-------|
| **Netatmo** | Local hardware + Cloud API | ✅ None needed | Physical modules local, access via cloud API |
| **Ring** | Cloud API | ✅ Token volume | Auto-adjusted path |
| **Nest (via HA)** | Cloud via HA | ✅ URL auto-detect | Auto-adjusts localhost |

**All cloud services work in Docker with minimal or no configuration changes!** ✅
