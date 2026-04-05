# Tapo Camera Connection Fix Plan

**Timestamp**: 2025-01-17
**Status**: IN PROGRESS - Camera Locked Out
**Priority**: HIGH

## Current Status

**Camera Status**: 🔒 **LOCKED OUT** (30 minute temporary suspension)
- **Error**: "Temporary Suspension: Try again in 1799 seconds"
- **Cause**: Too many failed authentication attempts
- **Solution**: Wait 30 minutes before retrying

## Root Cause Analysis

### Issue 1: Camera Lockout
- **Status**: ✅ IDENTIFIED
- **Cause**: Multiple failed authentication attempts
- **Lockout Duration**: 30 minutes (1800 seconds)
- **Action**: Wait for lockout to expire

### Issue 2: Authentication Method
- **Status**: ⚠️ UNKNOWN (needs testing after lockout)
- **Possible Causes**:
  1. Wrong credentials (Camera Account vs Admin)
  2. KLAP protocol required (newer firmware)
  3. Third-Party Compatibility not enabled
  4. pytapo version incompatibility

## Test Results

### Method 1: pytapo
- **Status**: ❌ FAILED
- **Error**: "Invalid authentication data" → "Temporary Suspension"
- **Version**: 3.3.51 (latest available)
- **Action**: Test after lockout expires

### Method 2: python-kasa
- **Status**: ❌ FAILED
- **Error**: Connection refused on port 9999
- **Version**: 0.7.7
- **Note**: Primarily for Kasa devices, limited Tapo support

### Method 3: ONVIF
- **Status**: ❌ FAILED
- **Error**: Connection aborted on all ports (80, 8080, 554, 443)
- **Note**: May not be enabled on camera

## Immediate Actions (After Lockout Expires)

### Step 1: Verify Settings in Tapo App

1. **Third-Party Compatibility**
   - Path: `Tapo App → Me → Tapo Lab → Third-Party Compatibility`
   - Status: Must be **ON**
   - Action: Verify and enable if needed

2. **Camera Account**
   - Path: `Tapo App → Camera → Settings → Advanced → Camera Account`
   - Username: `sandraschi` (from config)
   - Password: `Sec1000kitchen` (from config)
   - Action: Verify credentials are correct

3. **Firmware Version**
   - Path: `Tapo App → Camera → Settings → Firmware Update`
   - Action: Check version and update if available
   - Note: Newer firmware may require KLAP protocol

### Step 2: Test Credentials (After Lockout)

**Script**: `scripts/test_tapo_credentials.py`

This script tests multiple credential combinations:
1. Camera Account (from config)
2. Admin + Camera Password
3. Admin + Admin
4. Camera Username + Admin Password

**Usage**:
```bash
python scripts/test_tapo_credentials.py
```

**Important**: Only run ONCE after lockout expires to avoid another lockout!

### Step 3: Check pytapo Version

**Current**: 3.3.51

**Check for updates**:
```bash
pip install --upgrade pytapo
```

**Check GitHub**: https://github.com/JurajNyiri/pytapo
- Look for KLAP protocol support
- Check latest release notes
- Review open issues related to authentication

## Alternative Solutions

### Solution 1: Use RTSP Direct Streaming

**Pros**:
- Bypasses API authentication
- Works for video streaming
- Standard protocol

**Cons**:
- No camera control (PTZ, settings)
- Only for video streaming

**RTSP URL Format**:
```
rtsp://sandraschi:Sec1000kitchen@192.168.0.164:554/stream1
```

**Test with VLC**:
1. Open VLC
2. Media → Open Network Stream
3. Enter RTSP URL
4. Test connection

### Solution 2: Check for KLAP Support

**Research**:
- Check pytapo GitHub for KLAP support
- Look for alternative libraries with KLAP
- Consider contributing KLAP support to pytapo

**KLAP Protocol**:
- New authentication protocol in recent Tapo firmware
- May require library updates
- More secure than previous methods

### Solution 3: Use Home Assistant Integration

**Option**: Use Home Assistant's Tapo integration
- **Integration**: "HomeAssistant - Tapo: Cameras Control"
- **Status**: Actively maintained
- **Features**: Full camera control, motion detection

**If it works in Home Assistant**:
- Reverse engineer their method
- Adapt to our codebase

## Testing Checklist (After Lockout)

- [ ] Wait 30 minutes for lockout to expire
- [ ] Verify Third-Party Compatibility is enabled
- [ ] Verify Camera Account credentials in Tapo app
- [ ] Check camera firmware version
- [ ] Run `test_tapo_credentials.py` (ONCE!)
- [ ] Test RTSP streaming with VLC
- [ ] Check pytapo GitHub for KLAP support
- [ ] Test with latest pytapo version
- [ ] Document working solution

## Timeline

1. **Now**: Wait for lockout to expire (30 minutes)
2. **After Lockout**: Run credential test script
3. **If Still Failing**: Test RTSP and research KLAP
4. **Final Solution**: Implement working method

## Related Files

- `scripts/test_tapo_credentials.py` - Credential testing
- `scripts/test_all_tapo_methods.py` - All methods test
- `scripts/test_tapo_connection.py` - Basic connection test
- `docs/TAPO_CAMERA_CONNECTION_ANALYSIS_2025.md` - Full analysis
- `config.yaml` - Camera configuration

## Next Steps

1. **Wait 30 minutes** for lockout to expire
2. **Verify settings** in Tapo app (Third-Party Compatibility, Camera Account)
3. **Run test script** once to find working credentials
4. **Document solution** once working
5. **Update code** if different method is needed

---

**Last Updated**: 2025-01-17
**Lockout Expires**: ~30 minutes from last attempt
**Status**: Waiting for lockout to expire
