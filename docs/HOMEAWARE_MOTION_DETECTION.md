# HomeAware Motion Detection

## Overview

HomeAware is Philips Hue's innovative motion detection system that uses the Zigbee mesh network signal strength changes to detect when people move through areas with Hue lights. This provides **passive, distributed motion detection** without requiring dedicated motion sensors.

## How It Works

### Zigbee Mesh Signal Analysis
- **Signal Strength Monitoring**: Continuously monitors signal strength between Hue lights and the bridge
- **Movement Detection**: Detects when someone walks between lights (signal attenuation)
- **Distributed Sensing**: Uses your existing Hue lights as motion sensors
- **No Extra Hardware**: Works with any Hue lights, no dedicated sensors needed

### Bridge Pro Requirement
HomeAware is only available with the **Philips Hue Bridge Pro (BSB002)**. The standard Hue Bridge (BSB001) does not support this feature.

## Configuration

### Automatic Detection
The system automatically detects when you have a Bridge Pro connected:

```yaml
lighting:
  philips_hue:
    bridge_ip: 192.168.0.83
    username: YOUR_BRIDGE_API_KEY
    # HomeAware automatically enabled when Bridge Pro detected
```

### API Endpoints

#### Get HomeAware Status
```http
GET /api/lighting/hue/homeaware/status
```

Response:
```json
{
  "enabled": true,
  "lights_monitored": 5,
  "motion_events": 2,
  "sensors": [
    {
      "light_id": "hue_light_1",
      "room": "Living Room",
      "signal_strength": 85,
      "signal_quality": "good",
      "motion_detected": false,
      "last_motion": "2026-01-18T14:30:00Z",
      "confidence": 0.0
    }
  ]
}
```

#### Check Recent Motion Events
```http
GET /api/lighting/hue/homeaware/motion
```

Response:
```json
{
  "motion_events": 1,
  "events": [
    {
      "light_id": "hue_light_3",
      "room": "Hallway",
      "confidence": 0.87,
      "timestamp": "2026-01-18T14:35:22Z",
      "signal_strength": 72,
      "variance": 18.5
    }
  ]
}
```

## Motion Detection Algorithm

### Signal Analysis
1. **Baseline Establishment**: System learns normal signal strength patterns
2. **Variance Detection**: Monitors for sudden signal strength changes
3. **Confidence Scoring**: Rates motion confidence based on variance magnitude
4. **Threshold Filtering**: Only reports high-confidence motion events

### Parameters
- **Motion Threshold**: Minimum signal variance to trigger detection (default: 15)
- **Confidence Threshold**: Minimum confidence score for alerts (default: 0.7)
- **Cooldown Period**: Minimum time between motion alerts (default: 30 seconds)

## Security Integration

### Motion Alerts
HomeAware motion events automatically integrate with the security system:

- **Alert Generation**: Motion events trigger security alerts
- **Room Identification**: Alerts specify which room motion was detected in
- **Confidence Levels**: Alerts include motion confidence scores
- **Event Correlation**: Motion events can trigger camera recording, lighting changes, etc.

### Configuration Example
```yaml
security:
  motion_detection:
    enabled: true
    homeaware_integration: true
    alert_on_motion: true
    confidence_threshold: 0.7
    cooldown_seconds: 30

  automated_actions:
    motion_detected:
      - turn_on_lights: true
      - start_recording: true
      - send_notification: true
```

## Setup Instructions

### 1. Hardware Requirements
- **Philips Hue Bridge Pro** (BSB002 model)
- **Hue Lights**: Any Zigbee-connected Hue lights
- **Network Coverage**: Lights should be distributed throughout the area you want to monitor

### 2. Bridge Setup
1. Connect Hue Bridge Pro to your network
2. Install Philips Hue app on your phone
3. Create/link Hue account
4. Add lights through the Hue app
5. Note the bridge IP address

### 3. Software Configuration
1. Update `config.yaml` with bridge IP and API key
2. Restart the Devices MCP server
3. Check `/api/lighting/hue/homeaware/status` to confirm HomeAware is enabled
4. Monitor motion events via `/api/lighting/hue/homeaware/motion`

### 4. Testing
1. Walk between Hue lights while monitoring the API
2. Check that motion events are detected and reported
3. Verify security alerts are triggered (if configured)

## Troubleshooting

### HomeAware Not Enabled
**Problem**: API returns `"enabled": false, "reason": "Bridge Pro required"`

**Solutions**:
- Verify you have a Bridge Pro (BSB002), not a standard Bridge (BSB001)
- Check bridge firmware is up to date
- Ensure bridge is properly connected to network

### No Motion Detection
**Problem**: Motion events not being detected

**Solutions**:
- Ensure lights are distributed throughout the monitored area
- Check that lights are Zigbee-connected (not Bluetooth-only)
- Verify bridge has good connectivity to all lights
- Try walking closer to lights to test detection

### False Positives
**Problem**: Too many false motion alerts

**Solutions**:
- Increase confidence threshold in configuration
- Adjust motion detection parameters
- Check for sources of signal interference (microwaves, cordless phones)

## Technical Details

### Signal Strength Range
- **0-255**: Zigbee signal strength
- **200+**: Excellent signal
- **150-199**: Good signal
- **100-149**: Fair signal
- **<100**: Poor signal

### Motion Confidence Calculation
```python
variance = abs(current_signal - baseline_signal)
confidence = min(1.0, variance / 50.0)  # Scale with variance
```

### API Response Format
- **light_id**: Identifier of the light that detected motion
- **room**: Room name (from light grouping)
- **confidence**: Motion detection confidence (0.0-1.0)
- **timestamp**: ISO 8601 timestamp of detection
- **signal_strength**: Current signal strength reading
- **variance**: Signal variance from baseline

## Integration Examples

### Security System Integration
```python
# Motion detected - trigger security actions
if motion_event['confidence'] > 0.7:
    await security_system.alert_motion(
        room=motion_event['room'],
        confidence=motion_event['confidence']
    )
    await camera_system.start_recording()
    await lighting_system.turn_on_security_lights()
```

### Smart Home Automation
```python
# Motion in hallway - turn on lights
if motion_event['room'] == 'Hallway':
    await hue_system.set_scene('hallway_bright')
    await audio_system.play_welcome_message()
```

## Performance Considerations

- **Battery Impact**: Minimal impact on battery-powered lights
- **Network Load**: Low bandwidth usage for signal monitoring
- **CPU Usage**: Lightweight signal analysis on bridge/server
- **False Positives**: Tune confidence thresholds for your environment

## Limitations

- **Bridge Pro Only**: Requires Philips Hue Bridge Pro
- **Zigbee Only**: Only works with Zigbee-connected lights
- **Range Limited**: Detection range depends on light placement
- **Environmental Factors**: Signal can be affected by walls, furniture, etc.

## Future Enhancements

- **Multi-Room Correlation**: Combine signals from multiple rooms for better detection
- **Presence Learning**: Learn normal movement patterns to reduce false positives
- **Guest Detection**: Distinguish between residents and visitors
- **Activity Recognition**: Detect different types of movement (walking, running, etc.)
