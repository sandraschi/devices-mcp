# Tapo Camera Setup Checklist

## ✅ Power Cycle Complete
- [x] Kitchen camera power cycled (lockout cleared)

## Next Steps (Do in Order)

### Step 1: Set Up Camera in Tapo App
- [ ] Open Tapo app on your phone
- [ ] Log in with: sandraschipal@hotmail.com
- [ ] Tap **"+"** button to add device
- [ ] Select **"Cameras"** → **"Tapo C200"**
- [ ] Scan QR code on camera (or enter serial number)
- [ ] Connect camera to Wi-Fi (10.2.4.x network)
- [ ] Complete setup wizard

### Step 2: Create Camera Account (API Credentials)
- [ ] In Tapo app, tap on your kitchen camera
- [ ] Tap **Settings** (gear icon)
- [ ] Go to **"Advanced Settings"**
- [ ] Find **"Camera Account"** or **"Local Device Settings"**
- [ ] Enable/Set **Camera Account**:
  - Username: `admin` (or your choice)
  - Password: `________` (write it down!)
- [ ] Save settings

### Step 3: Update Config File
- [ ] Open `config.yaml`
- [ ] Find `tapo_kitchen` section
- [ ] Update username: `username: "admin"` (or what you set)
- [ ] Update password: `password: "YOUR_PASSWORD"`
- [ ] Save file

### Step 4: Test Connection
```powershell
python scripts/test_tapo_connection.py
```

Expected result: `[SUCCESS] Connection successful!`

### Step 5: Update Living Room Camera Too
- [ ] Repeat Steps 1-4 for living room camera (192.168.0.206)
- [ ] Update `tapo_living_room` section in config.yaml

---

## Notes

- **Camera Account ≠ Cloud Account**:
  - Cloud Account = Tapo app access (your email/password)
  - Camera Account = API access (username/password you set in app)

- **Camera IP**: Kitchen camera should be at 192.168.0.164 after setup

- **After setup**: Camera will be accessible via API using Camera Account credentials
