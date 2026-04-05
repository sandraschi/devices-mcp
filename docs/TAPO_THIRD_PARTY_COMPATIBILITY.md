# Tapo Third-Party Compatibility - REQUIRED for API Access

## Critical Discovery

**Tapo cameras require "Third-Party Compatibility" to be enabled in the Tapo app** for API access to work, even if you have correct Camera Account credentials.

This is a security feature that explicitly controls whether third-party applications (like our API) can access the camera.

## How to Enable Third-Party Compatibility

### Steps in Tapo iOS App:

1. **Open Tapo App** on your iPhone/iPad
2. **Tap "Me"** (bottom right) or your profile icon
3. **Tap "Tapo Lab"** (or "Settings" → "Tapo Lab")
4. **Find "Third-Party Compatibility"** (or "Third Party Compatibility")
5. **Toggle the switch to "ON"** (it will mention Home Assistant support)
6. **Reboot the camera** (power cycle or through app)

### Alternative Path (varies by app version):

- **Settings** → **Tapo Lab** → **Third-Party Compatibility** → **Toggle ON**
- **Me** → **Tapo Labs** → **Third-Party Compatibility** → **Toggle ON**
- **Camera** → **Settings** → **Advanced** → **Tapo Lab** → **Third-Party Compatibility**

## What This Does

When enabled:
- ✅ Allows third-party API access to camera
- ✅ Enables Home Assistant integration
- ✅ Allows our python API (pytapo) to authenticate
- ✅ Camera Account credentials will work via API

When disabled:
- ❌ API authentication fails even with correct credentials
- ❌ Third-party apps cannot access camera
- ❌ Error: "Invalid authentication data"

## After Enabling

1. **Reboot camera** (power cycle or through app)
2. **Wait 1-2 minutes** for camera to fully restart
3. **Test connection**: `python scripts/test_tapo_connection.py`

The Camera Account credentials (sandraschi / Sec1000kitchen) should now work via API.

## References

- Home Assistant Community: Tapo C200 requires this setting for integration
- Tapo Lab feature explicitly mentions Home Assistant support
- This is a security feature to control third-party access
