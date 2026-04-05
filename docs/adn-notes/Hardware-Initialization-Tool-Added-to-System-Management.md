# Hardware Initialization Tool Added to System Management

## Overview

Added an `initialize` action to the `system_management` portmanteau tool to provide explicit control over camera and hardware initialization.

## Problem Solved

Previously, when `TAPO_MCP_SKIP_HARDWARE_INIT=true` was set, cameras were not initialized at startup. Users had no way to explicitly initialize cameras after the server started.

## Solution

Added `initialize` action to the system management tool:

```python
# Initialize all cameras and hardware
result = await system_management(action="initialize")
```

## Implementation Details

- **Location**: `src/devices_mcp/tools/portmanteau/system_management.py`
- **Action**: `"initialize"` - Initialize all cameras and hardware
- **Parameters**: None required
- **Function**: Calls `initialize_all_hardware()` from the core hardware initialization module
- **Timeout**: Uses the same 20-second timeout as startup initialization

## Benefits

1. **User Control**: Explicit control over when initialization happens
2. **Error Handling**: Can retry initialization if it fails
3. **Status Checking**: Users can check initialization results
4. **Performance**: Avoids long startup times while providing on-demand initialization
5. **Flexibility**: Initialize all hardware components at user command

## Usage Pattern

```python
# Check system status first
status = await system_management(action="status")

# Initialize if needed
if not all(camera['connected'] for camera in status['cameras']):
    init_result = await system_management(action="initialize")
    print(f"Initialization completed: {init_result}")
```

## Integration with SEP-1577

This tool complements the agentic security workflow by providing explicit hardware initialization capabilities for automated security workflows.

## Status

✅ **Implemented** - Ready for use in Cursor MCP integration
