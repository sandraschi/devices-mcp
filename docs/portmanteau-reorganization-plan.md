# Portmanteau Tools Reorganization Plan

## Current Issues (Brand-Based Organization)

The current portmanteau tools are organized by brand/protocol, creating confusion and overlap:

### **Current Problems:**
- `tapo_control` handles Tapo devices + Hue lights + kitchen appliances
- `lighting_management` also handles Hue lights (DUPLICATE!)
- `kitchen_management` exists separately but `tapo_control` also handles kitchen
- Users don't care about brands - they want functionality

### **Current Tool Overlap:**
```
tapo_control:       Tapo cams | Tapo plugs | Hue lights | Kitchen appliances
lighting_management:           Hue lights | Scenes | Effects
kitchen_management:                     Kitchen appliances
camera_management:    Tapo cams | (presumably other cameras)
```

## Proposed Solution (Functionality-Based Organization)

### **New Organization Principle:**
**One tool per function, not per brand.** Users want to control "lights" not "Hue vs Tapo lights".

### **Proposed Functionality-Based Tools:**

### **Consolidated Tool Organization (16 Tools Total):**

#### **Core Functionality (7 tools):**
1. **lighting_management** - ALL smart lighting (Hue + Tapo + future brands)
2. **camera_management** - ALL cameras (Tapo + Ring + webcams + IP cameras)
3. **energy_management** - ALL energy devices (plugs + monitors + sensors)
4. **kitchen_management** - ALL kitchen appliances (kettles + ovens + refrigerators)
5. **security_management** - ALL security & safety (burglar + fire + gas + water + emergency)
6. **climate_management** - ALL climate control (temperature + humidity + HVAC)
7. **automation_management** - Scenes, schedules, rules, voice integration

#### **Extended Functionality (3 tools):**
8. **system_management** - System control + configuration + analytics + diagnostics
9. **media_management** - ALL streaming/recording (video + audio + screen capture)
10. **communication_management** - Alerts + messages + notifications (multi-channel)

#### **Specialized Tools (6 tools):**
11. **robotics_management** - Robot control systems (Moorebot Scout + others)
12. **medical_management** - Health monitoring devices (wearables + sensors)
13. **ai_analysis** - Computer vision & AI analysis (object detection + insights)
14. **emergency_management** - Emergency response & panic systems
15. **access_management** - Door locks & access control systems
16. **maintenance_management** - Device maintenance & diagnostics

## Migration Plan

### **Phase 1: Consolidate Lighting**
1. Merge `tapo_control` Hue functions into `lighting_management`
2. Remove Hue functions from `tapo_control`
3. Update `lighting_management` to support both Hue and Tapo lights

### **Phase 2: Consolidate Kitchen**
1. Merge `tapo_control` kitchen functions into `kitchen_management`
2. Remove kitchen functions from `tapo_control`
3. `tapo_control` becomes Tapo-specific only

### **Phase 3: Create Climate Management**
1. Extract temperature/humidity from various tools
2. Create dedicated `climate_management` tool
3. Integrate weather station data

### **Phase 4: Enhance Camera Management**
1. Merge Ring camera functions into `camera_management`
2. Add support for additional camera brands
3. Consolidate all camera operations

## Benefits

### **For Users:**
- ✅ **Intuitive**: "lights" tool controls all lights regardless of brand
- ✅ **No Confusion**: No more wondering which tool to use
- ✅ **Complete**: All devices of same type in one place

### **For Developers:**
- ✅ **Clear Separation**: One responsibility per tool
- ✅ **Easier Maintenance**: Related functionality together
- ✅ **Brand Agnostic**: Easy to add new device brands

### **For Integration:**
- ✅ **Consistent API**: Similar functions across brands
- ✅ **Unified Experience**: Same interface for all devices
- ✅ **Future-Proof**: Easy to add new brands

## Implementation Notes

### **Comprehensive Security:**
Security management includes ALL safety systems:
- Burglar protection (cameras, sensors, alarms)
- Fire safety (smoke detectors, fire alarms)
- Gas safety (leak detectors, CO monitors)
- Water safety (flood sensors, leak detectors)
- Emergency systems (panic buttons, medical alerts)

See [[Comprehensive Security Management Concept]] for details.

### **Backward Compatibility:**
- Keep old tools as deprecated aliases during transition
- Provide migration guide for existing users
- Gradual rollout to avoid breaking changes

### **Multi-Brand Support:**
- Abstract brand-specific code behind common interfaces
- Configuration-driven brand selection
- Plugin architecture for easy brand additions

### **Tool Registration:**
- Tools register based on available hardware
- Configuration determines which brands are active
- Graceful degradation when hardware unavailable

## Success Criteria

### **User Experience:**
- [ ] Users can control all lights through one "lighting" command
- [ ] Camera operations unified regardless of brand
- [ ] Security encompasses all safety systems (fire, gas, water, burglar)
- [ ] No more confusion about which tool to use

### **Developer Experience:**
- [ ] Clear separation of concerns
- [ ] Easy to add new device brands
- [ ] Consistent code patterns across tools

### **System Health:**
- [ ] No duplicate functionality
- [ ] Proper error handling for unavailable devices
- [ ] Clean tool registration and discovery
