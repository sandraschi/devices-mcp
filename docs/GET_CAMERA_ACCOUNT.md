# How to Get Camera Account Credentials in Tapo iOS App

## Steps to Find/Create Camera Account

Since both cameras are already set up in the Tapo app, follow these steps to get the **Camera Account** credentials (for API access):

### For Each Camera (Kitchen & Living Room):

1. **Open Tapo App** on your iPhone/iPad
2. **Tap on the camera** (Kitchen or Living Room)
3. **Tap the gear icon** ⚙️ (Settings) in the top right
4. **Scroll down and tap "Advanced Settings"**
5. **Look for one of these options:**
   - **"Camera Account"** (most common)
   - **"Local Device Settings"**
   - **"Device Account"**
   - **"Account Settings"**

6. **If Camera Account is already set:**
   - You'll see the username (usually `admin`)
   - Password will be hidden (dots or asterisks)
   - **Tap to view/edit** if there's an option

7. **If Camera Account is not set yet:**
   - **Tap "Enable Camera Account"** or **"Set Camera Account"**
   - Create username (usually `admin`)
   - Create password (**write it down!**)
   - Save

### Alternative Paths (varies by app version):

Some app versions have different paths:

- **Camera → Settings → Advanced → Account → Camera Account**
- **Camera → Settings → Device Settings → Advanced → Camera Account**
- **Camera → Settings → Local Account**

### What to Look For:

- Username: Usually `admin` (or what you set)
- Password: The password you created (write it down!)

### Note:

- **Camera Account** = Local credentials for API access
- **Different from your cloud account** (sandraschipal@hotmail.com)
- These are the credentials you'll use in `config.yaml`

## Once You Have the Credentials:

1. Update `config.yaml` with username/password for each camera
2. Test connection: `python scripts/test_tapo_connection.py`
3. Verify both cameras work via API
