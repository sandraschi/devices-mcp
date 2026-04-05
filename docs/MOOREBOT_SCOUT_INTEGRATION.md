# Moorebot Scout Integration

**Timestamp**: 2025-12-02
**Status**: Mock implementation ready, hardware arrives XMas 2025
**GitHub SDK**: https://github.com/Pilot-Labs-Dev/Scout-open-source

## Overview

Integration of Moorebot Scout AI-powered mobile security robot into the Home Security MCP platform. Provides full API control, camera streaming, sensor data, and autonomous patrol capabilities.

## Hardware Specs

- **Model**: Moorebot Scout (Original - Mecanum Wheels)
- **Dimensions**: 11.5cm × 10cm × 8cm (350g)
- **Camera**: 1080p @ 30fps, 120° wide-angle, IR night vision
- **Sensors**: ToF (0.1-3m), 6DoF IMU, light sensor
- **Mobility**: 4× mecanum wheels (omnidirectional)
- **Max Speed**: 2 km/h (0.3 m/s)
- **Battery**: 2+ hours (1 hour with night vision)
- **Connectivity**: Wi-Fi 2.4/5GHz, ROS 1.4
- **Price**: ~€200-300 (if available)

## Features Implemented

### ✅ Core Robot Control
- Get status (battery, position, sensors)
- Movement control (linear, angular velocities)
- Emergency stop
- Return to charging dock

### ✅ Autonomous Operations
- Patrol routes (default, perimeter, rooms)
- Auto-navigation with waypoints
- Obstacle avoidance (ToF sensor)
- Auto-return when battery low

### ✅ Camera & Sensors
- RTSP video streaming (1080p H.264)
- RTSP audio streaming (AAC)
- Camera snapshots (JPEG)
- Sensor data (ToF, IMU, light)

### ✅ Mock Mode
- Realistic test data generation
- Battery drain simulation
- Position tracking
- Docking failures (70% success rate - realistic!)

## Configuration

Add to `config.yaml`:

```yaml
robotics:
  moorebot_scout:
    enabled: true
    ip_address: "192.168.1.100"  # Robot IP
    mock_mode: true  # Set to false when hardware arrives

    # Apartment map (Stroheckgasse)
    location:
      home_base: {x: 0.0, y: 0.0}
      rooms:
        living_room: {x_min: 0, x_max: 5, y_min: 0, y_max: 4}
        bedroom: {x_min: 5, x_max: 8, y_min: 0, y_max: 3}
        kitchen: {x_min: 0, x_max: 3, y_min: 4, y_max: 7}

    # Patrol routes
    patrols:
      default:
        - {x: 2.0, y: 2.0, room: "living_room"}
        - {x: 6.0, y: 1.5, room: "bedroom"}
        - {x: 1.0, y: 5.0, room: "kitchen"}
        - {x: 0.0, y: 0.0, room: "home_base"}

    # Automation
    automation:
      japan_trip_patrol:  # Oct 2025
        enabled: false
        schedule: ["08:00", "14:00", "20:00", "02:00"]

      benny_follow:  # German Shepherd tracking
        enabled: false

      low_battery_auto_dock: true
      battery_threshold: 20  # %
```

## MCP Tools Available

### `moorebot_get_status()`
Get robot status (battery, position, WiFi, sensors).

```python
result = await moorebot_get_status()
# {
#   "status": "idle",
#   "battery_level": 85,
#   "position": {"x": 2.5, "y": 1.0, "heading": 45, "room": "living_room"}
# }
```

### `moorebot_move(linear, angular, duration)`
Move robot with specified velocities.

```python
# Forward 0.2 m/s for 3 seconds
await moorebot_move(linear=0.2, duration=3.0)

# Rotate in place
await moorebot_move(angular=-1.0, duration=2.0)

# Emergency stop
await moorebot_move(0.0, 0.0)
```

### `moorebot_patrol(route)`
Start autonomous patrol route.

```python
await moorebot_patrol("default")  # 4 waypoints
await moorebot_patrol("perimeter")  # Full apartment
```

### `moorebot_return_to_dock()`
Return to charging station.

```python
result = await moorebot_return_to_dock()
# Note: 70% success rate (alignment issues common)
```

### `moorebot_get_sensors()`
Get sensor readings (ToF, IMU, light).

```python
sensors = await moorebot_get_sensors()
# {
#   "tof_distance": 1.235,
#   "light_ch0": 45000,
#   "imu": {...}
# }
```

### `moorebot_get_camera_stream()`
Get RTSP stream URLs.

```python
streams = await moorebot_get_camera_stream()
# {
#   "video_url": "rtsp://192.168.1.100:8554/stream",
#   "audio_url": "rtsp://192.168.1.100:8554/audio"
# }
```

## Testing

### Run Mock Tests

```powershell
cd devices-mcp
pytest tests/unit/test_moorebot_client.py -v
```

### Test Coverage
- ✅ Client connection (mock mode)
- ✅ Status queries
- ✅ Movement commands
- ✅ Patrol operations
- ✅ Docking (with realistic failures)
- ✅ Sensor data
- ✅ Camera streaming
- ⏳ Hardware tests (pending robot arrival)

## Integration with Dashboard

The Moorebot Scout will appear in the Robotics section of the dashboard:

**Features:**
- Live camera feed (RTSP)
- Battery level indicator
- Position on apartment map
- Manual controls (joystick)
- Quick actions (patrol, dock, stop)
- Sensor readings (real-time)
- Event log

## Known Issues

### Docking Unreliability (~70% success)
- **Cause**: IR beacon alignment, surface issues
- **Workaround**: Place dock on hard floor, clear 1m area
- **Fix**: Manual placement if 3+ failures

### Surface Compatibility
- ✅ Wood floors (excellent)
- ✅ Short carpet (good)
- ❌ Shag carpet (gets stuck)
- ❌ Stairs (cannot climb)

### WiFi Dropouts
- **Cause**: 2.4GHz interference, range
- **Workaround**: Use 5GHz band, strong router

## ROS Integration

### Topics Subscribed
- `/CoreNode/h264` - Video frames (H.264)
- `/CoreNode/aac` - Audio frames (AAC)
- `/SensorNode/tof` - ToF distance
- `/SensorNode/imu` - IMU data
- `/SensorNode/light` - Light sensor

### Topics Published
- `/cmd_vel` - Movement commands (Twist)

### Services Called
- `/start_patrol` - Begin patrol route
- `/stop_patrol` - Stop current patrol
- `/return_home` - Return to dock

## Development Roadmap

### Phase 1: Mock Development (Current - Dec 2025)
- ✅ Client implementation
- ✅ Mock fixtures
- ✅ MCP tools
- ✅ Unit tests
- ✅ Configuration schema

### Phase 2: Hardware Integration (XMas 2025)
- ⏳ Real ROS bridge connection
- ⏳ Camera stream integration
- ⏳ Patrol route tuning
- ⏳ Stroheckgasse apartment mapping

### Phase 3: Advanced Features (Jan 2026)
- ⏳ Benny (German Shepherd) tracking
- ⏳ Japan trip automation (Oct patrols)
- ⏳ Custom CV models (RTX 4090)
- ⏳ Frigate NVR integration

## Resources

- **Official SDK**: https://github.com/Pilot-Labs-Dev/Scout-open-source
- **Moorebot Website**: https://www.moorebot.com
- **ROS Melodic Docs**: http://wiki.ros.org/melodic
- **Integration Plan**: `docs/SMART_KITCHEN_AND_ROBOTICS_INTEGRATION_PLAN.md`
- **Advanced Memory Note**: `hardware/robots/moorebot-scout-xmas-gift-2025`

## Support

- **Hardware Issues**: Contact Pilot Labs support
- **Software Issues**: Check GitHub SDK issues
- **Integration Issues**: See `devices-mcp` project docs

---

**Last Updated**: 2025-12-02
**Next Review**: When hardware arrives (XMas 2025)
