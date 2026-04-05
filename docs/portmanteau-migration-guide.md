# Portmanteau Tools Migration Guide

## From Brand-Based to Functionality-Based Organization

### **Current Problem:**
```
User wants to control lights:
- Do they use lighting_management? (Hue only)
- Or tapo_control? (includes Hue + Tapo lights)
- Confusion and overlap!
```

### **Solution:**
```
User wants to control lights:
- Use lighting_management (ALL lights, any brand)
- Simple, intuitive, no confusion!
```

---

## Migration Steps

## Phase 1: Lighting Consolidation ✅

### **Current State:**
- `lighting_management`: Hue lights only
- `tapo_control`: Hue lights + Tapo lights (DUPLICATE!)

### **Migration:**
```bash
# Move all Hue functions from tapo_control to lighting_management
# Update lighting_management to support both Hue and Tapo
# Remove Hue functions from tapo_control
```

### **After Migration:**
```python
# lighting_management supports:
LIGHTING_BRANDS = ["hue", "tapo", "future_brands"]

# tapo_control becomes Tapo-only:
TAPO_ONLY = ["cameras", "plugs", "kitchen_devices"]
```

## Phase 2: Kitchen Consolidation

### **Current State:**
- `kitchen_management`: Kitchen appliances
- `tapo_control`: Kitchen appliances (DUPLICATE!)

### **Migration:**
```bash
# Move kitchen functions from tapo_control to kitchen_management
# kitchen_management becomes the single source for all kitchen control
```

## Phase 3: Camera Unification

### **Current State:**
- `camera_management`: Some cameras
- `ring_management`: Ring cameras
- `tapo_control`: Tapo cameras

### **Migration:**
```bash
# Merge all camera functions into camera_management
# Support multiple brands: Tapo, Ring, IP cameras, webcams
```

## Phase 4: Energy Devices

### **Current State:**
- `energy_management`: Energy monitoring
- `tapo_control`: Tapo plugs

### **Migration:**
```bash
# Move plug control from tapo_control to energy_management
# energy_management handles all energy devices
```

---

## Tool Mapping (Before → After)

### **Lighting Control:**
```
BEFORE:
- lighting_management: Hue lights
- tapo_control: Hue + Tapo lights

AFTER:
- lighting_management: ALL lights (Hue + Tapo + future)
- tapo_control: No lighting functions
```

### **Camera Control:**
```
BEFORE:
- camera_management: Limited cameras
- ring_management: Ring cameras
- tapo_control: Tapo cameras

AFTER:
- camera_management: ALL cameras (Tapo + Ring + IP + webcams)
- ring_management: DEPRECATED (merged into camera_management)
```

### **Energy Control:**
```
BEFORE:
- energy_management: Energy monitoring
- tapo_control: Smart plugs

AFTER:
- energy_management: ALL energy devices (plugs + monitors + sensors)
- tapo_control: No plug functions
```

### **Kitchen Control:**
```
BEFORE:
- kitchen_management: Kitchen appliances
- tapo_control: Kitchen appliances

AFTER:
- kitchen_management: ALL kitchen appliances
- tapo_control: No kitchen functions
```

---

## New Tool Responsibilities

### **lighting_management**
**Purpose:** All smart lighting control
**Supports:** Hue, Tapo, future brands
**Actions:** on/off, brightness, color, effects, scenes, groups

### **camera_management**
**Purpose:** All camera and video device control
**Supports:** Tapo, Ring, IP cameras, webcams
**Actions:** streaming, recording, motion detection, PTZ

### **energy_management**
**Purpose:** All energy monitoring and control
**Supports:** Smart plugs, energy sensors, power monitors
**Actions:** on/off, power monitoring, cost analysis, scheduling

### **kitchen_management**
**Purpose:** All smart kitchen appliance control
**Supports:** Kettles, coffee makers, refrigerators, ovens
**Actions:** on/off, temperature control, timers, monitoring

### **security_management**
**Purpose:** All security and safety systems (burglar, fire, gas, water, emergency)
**Supports:** Cameras, doorbells, sensors, fire/gas/water/burglar alarms, emergency systems
**Actions:** arm/disarm, alerts, monitoring, access control, safety tests, emergency response

### **system_management** (Consolidated)
**Purpose:** System control + configuration + analytics + diagnostics
**Supports:** System health, configuration, performance monitoring, diagnostics
**Actions:** System status, config management, analytics, diagnostics, maintenance

### **media_management** (Consolidated)
**Purpose:** ALL streaming/recording (video + audio + screen capture)
**Supports:** Camera streams, audio, screen recording, media management
**Actions:** Streaming control, recording, media storage, quality settings

### **communication_management** (Consolidated)
**Purpose:** Alerts + messages + notifications (multi-channel)
**Supports:** Dashboard, email, SMS, push notifications, voice alerts
**Actions:** Send alerts, manage notifications, configure channels, message history

### **robotics_management** (Specialized)
**Purpose:** Robot control systems (Moorebot Scout + others)
**Supports:** Autonomous robots, robotic arms, mobile robots
**Actions:** Movement control, autonomous modes, sensor monitoring, safety

### **medical_management** (Specialized)
**Purpose:** Health monitoring devices (wearables + sensors)
**Supports:** Medical sensors, health monitors, telemedicine devices
**Actions:** Vital monitoring, alerts, data management, emergency response

### **ai_analysis** (Specialized)
**Purpose:** Computer vision & AI analysis (object detection + insights)
**Supports:** Image/video analysis, pattern recognition, anomaly detection
**Actions:** Object detection, scene analysis, predictive insights, automation

### **emergency_management** (Specialized)
**Purpose:** Emergency response & panic systems
**Supports:** Emergency protocols, evacuation systems, crisis management
**Actions:** Emergency activation, evacuation, crisis coordination, safety

### **access_management** (Specialized)
**Purpose:** Door locks & access control systems
**Supports:** Smart locks, access cards, biometric systems, remote access
**Actions:** Lock/unlock, access codes, permissions, security logs

### **maintenance_management** (Specialized)
**Purpose:** Device maintenance & diagnostics
**Supports:** Firmware updates, battery monitoring, sensor calibration
**Actions:** Health checks, updates, calibration, preventive maintenance

### **climate_management** (New)
**Purpose:** Temperature and climate control
**Supports:** Sensors, thermostats, weather stations
**Actions:** temperature monitoring, climate control, scheduling

### **automation_management**
**Purpose:** Smart home automation and scenes
**Supports:** Cross-brand scene management
**Actions:** scenes, schedules, rules, voice integration

---

## Implementation Plan

### **Week 1: Analysis & Planning**
- [x] Document current tool overlaps
- [x] Define new tool boundaries
- [x] Create migration plan

### **Week 2: Lighting Migration**
- [ ] Update lighting_management to support multiple brands
- [ ] Move Hue functions from tapo_control
- [ ] Test multi-brand lighting control

### **Week 3: Camera Unification**
- [ ] Merge camera functions into camera_management
- [ ] Add Ring camera support
- [ ] Deprecate ring_management

### **Week 4: Energy Consolidation**
- [ ] Move plug control to energy_management
- [ ] Add energy monitoring features
- [ ] Update tapo_control

### **Week 5: Testing & Validation**
- [ ] Test all migrated functions
- [ ] Update documentation
- [ ] User acceptance testing

---

## Backward Compatibility

### **During Migration:**
- Keep old tools functional but mark as deprecated
- Provide clear migration path in error messages
- Support both old and new APIs

### **Migration Helpers:**
```python
# Old way (still works during migration)
tapo_control("turn_on_light", light_id="hue_lamp_1")

# New way (recommended)
lighting_management("turn_on_light", light_id="hue_lamp_1")
```

### **Deprecation Timeline:**
- **Phase 1:** Mark tapo_control lighting functions deprecated
- **Phase 2:** Mark separate kitchen/camera tools deprecated
- **Phase 3:** Remove deprecated functions (6 months later)

---

## Benefits Achieved

### **User Experience:**
- ✅ **Intuitive:** One tool per function
- ✅ **Complete:** All devices of same type together
- ✅ **Brand Agnostic:** Works regardless of manufacturer

### **Developer Experience:**
- ✅ **Clear:** No more overlap confusion
- ✅ **Maintainable:** Related code together
- ✅ **Extensible:** Easy to add new brands

### **System Health:**
- ✅ **No Duplicates:** Single source of truth
- ✅ **Consistent:** Same patterns across brands
- ✅ **Future-Proof:** Easy to add new device types
