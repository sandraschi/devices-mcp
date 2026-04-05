# 🔧 Tool Consolidation Plan

**Goal**: Reduce from 64 tools to 35-40 tools (50% reduction) using portmanteau tools

## 📊 Current State Analysis

### Tool Categories (64 total):
- **Utility**: 50 tools (MISCLASSIFIED - should be properly categorized)
- **PTZ**: 8 tools → **Target: 2 tools**
- **System**: 3 tools → **Target: 2 tools**
- **Configuration**: 3 tools → **Target: 2 tools**

## 🎯 Consolidation Strategy

### 1. **PTZ Tools** (8 → 2 tools)
```
Current:
- MovePTZTool
- GetPTZPositionTool
- StopPTZTool
- GetPTZPresetsTool
- SavePTZPresetTool
- RecallPTZPresetTool
- GoToHomePTZTool

Consolidated:
- PTZControlTool (move, position, stop)
- PTZPresetTool (presets, save, recall, home)
```

### 2. **Camera Management** (9 → 3 tools)
```
Current:
- ListCamerasTool
- AddCameraTool
- RemoveCameraTool
- ConnectCameraTool
- DisconnectCameraTool
- SetActiveCameraTool
- GetCameraInfoTool
- GetCameraStatusTool
- ManageCameraGroupsTool

Consolidated:
- CameraManagementTool (list, add, remove)
- CameraConnectionTool (connect, disconnect, set active)
- CameraInfoTool (info, status, groups)
```

### 3. **Energy Management** (8 → 2 tools)
```
Current:
- GetSmartPlugStatusTool
- ControlSmartPlugTool
- GetEnergyConsumptionTool
- GetEnergyCostAnalysisTool
- GetTapoP115DetailedStatsTool
- SetTapoP115EnergySavingModeTool
- GetTapoP115PowerScheduleTool
- SetEnergyAutomationTool

Consolidated:
- EnergyManagementTool (status, control, consumption, cost)
- TapoP115Tool (P115-specific features)
```

### 4. **Weather Management** (5 → 2 tools)
```
Current:
- GetNetatmoStationsTool
- GetNetatmoWeatherDataTool
- GetNetatmoHistoricalDataTool
- ConfigureNetatmoAlertsTool
- GetNetatmoHealthReportTool

Consolidated:
- NetatmoWeatherTool (stations, current data)
- NetatmoAnalysisTool (historical, alerts, health)
```

### 5. **Alarm Management** (5 → 2 tools)
```
Current:
- GetNestProtectStatusTool
- GetNestProtectAlertsTool
- GetNestProtectBatteryStatusTool
- TestNestProtectDeviceTool
- CorrelateNestCameraEventsTool

Consolidated:
- NestProtectTool (status, alerts, battery)
- SecurityAnalysisTool (testing, correlation)
```

### 6. **Media Tools** (6 → 2 tools)
```
Current:
- CaptureImageTool
- CaptureStillTool
- AnalyzeImageTool
- StartRecordingTool
- StopRecordingTool
- GetStreamURLTool

Consolidated:
- ImageCaptureTool (capture, still, analyze)
- VideoRecordingTool (start, stop, stream)
```

### 7. **System Tools** (6 → 2 tools)
```
Current:
- GetSystemInfoTool
- GetLogsTool
- HealthCheckTool
- RebootCameraTool
- StatusTool
- HelpTool (duplicate)

Consolidated:
- SystemInfoTool (info, logs, health)
- SystemControlTool (reboot, status)
```

### 8. **Onboarding** (4 → 1 tool)
```
Current:
- DiscoverDevicesTool
- ConfigureDeviceTool
- CompleteOnboardingTool
- GetOnboardingProgressTool

Consolidated:
- DeviceOnboardingTool (all onboarding functions)
```

### 9. **Configuration** (3 → 2 tools)
```
Current:
- SetLEDEnabledTool
- SetMotionDetectionTool
- SetPrivacyModeTool

Consolidated:
- DeviceSettingsTool (LED, motion detection)
- PrivacySettingsTool (privacy mode + other privacy features)
```

### 10. **Specialized Tools** (Keep as-is)
```
Keep separate (unique functionality):
- FindSimilarImagesTool
- SecurityScanTool
- PerformanceAnalyzerTool
- SmartAutomationTool
- SceneAnalyzerTool
- GrafanaMetricsTool
- GrafanaSnapshotsTool
- ViennaDashboardTool
- GetTapoP115DataStorageInfoTool
```

## 📈 Expected Results

### Before: 64 tools
- PTZ: 8 tools
- Camera: 9 tools
- Energy: 8 tools
- Weather: 5 tools
- Alarms: 5 tools
- Media: 6 tools
- System: 6 tools
- Onboarding: 4 tools
- Configuration: 3 tools
- Specialized: 10 tools

### After: 35 tools
- PTZ: 2 tools
- Camera: 3 tools
- Energy: 2 tools
- Weather: 2 tools
- Alarms: 2 tools
- Media: 2 tools
- System: 2 tools
- Onboarding: 1 tool
- Configuration: 2 tools
- Specialized: 10 tools
- New Categories: 9 tools

## 🚀 Implementation Benefits

1. **Reduced Cognitive Load**: 50% fewer tools to choose from
2. **Better Organization**: Logical grouping of related functions
3. **Improved UX**: Single tools for common workflows
4. **Maintained Functionality**: All features preserved
5. **Claude/Cursor Friendly**: Manageable tool count

## ⚡ Implementation Plan

1. **Phase 1**: Create portmanteau tool classes
2. **Phase 2**: Implement multi-function parameters
3. **Phase 3**: Update tool registration
4. **Phase 4**: Test functionality preservation
5. **Phase 5**: Remove old individual tools
6. **Phase 6**: Update documentation

## 🎯 Success Metrics

- **Tool Count**: 64 → 35 tools (45% reduction)
- **Functionality**: 100% preserved
- **Performance**: Maintained or improved
- **Usability**: Enhanced through logical grouping
