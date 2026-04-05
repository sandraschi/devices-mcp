# Tapo Camera Credentials Guide

## Finding Your Tapo Camera Credentials

After resetting a Tapo camera, the default credentials are typically:

### Default After Reset
- **Username:** `admin`
- **Password:** `admin`

However, **this is not guaranteed** - some cameras may have:
- Different default passwords (like `TPL075526460603` format)
- Password printed on the camera label
- Password in the device manual

### Where to Find Credentials

1. **Camera Label**
   - Check the bottom or back of your camera
   - Look for a sticker with username/password
   - Format might be: `TPL[numbers]` or similar

2. **Tapo App**
   - Open Tapo app → Your Camera
   - Device Settings → Advanced Settings → Local Device Settings
   - Look for "Local User" or "Local Admin Account"
   - This shows the LOCAL username/password (not cloud account)

3. **Device Manual**
   - Check the printed manual or PDF
   - Default credentials should be listed there

4. **After Setup**
   - If you set up the camera through the Tapo app
   - The LOCAL admin password might be different from your cloud account
   - Check: Tapo app → Camera → Advanced → Local Device Settings

### Important: Local vs Cloud Credentials

**Tapo cameras use LOCAL credentials for API access, NOT your cloud account!**

- **Cloud Account:** Used for Tapo app access (email: sandraschipal@hotmail.com)
- **Local Account:** Used for API/local access (usually admin/your-local-password)

These are **separate** - you need to find or set the LOCAL credentials.

## MCP Server Configuration

### Configuration Sources (Hierarchical Priority)

The MCP server loads credentials from multiple sources:

#### 1. Primary: YAML Configuration File
**Location**: `config.yaml` (recommended)
```yaml
# Tapo Cameras
cameras:
  kitchen:
    type: tapo
    host: 192.168.1.100
    username: admin  # Local admin username
    password: your_local_password  # Local admin password
    port: 443

# Tapo Smart Plugs
energy:
  tapo_p115:
    account:
      email: your_cloud_account@example.com
      password: your_cloud_password
    devices:
      - host: 192.168.1.120
        device_id: tapo_p115_living_room
```

#### 2. Secondary: Environment Variables
**Fallback when config missing**:
```bash
TAPO_ACCOUNT_EMAIL=your_email@example.com
TAPO_ACCOUNT_PASSWORD=your_password
TAPO_P115_HOSTS=192.168.1.120,192.168.1.121
```

#### 3. Tertiary: Token Cache Files
**OAuth services**:
- `ring_token.cache` - Ring doorbell OAuth
- `nest_token.cache` - Nest Protect OAuth

### Current Working Configuration (January 2026)

```yaml
# Cameras (ONVIF protocol)
cameras:
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

# Energy devices (Tapo P115 plugs)
energy:
  tapo_p115:
    account:
      email: sandraschipal@hotmail.com
      password: Sec1060ta#
    devices:
      - host: 192.168.0.17
      - host: 192.168.0.137
      - host: 192.168.0.38

# Lighting (Tapo L900)
lighting:
  tapo_lighting:
    account:
      email: sandraschipal@hotmail.com
      password: Sec1060ta#

# External services
ring:
  enabled: true
  email: sandraschipal@hotmail.com
  password: Sec1000ri#
  token_file: ring_token.cache

netatmo:
  enabled: true
  client_id: 6939e5b98080806f1c003668
  client_secret: IyWYPAE9cq28N6HQNHWp3XDdbz
  refresh_token: 5ca3ae420ec7040a008b57dd|a289c1f0899232016582aa5cf52940f9
```

### Authentication Methods Summary

| Service | Auth Method | Credentials From | Status |
|---------|-------------|------------------|---------|
| Tapo Cameras | ONVIF/Local API | Config file | Working |
| Tapo Plugs | Cloud Account API | Config + Env vars | Working |
| Tapo Lighting | Cloud Account API | Config file | Working |
| Ring Doorbell | OAuth + Token Cache | Config + Cache | Working |
| Netatmo Weather | OAuth2 Refresh Token | Config file | Working |
| Home Assistant | Long-lived Access Token | Config file | Working |
| USB Cameras | Direct Device Access | No auth required | Working |

### Setting Local Admin Password

If you haven't set one:

1. Open **Tapo app** → Your Camera
2. Go to **Device Settings** → **Advanced Settings**
3. Find **Local Device Settings** or **Local User Management**
4. Enable **Local Admin Account** (if not already enabled)
5. Set a username (usually `admin`) and password
6. **Write this down** - you'll need it for API access!

### Testing Credentials

Use the test script to check if credentials work:

```powershell
python scripts/test_tapo_connection.py
```

Or manually update the script:
```python
ip = "192.168.0.164"  # Your camera IP
username = "admin"  # Try admin first
password = "admin"  # Try admin first, or password from label/manual
```

### Common Issues

1. **"Invalid authentication"**
   - Wrong username/password
   - Using cloud account instead of local account
   - Password changed but not updated in config

2. **"Temporary Suspension"**
   - Too many failed login attempts
   - Wait 30 minutes or power cycle camera

3. **Can't find local settings in app**
   - Some older Tapo cameras use cloud account for local access
   - Try your cloud account email as username
   - Password might be your cloud password (but often different)

### Next Steps

1. **Check camera label** for default credentials
2. **Check Tapo app** for local admin settings
3. **Test with admin/admin** (common default after reset)
4. **If admin/admin doesn't work**, try:
   - Password from camera label (TPL format)
   - Your cloud password (less common)
   - Check device manual

Once you find the correct credentials, update `config.yaml`:

```yaml
tapo_kitchen:
  type: tapo
  params:
    host: 192.168.0.164
    username: "admin"  # Or username from label/app
    password: "YOUR_ACTUAL_PASSWORD"  # From label/manual/app
    port: 443
    verify_ssl: true
```
