# Netatmo Weather Station Integration

## Overview
Adds a configurable Netatmo integration with graceful fallback to simulated data until credentials are provided. When enabled, the weather API and `/metrics` can source real readings.

**⚠️ Important**: All simulated/mock data is clearly marked with warnings and indicators. When Netatmo is properly configured, you'll see real data from your weather station.

## Configuration
Add to your `config.yaml` (example):

```yaml
weather:
  integrations:
    netatmo:
      enabled: true
      client_id: "<your_client_id>"
      client_secret: "<your_client_secret>"
      redirect_uri: "https://localhost/callback"
      refresh_token: "<your_refresh_token>"
      # Legacy fallback (optional; not recommended):
      # username: "<your_netatmo_email>"
      # password: "<your_netatmo_password>"
      home_id: "<optional_home_id>"
```

**Important Notes:**
- If `enabled: true` but credentials are missing/invalid, the system falls back to **simulated data** (clearly marked with warnings)
- When disabled, the weather API continues to serve simulated data for UI/dev
- **Simulated data indicators**: Station names include "(SIMULATED/MOCK DATA)", responses include `is_simulated: true` flags, and warning banners are displayed
- The `refresh_token` should be a single string without special characters (no pipes `|` or other separators)

## Endpoints
- `GET /api/weather/stations` — lists stations (real or simulated)
- `GET /api/weather/stations/{station_id}/data?module_type=indoor|outdoor|all` — current readings
- Additional endpoints (historical, health) remain available with simulated outputs until extended.

## Metrics
- `/metrics` already publishes Netatmo-style series. Once enabled, these can be backed by real readings.

## Install Dependency

**Required**: The `pyatmo` package must be installed for real Netatmo data:

```powershell
pip install "pyatmo>=8.0.0,<9.0.0"
```

**⚠️ Without pyatmo installed**, the system will use simulated data even if credentials are configured.

The client wrapper is at `src\devices_mcp\integrations\netatmo_client.py` and will switch to real calls when:
1. `pyatmo` is installed
2. `enabled: true` in config
3. Valid `client_id`, `client_secret`, and `refresh_token` are provided
4. Token refresh succeeds

## OAuth Flow (Recommended)
1. Build an authorization URL and open it:
   ```powershell
   python .\\scripts\\netatmo_oauth_helper.py auth-url <CLIENT_ID> https://localhost/callback
   ```
2. After login/consent, copy the `code` from the redirect URL.
3. Exchange code for tokens:
   ```powershell
   python .\\scripts\\netatmo_oauth_helper.py exchange <CLIENT_ID> <CLIENT_SECRET> <CODE> https://localhost/callback
   ```
   Save `refresh_token` into `config.yaml` under `weather.integrations.netatmo.refresh_token`.
4. To periodically refresh access tokens (if needed for direct API calls):
   ```powershell
   python .\\scripts\\netatmo_oauth_helper.py refresh <CLIENT_ID> <CLIENT_SECRET> <REFRESH_TOKEN>
   ```

      "no netatmo metrics found"
  }
  ```
  You should see: `netatmo_temperature_celsius`, `netatmo_humidity_percent`, `netatmo_co2_ppm`, `netatmo_pressure_mbar` populated from your station.
