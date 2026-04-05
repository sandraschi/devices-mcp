# How to Get a New Netatmo Refresh Token

**Date:** 2025-12-10
**Status:** ✅ Complete Guide

## Overview

Netatmo uses OAuth2 authentication. You need a **refresh token** to access your weather station data. This guide walks you through getting a new refresh token.

## Prerequisites

1. **Netatmo Developer Account**: Create an app at https://dev.netatmo.com/apps
2. **Client ID and Secret**: From your Netatmo developer app
3. **Redirect URI**: Must match what's configured in your Netatmo app (e.g., `https://localhost/callback`)

## Step-by-Step Guide

### Step 1: Get Authorization URL

Run the helper script to generate the authorization URL:

```powershell
cd D:\Dev\repos\devices-mcp
.\venv\Scripts\Activate.ps1
python scripts\netatmo_oauth_helper.py auth-url <CLIENT_ID> <REDIRECT_URI>
```

**Example:**
```powershell
python scripts\netatmo_oauth_helper.py auth-url 6827631abc073747f105a0e4 https://localhost/callback
```

This will:
- Print the authorization URL
- Automatically open it in your browser

### Step 2: Login and Authorize

1. **Login** with your Netatmo account credentials
2. **Authorize** the app to access your weather station data
3. **Copy the authorization code** from the redirect URL

The redirect URL will look like:
```
https://localhost/callback?code=AUTHORIZATION_CODE_HERE&state=xyz
```

**Important:**
- Copy the `code` parameter value (everything after `code=` and before `&state`)
- **⚠️ Authorization codes expire quickly (usually within 10 minutes)**
- **⚠️ Codes can only be used once** - if you get "invalid_grant" error, get a fresh code
- **⚠️ The "not found" page is normal** - there's no server listening on `https://localhost/callback`. Just copy the code from the URL!

### Step 3: Exchange Code for Tokens

Exchange the authorization code for access and refresh tokens:

```powershell
python scripts\netatmo_oauth_helper.py exchange <CLIENT_ID> <CLIENT_SECRET> <CODE> <REDIRECT_URI>
```

**Example:**
```powershell
python scripts\netatmo_oauth_helper.py exchange 6827631abc073747f105a0e4 Uge1m7YrypuK2Wz7QjqfhduhEQlPJYWC4uKSEH AUTHORIZATION_CODE_HERE https://localhost/callback
```

**Output:**
```json
{
  "access_token": "...",
  "refresh_token": "NEW_REFRESH_TOKEN_HERE",
  "expires_in": 10800,
  "scope": "read_station"
}
```

### Step 4: Update config.yaml

1. **Copy the `refresh_token`** from the output
2. **Open** `config.yaml`
3. **Update** the refresh token:

```yaml
weather:
  integrations:
    netatmo:
      enabled: true
      client_id: '6827631abc073747f105a0e4'
      client_secret: 'Uge1m7YrypuK2Wz7QjqfhduhEQlPJYWC4uKSEH'
      redirect_uri: 'https://localhost/callback'
      refresh_token: 'NEW_REFRESH_TOKEN_HERE'  # ← Update this
```

4. **Save** the file
5. **Restart** the server: `.\start_dashboard.ps1`

## Quick Reference

### Current Config Values

From your `config.yaml`:
- **Client ID**: `6827631abc073747f105a0e4`
- **Client Secret**: `Uge1m7YrypuK2Wz7QjqfhduhEQlPJYWC4uKSEH`
- **Redirect URI**: `https://localhost/callback`

### One-Line Commands

**Get auth URL:**
```powershell
python scripts\netatmo_oauth_helper.py auth-url 6827631abc073747f105a0e4 https://localhost/callback
```

**Exchange code (replace CODE_HERE):**
```powershell
python scripts\netatmo_oauth_helper.py exchange 6827631abc073747f105a0e4 Uge1m7YrypuK2Wz7QjqfhduhEQlPJYWC4uKSEH CODE_HERE https://localhost/callback
```

## Troubleshooting

### "Invalid redirect_uri"

- Ensure the redirect URI in your Netatmo app matches exactly: `https://localhost/callback`
- Check for typos or trailing slashes

### "Invalid client_id or client_secret"

- Verify your credentials at https://dev.netatmo.com/apps
- Make sure you're using the correct app's credentials

### "Authorization code expired" or "invalid_grant"

- Authorization codes expire quickly (usually within 10 minutes)
- **Codes can only be used once** - if exchange fails, get a fresh code
- Get a new code by repeating Step 1-2
- **Do the exchange immediately** after getting the code - don't wait!

### "Refresh token expired"

- Refresh tokens can expire if not used for a long time
- Follow this guide to get a new refresh token

### "403 - Forbidden - Invalid access token" (After Refresh)

**Symptom**: You just refreshed the token 20 minutes ago, but still getting 403 errors.

**Cause**: The system was using a cached/stale access token instead of refreshing.

**Fix Applied (2025-12-10)**: The system now properly clears cached tokens when 403 errors occur:
- Clears both access token AND expiry timestamp
- Forces a complete token refresh
- Automatically retries the API call

**What to do**:
1. **Wait for next API call** - The fix will automatically trigger on the next weather data request
2. **Or restart the server** - This forces a fresh token refresh on startup
3. **Check logs** - Look for "Netatmo access token refreshed" messages
4. **If still failing** - The refresh token itself might be invalid - follow this guide to get a new one

## Token Refresh (Automatic)

Once you have a valid refresh token, the system automatically refreshes access tokens as needed. The refresh token itself is updated automatically when Netatmo issues a new one.

### How Automatic Refresh Works

The system handles token refresh automatically:

1. **Access tokens expire** after ~3 hours (10800 seconds)
2. **Automatic refresh** happens before expiry (60 seconds buffer)
3. **403 errors trigger refresh**: If a 403 "Invalid access token" error occurs, the system:
   - Clears the cached access token
   - Clears the token expiry timestamp
   - Forces a fresh token refresh
   - Retries the API call with the new token
4. **Refresh token updates**: When Netatmo issues a new refresh token, it's automatically saved to `netatmo_token.cache`

### Token Refresh Fix (2025-12-10)

**Issue**: After refreshing tokens, the system was still getting 403 errors because pyatmo was using cached tokens.

**Fix**: The system now properly clears both the access token AND the token expiry timestamp when 403 errors occur, forcing a complete token refresh instead of using stale cached tokens.

**Result**: Token refresh now works reliably - if you refresh a token and still see 403 errors, the system will automatically detect and fix it on the next API call.

## Alternative: Netatmo Developer Portal

If the script doesn't work, you can also:

1. Go to https://dev.netatmo.com/apps
2. Login with your Netatmo account
3. Select your app
4. Use the "Generate Token" feature (if available)
5. Copy the refresh token to `config.yaml`

## Verification

After updating the refresh token:

1. **Restart the server**: `.\start_dashboard.ps1`
2. **Check logs**: Look for "Netatmo initialized" messages
3. **Check weather page**: http://localhost:7777/weather
4. **Verify data**: Should show real weather station data (not simulated)

## Notes

- **Refresh tokens** are long-lived and don't expire unless revoked
- **Access tokens** expire after ~3 hours and are automatically refreshed
- The system saves updated refresh tokens to `netatmo_token.cache` automatically
- If token refresh fails, check logs for specific error messages
- **Token refresh fix (2025-12-10)**: Fixed issue where 403 errors occurred after token refresh due to cached tokens. System now properly clears cache and forces refresh on 403 errors.

## Recent Changes

### 2025-12-10: Token Refresh Fix

**Problem**: After refreshing Netatmo tokens, the system was still getting 403 "Invalid access token" errors because pyatmo was using cached/stale access tokens.

**Solution**:
- Modified token refresh logic to clear both `_access_token` and `_token_expiry` when 403 errors occur
- Added proper 403 error handling in both `list_stations()` and `current_data()` methods
- System now forces a complete token refresh instead of using stale cached tokens

**Files Changed**:
- `src/devices_mcp/integrations/netatmo_client.py`
- `src/devices_mcp/web/server.py` (added missing `active_page` parameter to weather route)

**Result**: Token refresh now works reliably. If you refresh a token and see 403 errors, the system will automatically detect and fix it on the next API call.
