# Ring Doorbell & Alarm Integration

## Overview

The Devices MCP integrates with Ring devices to provide:
- **Ring Alarm Base Station EU** with full sensor support
- Live video streaming (WebRTC) for doorbells/cameras
- Two-way audio communication
- Motion and doorbell event notifications
- Alarm system arm/disarm control
- Sensor monitoring (contact, motion, flood/freeze, smoke/CO)
- Siren control

## Ring Alarm EU Support

### Supported Devices
| Device Type | Support |
|-------------|---------|
| Base Station EU (hub.redsky) | ✅ Full |
| Contact Sensors | ✅ Full |
| Motion Sensors | ✅ Full |
| Keypads | ✅ Full |
| Range Extenders | ✅ Status |
| Siren | ✅ Control |
| Flood/Freeze Sensors | ✅ Full |
| Smoke/CO Listeners | ✅ Full |
| Glass Break Sensors | ✅ Full |

### EU Hardware Specs
- Z-Wave Frequency: 868 MHz (EU/UK)
- Siren Volume: 104 dB
- Battery Backup: 24 hours
- Connectivity: Wi-Fi, Ethernet, Z-Wave

## Doorbell & Speakerphone Features (v1.18.0)

### 🔔 Doorbell Detection
- **Real-time doorbell press detection** from Ring's event API
- **Event history** with timestamps and answered/unanswered status
- **Recording availability** tracking for cloud-stored videos
- **Web interface integration** with dedicated doorbell events panel
- **Event notifications** with full metadata

### 📢 Speakerphone Integration
- **WebRTC two-way audio** using Ring's native infrastructure
- **Built-in speaker control** for talking back to visitors
- **Microphone input** for hearing doorbell audio
- **Full duplex communication** (simultaneous send/receive)
- **High-quality audio** compared to Tapo cameras

### Speakerphone vs Other Cameras

| Feature | Ring | Tapo | USB Webcam |
|---------|------|------|------------|
| **Two-way audio** | ✅ WebRTC | ✅ RTSP | ❌ None |
| **Speaker quality** | ✅ Good | ⚠️ Tinny | ❌ None |
| **Doorbell detection** | ✅ Real-time | ❌ None | ❌ None |
| **Cloud integration** | ✅ Ring Cloud | ❌ Local | ❌ Local |

---

## Features by Subscription

### Without Ring Protect (FREE)

| Feature | Status |
|---------|--------|
| Live View | ✅ Works |
| Two-Way Talk | ✅ Works |
| Motion Notifications | ✅ Works |
| Ding Notifications | ✅ Works |
| Device Status | ✅ Works |
| Alarm Control | ✅ Works |
| **Doorbell Events** | ✅ Works |
| **Speakerphone** | ✅ Works |

### With Ring Protect (~€4/month)

| Feature | Status |
|---------|--------|
| All free features | ✅ Works |
| Video Recording | ✅ Works |
| Event History Playback | ✅ Works |
| Snapshots | ✅ Works |

## Configuration

Add Ring credentials to `config.yaml`:

```yaml
ring:
  enabled: true
  email: your-email@example.com
  password: "your-ring-password"
  token_file: ring_token.cache
  cache_ttl: 60
```

## First-Time Authentication

1. Start the dashboard: `python start.py dashboard`
2. Ring will require 2FA - check your email/SMS for code
3. Go to http://localhost:7777/alarms
4. Enter the 2FA code when prompted
5. Token is cached for future sessions

## API Endpoints

### Status & Summary

```
GET /api/ring/status
GET /api/ring/summary
GET /api/ring/capabilities/{device_id}
```

### Events

```
GET /api/ring/events?limit=10
GET /api/ring/events/{device_id}/video/{recording_id}
```

### Alarm Control

```
GET /api/ring/alarm
GET /api/ring/alarm/devices
GET /api/ring/alarm/events?limit=50
POST /api/ring/alarm/mode
Body: {"mode": "disarmed|home|away"}
POST /api/ring/alarm/siren
Body: {"activate": true, "duration": 30}
```

### Alarm Mode Values
- `disarmed` (none): System off
- `home` (some): Perimeter sensors active
- `away` (all): All sensors active

### WebRTC Live View

```
POST /api/ring/webrtc/offer
Body: {"device_id": "xxx", "sdp_offer": "..."}

POST /api/ring/webrtc/candidate
Body: {"device_id": "xxx", "candidate": "..."}

POST /api/ring/webrtc/keepalive/{device_id}
POST /api/ring/webrtc/close/{device_id}
GET /api/ring/webrtc/ice-servers
```

### Authentication

```
POST /api/ring/auth/init
Body: {"email": "...", "password": "..."}

POST /api/ring/auth/2fa
Body: {"code": "123456"}
```

## Dashboard Features

### Alarms Page (http://localhost:7777/alarms)

- **Device Cards**: Shows all Ring doorbells with status
- **Live View Button**: Opens WebRTC stream with two-way talk
- **Alarm Controls**: Arm/disarm Ring alarm system
- **Event List**: Recent motion and ding events
- **DING Alert**: Full-screen popup when doorbell is pressed

### Alert System

The dashboard polls for new events every 10 seconds:

- **Doorbell Ring**: Full-screen orange alert with sound
- **Motion Detection**: Toast notification (slides in from right)

## Troubleshooting

### "Invalid user credentials"
- Check email/password in config.yaml
- Password may have special characters - use quotes

### "2FA Required"
- Check email/SMS for Ring verification code
- Enter via dashboard or API endpoint

### "No subscription" warnings
- Normal for free accounts
- Live view still works
- Video playback requires Ring Protect

### WebRTC Connection Issues
- Check browser console for errors
- Ensure microphone permissions granted
- Try refreshing the page

## Technical Notes

### Dependencies
- `ring_doorbell` library (installed via requirements.txt)
- WebRTC support in browser (Chrome/Firefox/Edge)

### Token Caching
- After successful 2FA, token is saved to `ring_token.cache`
- Future startups use cached token (no 2FA needed)
- Token auto-refreshes as needed

### Rate Limiting
- Ring API has rate limits
- Dashboard caches responses for 60 seconds
- Snapshot API limited without subscription
