# Robotics Integration: Technical Architecture

**Timestamp**: 2026-01-07
**Component**: `devices-mcp` -> `robots.py`

## Overview
The robotics module (`src/devices_mcp/web/api/robots.py`) provides a unified REST API and WebSocket interface for controlling both physical units (Unitree, Moorebot) and virtual digital twins (Unity3D/VRChat).

## Core Logic: `robots.py`
This module serves as the **Robotics Gateway**. It maintains an in-memory registry (`_robots`) of all known entities and routes commands to the appropriate integration client.

### Key Components
1.  **Registry**: `_robots: Dict[str, Robot]` stores the live state of all robots.
2.  **Telemetry Loop**: Real-time polling of battery, position, and sensor data.
3.  **Command Routing**:
    - **Physical**: Routes to `MoorebotScoutClient` or `UnitreeGo2Client`.
    - **Virtual**: Routes to `VbotClient` (see below).

## Orchestration: `robotics-mcp` & `vbot_client.py`
Virtual robots are managed via the `VbotClient` (`src/devices_mcp/integrations/vbot_client.py`), which acts as an HTTP client for the **Robotics MCP Server**.

### Communication Protocol
- **Transport**: HTTP POST
- **Endpoint**: `/api/v1/tools/{tool_name}` (FastMCP convention)
- **Tools Used**:
    - `robot_virtual`: Lifecycle management (CRUD), state synchronization.
    - `robot_behavior`: Movement primitives, animation, camera feeds.
    - `robotics_system`: System status and health checks.

### Workflow: Virtual Robot Creation
When `POST /api/robots/create_vbot` is called:
1.  `robots.py` calls `_vbot_client.create_vbot()`.
2.  `VbotClient` sends a POST request to `robotics-mcp` calling the `robot_virtual` tool with `operation="create"`.
3.  **Robotics MCP** orchestrates the instantiation:
    - **Unity3D**: Via `unity3d-mcp`, spawns the prefab at the specified coordinates.
    - **state**: Updates the global virtual robot registry.
4.  `robots.py` receives the new `robot_id` and adds it to its local `_robots` registry.

## Unity/VRChat Integration
The `robotics-mcp` server acts as the bridge to 3D environments.
- **Unity3D**: Connected via `unity3d-mcp` (C# scripts listening for MCP commands).
- **VRChat**: Connected via `vrchat-mcp` (OSC protocol for avatar parameter control).

This architecture ensures `devices-mcp` remains decoupled from specific 3D engines, communicating only via standardized MCP tool calls.
