# Tapo Camera Username Quirk

## Important Discovery

**Some Tapo cameras require `admin` as the username for API access**, even if you set a different username in the Camera Account settings in the Tapo app.

## The Issue

- **Camera Account in App**: You set username `sandraschi` with password `Sec1000kitchen`
- **API Access**: May require username `admin` with the same password `Sec1000kitchen`

## Solution to Try

After power cycling the camera, try:

1. **Username**: `admin` (not `sandraschi`)
2. **Password**: `Sec1000kitchen` (your Camera Account password)

This is a common quirk with Tapo cameras - the Camera Account username is for app access, but API access often requires `admin`.

## Test After Power Cycle

Once camera is power cycled and lockout cleared:

```powershell
python scripts/test_admin_username.py
```

This will test with `admin` / `Sec1000kitchen`.

If that works, update config.yaml:

```yaml
tapo_kitchen:
  type: tapo
  params:
    host: 192.168.0.164
    username: "admin"  # Use 'admin' for API access
    password: "Sec1000kitchen"  # Your Camera Account password
```

## Alternative: Check App Settings

In Tapo app:
1. Camera → Settings → Advanced
2. Look for "API Access" or "Local Access" settings
3. Check if there's a toggle for API access with Camera Account
4. Some cameras have separate API credentials
