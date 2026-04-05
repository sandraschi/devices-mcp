# Verify Tapo Camera Credentials

## Kitchen Camera - Credentials to Verify

**Current credentials in config.yaml:**
- Username: `sandraschi`
- Password: `Sec1000kitchen`
- IP: `192.168.0.164`

## Verification Steps

### 1. In Tapo iOS App

1. Open Tapo app → Kitchen Camera
2. Tap Settings (gear icon) → Advanced Settings
3. Find **Camera Account** (or Local Device Settings)
4. **Verify:**
   - Username shows as: `sandraschi` ✓
   - Password matches: `Sec1000kitchen` ✓
   - Check for typos or case sensitivity

### 2. Common Issues to Check

- **Username typo**: Is it `sandraschi` or `sandraschipal`?
- **Password case**: `Sec1000kitchen` vs `sec1000kitchen` vs `SEC1000kitchen`
- **Special characters**: Make sure password matches exactly
- **Space issues**: No leading/trailing spaces

### 3. After Lockout Clears

1. **Power cycle camera** (quickest way to clear lockout)
2. **Verify credentials** in Tapo app (Steps 1-2 above)
3. **Update config.yaml** if credentials don't match
4. **Test connection**: `python scripts/test_tapo_connection.py`

## Alternative: Reset Camera Account

If credentials keep failing:

1. In Tapo app: Camera → Settings → Advanced → Camera Account
2. **Change password** (reset it)
3. **Write down new password**
4. **Update config.yaml** with new password
5. **Test connection**

## Test Script

After lockout clears, test with:

```powershell
python scripts/test_tapo_connection.py
```

This will use credentials from `config.yaml` automatically.
