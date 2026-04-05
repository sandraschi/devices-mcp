# Tapo Camera Authentication Checklist

## ✅ Completed Steps
- [x] Camera set up in Tapo app
- [x] Camera Account created (sandraschi / Sec1000kitchen)
- [x] Third-Party Compatibility enabled in Tapo app
- [x] Camera power cycled after enabling Third-Party Compatibility
- [x] Camera is online (port 443 reachable)

## ❌ Still Failing - Additional Checks Needed

### 1. Disable Two-Step Verification
**In Tapo App:**
- Go to **Me** → **View Account** → **Login Security**
- **Turn OFF** Two-Step Verification
- Two-Step Verification can interfere with API authentication

### 2. Verify Camera Account Settings
**In Tapo App:**
- Camera → Settings → Advanced → Camera Account
- **Double-check:**
  - Username: `sandraschi` ✓
  - Password: `Sec1000kitchen` ✓
  - No extra spaces or characters
  - Password matches exactly (case-sensitive)

### 3. Check Firmware Version
**In Tapo App:**
- Camera → Settings → Advanced → Firmware
- **Check for updates** - outdated firmware can cause auth issues
- Update if available, then reboot camera

### 4. Try Alternative Authentication
Some cameras require different approaches:
- ONVIF credentials (if camera has ONVIF enabled)
- Different authentication method
- Check if Camera Account needs "API Access" toggle enabled

### 5. Network/Port Issues
- Verify camera is on same network (10.2.4.x)
- Check firewall settings (port 443)
- Try accessing camera web interface directly (if available)

## Next Steps

1. **Disable Two-Step Verification** (most likely culprit)
2. **Verify Camera Account credentials again** in app
3. **Update firmware** if available
4. **Test again** after changes

## If Still Failing

May need to:
- Reset Camera Account and recreate it
- Check pytapo library version (may need update)
- Contact TP-Link support with specific error
- Try different third-party library (if available)
