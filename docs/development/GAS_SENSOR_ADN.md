# Domestic Gas Sensor Integration - ADN

**Timestamp**: 2025-01-17
**Status**: PLANNING - Research Complete
**Tags**: gas-detection, safety, natural-gas, propane, co-detection

## Quick Summary

Comprehensive plan for integrating domestic gas leak detection sensors (natural gas, propane, CO) into the home security system. Critical safety feature for homes with gas cooking and boilers.

## Gas Types & Detection

### Natural Gas (Methane)
- **Placement**: Near ceiling (6-12 inches from top)
- **LEL**: 5% concentration
- **Sources**: Stoves, ovens, water heaters, boilers

### Propane/LPG
- **Placement**: Near floor (6-12 inches from bottom)
- **LEL**: 2.1% concentration
- **Sources**: Portable stoves, outdoor grills, some boilers

### Carbon Monoxide (CO)
- **Placement**: Breathing level (5-6 feet)
- **Danger**: 50 ppm immediate danger
- **Sources**: Incomplete combustion from gas appliances

## Recommended Sensors

### Commercial (Best Options)
1. **DeNova Detect** - 10-year battery, Amazon Sidewalk, ~$100-150
2. **Kidde Smart** - Wi-Fi, IFTTT, budget option ~$50-80
3. **Grus Smart** - Multi-gas, Wi-Fi, ~$80-120

### DIY (Advanced Users)
- **ESP32 + MQ-5** (natural gas) - ~$15-25
- **ESP32 + MQ-6** (LPG) - ~$15-25
- **ESPHome firmware** - Easy MQTT integration

## Integration Methods

1. **Wi-Fi**: Direct integration (DeNova, Kidde, Grus)
2. **MQTT**: Best for DIY sensors (ESP32)
3. **Zigbee/Z-Wave**: Some commercial sensors
4. **RF433MHz**: IK-W6 and alarm systems

## Emergency Automation

- **Gas Shutoff Valve**: Auto-shutoff on critical detection
- **Ventilation**: Auto-activate fans on warning
- **Emergency Services**: Auto-call 911 on emergency (with delay)
- **Voice Alerts**: Immediate voice warnings

## Implementation Timeline

- **Weeks 1-4**: Commercial sensor integration
- **Weeks 5-6**: Dashboard & alerts
- **Weeks 7-8**: DIY sensor support (MQTT)
- **Weeks 9-10**: Automation & testing

**Total**: 10 weeks (2.5 months)

## Key Safety Notes

- **Placement Critical**: Wrong placement = useless detection
- **False Positives**: Proper calibration essential
- **Redundancy**: Multiple sensors recommended
- **Battery Backup**: Essential for power outages

## Related Documents

- `docs/DOMESTIC_GAS_SENSOR_INTEGRATION_PLAN.md` - Full detailed plan
- `docs/EMERGENCY_DETECTION_AND_VOICE_INTEGRATION_PLAN.md` - Emergency response system

---

**Last Updated**: 2025-01-17
