# Tapo Camera Setup Guide

## Important: Local vs Cloud Credentials

**Tapo cameras require LOCAL admin credentials, NOT your cloud account credentials.**

### Finding Your Local Admin Credentials

1. **Open the Tapo app** on your phone
2. **Select your camera** (Kitchen C200)
3. Go to **Device Settings** → **Advanced Settings** → **Local Device Settings**
4. Look for **Local User Management** or **Local Admin Account**
5. You'll see the local username (usually `admin`) and can set/reset the password

### Setting Local Admin Password

If you haven't set a local admin password:
1. Open Tapo app → Your Camera → Device Settings
2. Go to **Advanced** → **Local Device Settings**
3. Enable **Local User** or **Local Admin Account**
4. Set a password (write it down!)

### Current Configuration

```yaml
tapo_camera:
  type: tapo
  params:
    host: 192.168.0.164  # Your kitchen camera IP
    username: "admin"    # Local admin username (usually "admin")
    password: "admin"    # ⚠️ UPDATE: Set your local admin password here
    port: 443
    verify_ssl: true
```

### Security Lockout

If you see "Temporary Suspension: Try again in 1800 seconds":
- The camera locked out due to too many failed login attempts
- Wait 30 minutes before trying again
- Make sure you're using the correct **local admin** credentials

### Testing Connection

After setting your local admin password, test the connection:

```powershell
python scripts/test_tapo_connection.py
```

Or update the script with your local credentials:
```python
username = "admin"  # Local admin username
password = "YOUR_LOCAL_ADMIN_PASSWORD"  # Your local admin password
```

### Common Issues

1. **"Invalid authentication data"**
   - You're using cloud account credentials instead of local admin
   - Use local admin username/password set in the Tapo app

2. **"Temporary Suspension"**
   - Too many failed login attempts
   - Wait 30 minutes or reset the camera

3. **Can't find local admin settings**
   - Some Tapo cameras use the cloud account for local access
   - Try using your cloud account email as username
   - Password might be different from cloud password

### MAC Address

**No, you don't need the MAC address** - only the IP address, local username, and local password are required.
