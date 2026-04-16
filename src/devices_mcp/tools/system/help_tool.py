"""
Help tool for Devices MCP that provides comprehensive documentation.
"""

from typing import Any

from pydantic import ConfigDict, Field

from devices_mcp.tools.base_tool import BaseTool, ToolCategory, tool


@tool(name="help")
class HelpTool(BaseTool):
    """Tool to get help about Devices MCP functionality and Grafana integration."""

    class Meta:
        name = "help"
        category = ToolCategory.SYSTEM

    section: str | None = Field(default="all", description="Section of the help to display")

    model_config = ConfigDict(json_schema_extra={"enum": ["all", "core", "grafana", "api", "ptz", "troubleshooting"]})

    async def execute(self) -> dict[str, Any]:
        """Return help information based on the requested section."""
        help_sections = {
            "core": self._get_core_help(),
            "grafana": self._get_grafana_help(),
            "api": self._get_api_help(),
            "ptz": self._get_ptz_help(),
            "troubleshooting": self._get_troubleshooting_help(),
        }

        if self.section == "all":
            return {"status": "success", "help": "\n\n".join(help_sections.values())}
        help_text = help_sections.get(self.section, "Invalid help section. Try: " + ", ".join(help_sections.keys()))
        return {"status": "success", "help": help_text}

    def _get_core_help(self) -> str:
        return """# Devices MCP - Core Functionality

## Camera Management
- List all cameras: `list_cameras()`
- Get camera details: `get_camera_details(camera_id: str)`
- Add camera: `add_camera(host: str, username: str, password: str)`
- Remove camera: `remove_camera(camera_id: str)`

## Stream Management
- Start stream: `start_stream(camera_id: str, stream_type: str = "rtsp")`
- Stop stream: `stop_stream(stream_id: str)`
- List active streams: `list_streams()`"""

    def _get_grafana_help(self) -> str:
        return """# Grafana Integration

## Setup
1. Install the Tapo Camera Stream plugin in Grafana
2. Add a new panel and select "Tapo Camera Stream"
3. Configure the camera stream URL and authentication

## Dashboard Features
- Real-time video streaming
- PTZ controls
- Motion detection alerts
- System health metrics
- Historical data visualization

## Available Variables
- `$camera`: Select camera
- `$stream_type`: RTSP, HLS, or MJPEG
- `$quality`: Stream quality (HD/SD)"""

    def _get_api_help(self) -> str:
        return """# API Endpoints

## Camera Control
- `GET /api/v1/cameras`: List all cameras
- `GET /api/v1/cameras/{camera_id}`: Get camera details
- `POST /api/v1/cameras`: Add new camera
- `DELETE /api/v1/cameras/{camera_id}`: Remove camera

## Stream Control
- `POST /api/v1/streams/start`: Start a new stream
- `DELETE /api/v1/streams/{stream_id}`: Stop a stream"""

    def _get_ptz_help(self) -> str:
        return """# PTZ Controls

## Basic Movement
- `move_ptz(camera_id: str, direction: str, speed: int = 50)`
  - Directions: up, down, left, right, up-left, up-right, down-left, down-right
  - Speed: 1-100

## Presets
- `save_preset(camera_id: str, preset_name: str)`
- `go_to_preset(camera_id: str, preset_name: str)`
- `delete_preset(camera_id: str, preset_name: str)`

## Advanced Controls
- `set_home_position(camera_id: str)`
- `reset_position(camera_id: str)`"""

    def _get_troubleshooting_help(self) -> str:
        return """# Troubleshooting

## Common Issues
1. **No Video Feed**
   - Check camera network connectivity
   - Verify credentials
   - Ensure correct stream URL

2. **PTZ Not Working**
   - Check if camera supports PTZ
   - Verify user permissions
   - Check for firmware updates

3. **Grafana No Data**
   - Verify plugin installation
   - Check API endpoint accessibility
   - Review browser console for errors"""
