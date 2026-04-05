# Tapo C200 Setup Required

## Important: Camera Must Be Set Up in App First

**Newer Tapo cameras (like C200) do NOT have default credentials.** After factory reset, you **must** set up the camera through the Tapo app before you can access it via API.

## Setup Steps

### 1. Open Tapo App
- Launch the Tapo app on your phone
- Log in with your TP-Link account (sandraschipal@hotmail.com)

### 2. Add Camera
- Tap the **"+"** icon to add a new device
- Select **"Cameras"** → Choose **"Tapo C200"**
- Follow on-screen instructions:
  - Scan QR code on camera (or enter serial number)
  - Connect camera to your Wi-Fi network
  - Complete initial setup

### 3. Set Camera Account (Local Credentials)
After adding the camera:

1. Tap on your camera in the app
2. Tap the **gear icon** (Settings)
3. Go to **"Advanced Settings"**
4. Select **"Camera Account"** or **"Local Device Settings"**
5. **Create a username and password** for local API access
   - Username: Usually `admin` (or custom)
   - Password: Set a secure password (write this down!)

### 4. Use Credentials for API

After setting up the camera account, use those credentials in `config.yaml`:

```yaml
tapo_kitchen:
  type: tapo
  params:
    host: 192.168.0.164
    username: "admin"  # Or username you set in app
    password: "YOUR_PASSWORD"  # Password you set in app
    port: 443
    verify_ssl: true
```

## Important Notes

- **No default credentials** - Camera has no username/password until set up in app
- **Camera Account ≠ Cloud Account** - These are separate credentials
- **Camera Account = Local API access** - Used for third-party apps/API
- **Cloud Account = App access** - Used for Tapo app (your email/password)

## If Camera is Locked Out

1. **Power cycle** the camera (unplug, wait 10 seconds, plug back in)
2. **Wait 30 minutes** for automatic lockout expiration
3. **Then set up in app** - Don't try API access until after app setup

## After Setup

Once camera is set up in app and you've created the Camera Account:

1. Get the username/password from: Tapo app → Camera → Advanced → Camera Account
2. Update `config.yaml` with those credentials
3. Test connection: `python scripts/test_tapo_connection.py`

The camera will be accessible via API once these steps are complete.
