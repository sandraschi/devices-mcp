# Polling Manager Documentation

## Overview

The Devices MCP system monitors many hardware components (cameras, energy meters, weather stations, etc.). To prevent aggressive polling that causes high CPU usage, a centralized **Polling Manager** has been implemented.

## Problem

Previously, each monitoring component had its own polling loop with hardcoded intervals. This led to:
- **Aggressive polling** (0.01-0.03s intervals) causing 30%+ CPU usage
- **No coordination** between different polling tasks
- **No error handling** or backoff strategies
- **Difficult to monitor** and debug polling behavior

## Solution: Centralized Polling Manager

The `PollingManager` class (`src/devices_mcp/polling_manager.py`) provides:

1. **Unified Configuration**: All polling tasks registered in one place
2. **Minimum Interval Enforcement**: Prevents aggressive polling based on priority
3. **Exponential Backoff**: Automatically backs off on errors
4. **Health Monitoring**: Tracks success/error rates and statistics
5. **Graceful Management**: Start/stop/enable/disable tasks dynamically

## Priority Levels

| Priority | Minimum Interval | Use Case |
|----------|-----------------|----------|
| `CRITICAL` | 1 second | System health, security monitoring |
| `HIGH` | 5 seconds | Camera status, energy monitoring |
| `NORMAL` | 15 seconds | Metrics collection, logs |
| `LOW` | 60 seconds | Historical data, analytics |

## Polling Loops Found and Fixed

### 1. Camera Capture Loops ✅ FIXED

**Files:**
- `src/devices_mcp/camera/laptop.py`
- `src/devices_mcp/camera/webcam.py`
- `src/devices_mcp/web/server.py`

**Issue:** Polling at 30 FPS (0.03s intervals) for frame capture

**Fix:**
- Increased sleep interval from 0.03s to 0.1s (10 FPS)
- Added error handling to ensure sleep always executes
- Added retry logic for failed reads

**Status:** ✅ Fixed - No longer uses polling manager (streaming-specific)

### 2. Metrics Collection Service ✅ MIGRATED

**File:** `src/devices_mcp/metrics_service.py`

**Issue:** Manual `while True` loop with 30-second intervals

**Fix:**
- Migrated to use `PollingManager`
- Registered as `metrics_collection` task with `NORMAL` priority
- Interval: 30 seconds (meets minimum requirement)

**Status:** ✅ Migrated to polling manager

### 3. Edge Collectors ✅ MIGRATED

**File:** `src/devices_mcp/edge/agents.py`

**Issue:** Manual `while True` loop with configurable scrape intervals

**Fix:**
- Migrated to use `PollingManager`
- Priority determined dynamically based on scrape interval
- Each collector registered as `edge_collector_{host}` task

**Status:** ✅ Migrated to polling manager

### 4. Wien Energie Smart Meter ⚠️ NO ACTIVE LOOP

**File:** `src/devices_mcp/ingest/wien_energie.py`

**Status:** Configuration exists for polling (default 60s), but no active polling loop found. Methods are called on-demand.

**Recommendation:** If polling is needed, register with polling manager.

### 5. Tapo P115 Smart Plugs ⚠️ NO ACTIVE LOOP

**File:** `src/devices_mcp/ingest/tapo_p115.py`

**Status:** No active polling loop. Methods are called on-demand.

**Recommendation:** If polling is needed, register with polling manager.

## Usage Examples

### Registering a New Polling Task

```python
from devices_mcp.polling_manager import get_polling_manager, PollingPriority

manager = get_polling_manager()

async def my_monitoring_task():
    # Your monitoring logic here
    data = await fetch_sensor_data()
    process_data(data)

# Register the task
task = manager.register_task(
    name="sensor_monitoring",
    callback=my_monitoring_task,
    interval_seconds=30.0,  # Will be enforced to minimum based on priority
    priority=PollingPriority.NORMAL,
    enabled=True,
)

# Start the manager (if not already running)
await manager.start()
```

### Checking Task Status

```python
manager = get_polling_manager()

# Get status of specific task
status = manager.get_task_status("metrics_collection")
print(f"Last run: {status['last_run']}")
print(f"Error rate: {status['error_rate']}")

# Get all tasks status
all_status = manager.get_all_status()
print(f"Total tasks: {all_status['total_tasks']}")
print(f"Active tasks: {all_status['active_tasks']}")
```

### Health Monitoring

```python
manager = get_polling_manager()

health = manager.get_health()
if not health['healthy']:
    print(f"Unhealthy tasks: {health['unhealthy_tasks']}")
```

## Configuration

The polling manager enforces minimum intervals based on priority:

- **CRITICAL**: 1 second minimum
- **HIGH**: 5 seconds minimum
- **NORMAL**: 15 seconds minimum
- **LOW**: 60 seconds minimum

If you try to register a task with an interval below the minimum, it will be automatically adjusted and a warning will be logged.

## Error Handling

The polling manager implements exponential backoff:

- On error, the interval is multiplied by `backoff_factor` (default 1.0, but increases with error count)
- Maximum backoff is 5 minutes (300 seconds)
- Error count decreases gradually on successful runs
- All errors are logged with context

## Benefits

1. **Reduced CPU Usage**: Enforced minimum intervals prevent aggressive polling
2. **Better Error Handling**: Exponential backoff prevents hammering failed services
3. **Centralized Monitoring**: All polling activity visible in one place
4. **Dynamic Management**: Enable/disable tasks without restarting
5. **Health Tracking**: Monitor success rates and identify problematic tasks

## Migration Checklist

When adding new monitoring code:

- [ ] Check if it needs polling (vs. on-demand)
- [ ] Register with `PollingManager` instead of manual `while True` loops
- [ ] Choose appropriate priority level
- [ ] Set reasonable interval (will be enforced to minimum)
- [ ] Test error handling and backoff behavior

## Future Improvements

- [ ] Web UI for monitoring polling tasks
- [ ] Configurable backoff strategies per task
- [ ] Metrics export for Prometheus
- [ ] Alerting on high error rates
- [ ] Dynamic interval adjustment based on load
