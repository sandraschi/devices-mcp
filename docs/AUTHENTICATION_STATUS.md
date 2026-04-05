# Tapo Camera Authentication Status

**Date**: November 29, 2025
**Status**: ✅ FULLY WORKING via ONVIF

## Summary

**RESOLVED**: Both Tapo C200 cameras now fully operational via ONVIF protocol!

| Protocol | Status | Features |
|----------|--------|----------|
| ONVIF | ✅ **Fully working** | Live stream, PTZ, snapshots |
| pytapo 3.3.53 | ❌ "Invalid authentication data" | N/A |

## Working Features (ONVIF)

| Feature | Status | Notes |
|---------|--------|-------|
| Device Info | ✅ | Model, firmware, serial |
| RTSP Streaming | ✅ | `rtsp://host:554/stream1` |
| Snapshot Capture | ✅ | Via RTSP frame grab |
| PTZ Control | ✅ | Pan, tilt, zoom |
| Media Profiles | ✅ | mainStream, minorStream, jpegStream |

## Camera Configuration

### Kitchen Camera (192.168.0.164)

| Property | Value |
|----------|-------|
| Device Name | Kitchencam |
| Model | Tapo C200 |
| Firmware | 1.4.4 Build 250922 Rel.71116n |
| Serial | 746161dd |
| Status | ✅ Online |

### Living Room Camera (192.168.0.206)

| Property | Value |
|----------|-------|
| Device Name | Living Room |
| Model | Tapo C200 |
| Firmware | 1.4.4 Build 250922 Rel.71116n |
| Serial | 7461ae28 |
| Status | ✅ Online |

## config.yaml (Working)

```yaml
cameras:
  kitchen_cam:
    type: onvif
    params:
      host: 192.168.0.164
      onvif_port: 2020
      username: sandraschi
      password: <redacted>

  living_room_cam:
    type: onvif
    params:
      host: 192.168.0.206
      onvif_port: 2020
      username: sandraschi
      password: <redacted>
```

## PTZ Controls (Working)

Dashboard UI at `/cameras` includes:
- D-pad for pan/tilt
- Zoom in/out buttons
- Stop button (center)
- Hold-to-move interaction

API endpoints:
- `POST /api/ptz/move` - Continuous movement
- `POST /api/ptz/stop/{camera_id}` - Stop movement
- `GET /api/ptz/presets/{camera_id}` - List presets
- `POST /api/ptz/preset/{camera_id}` - Go to preset

## Demo Script

```bash
# Full demo with PTZ movements
python scripts/demo.py --camera kitchen_cam

# Skip PTZ (just info and snapshot)
python scripts/demo.py --camera living_room_cam --no-ptz

# List all cameras
python scripts/demo.py --list
```

## Legacy pytapo Status (Deprecated)

pytapo library fails authentication for Tapo C200 cameras even with:
- ✅ Correct Camera Account credentials
- ✅ Third-Party Compatibility enabled
- ✅ Latest pytapo version (3.3.53)
- ✅ Camera online (port 443 reachable)

**Recommendation**: Use ONVIF for Tapo C200 cameras. pytapo may work for other Tapo models.

---

*Last Updated: November 29, 2025*
