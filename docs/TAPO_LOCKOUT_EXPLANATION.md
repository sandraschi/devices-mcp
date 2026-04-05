# Tapo Camera Lockout Mechanism Explained

## What Happened

When we tried to connect to your kitchen camera (192.168.0.164), we encountered this error:

```
Temporary Suspension: Try again in 1800 seconds
```

## Why It Happened

**Tapo cameras have a built-in security feature that temporarily locks the camera after multiple failed login attempts.**

### Lockout Triggers

1. **Multiple Failed Authentication Attempts**:
   - Camera receives 3-5 incorrect username/password combinations
   - Security system activates temporary lockout

2. **Time Window**:
   - Lockout typically lasts **30 minutes** (1800 seconds)
   - Cannot attempt login during lockout period

3. **What We Did Wrong**:
   - Discovery script scanned many IPs (254 IPs on /24 network)
   - Each IP attempted connection with potentially wrong credentials
   - Multiple rapid attempts triggered the lockout

## Lockout Protection Implemented

We've updated the code to **prevent future lockouts**:

### 1. Single-Attempt Logic
- ✅ Only attempts connection **once per camera**
- ✅ No automatic retries on authentication failures
- ✅ Stops immediately on lockout detection

### 2. Smart Error Detection
- ✅ Recognizes "Temporary Suspension" messages
- ✅ Detects "Invalid authentication" errors
- ✅ Logs specific error types for debugging

### 3. Discovery Script Improvements
- ✅ Checks port 443 first (faster, no auth attempt)
- ✅ Only authenticates if port is open and likely Tapo camera
- ✅ Skips locked-out cameras with warning

### 4. Connection Logic
```python
# Only attempts ONCE - no retries
def create_and_test_tapo():
    try:
        camera = Tapo(host, username, password)
        basic_info = camera.getBasicInfo()  # This authenticates
        return (True, camera, None)
    except Exception as e:
        # Stop immediately on any error
        return (False, None, str(e))
```

## How to Avoid Lockouts

### For Manual Testing
1. **Use correct credentials** - Local admin username/password
2. **Don't retry immediately** - Wait at least 1 minute between attempts
3. **Check Tapo app first** - Verify camera is accessible there
4. **One camera at a time** - Don't test multiple cameras simultaneously

### For Automated Discovery
1. **Port scan first** - Only attempt auth on open port 443
2. **Single attempt per IP** - Never retry on same IP
3. **Rate limiting** - Add delays between different IPs (already implemented)
4. **Stop on lockout** - Skip locked cameras entirely

## Current Status

### Kitchen Camera (192.168.0.164)
- ⚠️ **Currently locked out** - Wait 30 minutes
- ✅ IP and model (C200) confirmed
- ⚠️ Need correct local admin password

### Living Room Camera (192.168.0.206)
- ✅ IP configured
- ⚠️ Need to test with correct credentials (after getting password)
- ✅ Lockout protection enabled

## Next Steps

1. **Wait 30 minutes** for kitchen camera lockout to expire
2. **Get local admin passwords** from Tapo app for both cameras
3. **Update config.yaml** with correct passwords
4. **Test one camera at a time** using `test_tapo_connection.py`
5. **Restart dashboard** to connect cameras

## Lockout Recovery

If you accidentally trigger a lockout:

1. **Wait 30 minutes** - Lockout automatically expires
2. **Or power cycle camera** - Unplug and replug (resets lockout counter)
3. **Or use Tapo app** - App can unlock camera faster than API

The code now prevents this from happening again by:
- Single-attempt authentication
- Immediate error detection
- No retries on failures
- Smart discovery that checks ports first
