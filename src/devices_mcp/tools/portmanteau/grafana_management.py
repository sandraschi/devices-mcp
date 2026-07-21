"""
Grafana Management Portmanteau Tool
Consolidates all Grafana integration operations into a single tool with action-based interface.
Currently supports dashboard data, metrics export, and snapshot management.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

logger = logging.getLogger(__name__)
GRAFANA_ACTIONS = {
    "get_metrics": "Export camera metrics for Grafana HTTP data source",
    "get_dashboard": "Get dashboard data for Grafana panels",
    "create_snapshot": "Create camera snapshot for Grafana image panels",
    "get_vienna_dashboard": "Get Vienna-specific security dashboard data",
    "export_timeseries": "Export time-series data for Grafana",
}


def register_grafana_management_tool(mcp: FastMCP) -> None:
    """Register the Grafana management portmanteau tool."""

    @mcp.tool(annotations=_READ_ONLY)
    async def grafana_management(
        action: Literal[
            "get_metrics",
            "get_dashboard",
            "create_snapshot",
            "get_vienna_dashboard",
            "export_timeseries",
        ],
        camera_id: str | None = None,
        dashboard_type: str = "security",
        time_range: str = "24h",
        format_type: str = "json",
    ) -> dict[str, Any]:
        """
        Comprehensive Grafana management portmanteau tool for dashboard integration.
        PORTMANTEAU PATTERN RATIONALE:
        Consolidates Grafana operations into a single interface to reduce tool explosion
        while maintaining full functionality. Supports metrics export, dashboard data,
        snapshots, and Vienna-specific localization.
        Args:
            action (Literal, required): The Grafana operation to perform. Must be one of:
                - "get_metrics": Export comprehensive camera metrics for Grafana
                - "get_dashboard": Get dashboard panel data
                - "create_snapshot": Create camera snapshot for image panels
                - "get_vienna_dashboard": Get Vienna-specific security dashboard (German labels)
                - "export_timeseries": Export time-series data for Grafana
            camera_id (str | None): Specific camera for snapshot/metrics operations
            dashboard_type (str): Type of dashboard data (default: "security")
                - "security", "performance", "energy", "weather"
            time_range (str): Time range for data export (default: "24h")
                - "1h", "24h", "7d", "30d"
            format_type (str): Export format (default: "json")
                - "json", "prometheus", "influxdb"
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Grafana-compatible data (metrics, dashboard data, snapshots, etc.)
                - error (str | None): Error message if success is False
        Examples:
            # Export metrics for Grafana
            result = await grafana_management(action="get_metrics")
            # Get Vienna security dashboard data
            result = await grafana_management(action="get_vienna_dashboard")
            # Create camera snapshot for image panel
            result = await grafana_management(action="create_snapshot", camera_id="living_room_cam")
            # Export time-series data
            result = await grafana_management(action="export_timeseries", time_range="7d")
            # Get performance dashboard data
            result = await grafana_management(action="get_dashboard", dashboard_type="performance")
        """
        try:
            if action not in GRAFANA_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(GRAFANA_ACTIONS.keys())}",
                }
            logger.info(f"Executing Grafana management action: {action}")
            # Import Grafana tools
            if action == "get_metrics":
                from ...tools.grafana.metrics import GrafanaMetricsTool

                tool = GrafanaMetricsTool()
                result = await tool.execute()
            elif action == "get_vienna_dashboard":
                from ...tools.grafana.dashboards import ViennaDashboardTool

                tool = ViennaDashboardTool()
                result = await tool.execute()
            elif action == "create_snapshot":
                if not camera_id:
                    return {
                        "success": False,
                        "message": "camera_id is required for create_snapshot",
                        "error": "camera_id is required for create_snapshot",
                    }
                from ...tools.grafana.snapshots import GrafanaSnapshotsTool

                tool = GrafanaSnapshotsTool()
                result = await tool.execute(camera_id=camera_id)
            elif action == "get_dashboard":
                # For now, use Vienna dashboard as the main dashboard tool
                from ...tools.grafana.dashboards import ViennaDashboardTool

                tool = ViennaDashboardTool()
                result = await tool.execute()
                # Add dashboard type context
                if "dashboard_data" in result:
                    result["dashboard_data"]["type"] = dashboard_type
            elif action == "export_timeseries":
                # Use metrics tool for time-series export
                from ...tools.grafana.metrics import GrafanaMetricsTool

                tool = GrafanaMetricsTool()
                result = await tool.execute()
                # Add time_range context if provided
                if time_range and "data" in result:
                    result["time_range"] = time_range
                # Format for specified export type
                if format_type == "prometheus":
                    result = _format_prometheus_metrics(result)
                elif format_type == "influxdb":
                    result = _format_influxdb_metrics(result)
            else:
                return {
                    "success": False,
                    "message": f"Action '{action}' not implemented",
                    "error": f"Action '{action}' not implemented",
                }
            return {
                "success": True,
                "action": action,
                "data": result,
                "format": format_type,
            }
        except Exception as e:
            logger.exception("Error in Grafana management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute Grafana action '{action}': {e!s}",
            }


def _format_prometheus_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """Format metrics data for Prometheus ingestion."""
    prometheus_lines = []
    # Convert camera metrics to Prometheus format
    for camera_id, camera_data in data.get("cameras", {}).items():
        labels = f'camera="{camera_id}"'
        if "motion_events_1h" in camera_data:
            prometheus_lines.append(f"tapo_motion_events_1h{{{labels}}} {camera_data['motion_events_1h']}")
        if "recording_duration_today" in camera_data:
            prometheus_lines.append(
                f"tapo_recording_duration_today{{{labels}}} {camera_data['recording_duration_today']}"
            )
        if "storage_used_mb" in camera_data:
            prometheus_lines.append(f"tapo_storage_used_mb{{{labels}}} {camera_data['storage_used_mb']}")
    # System metrics
    system = data.get("system", {})
    prometheus_lines.extend(
        [
            f"tapo_active_cameras {system.get('active_cameras', 0)}",
            f"tapo_total_cameras {system.get('total_cameras', 0)}",
            f"tapo_alerts_pending {system.get('alerts_pending', 0)}",
        ]
    )
    return {
        "format": "prometheus",
        "metrics": prometheus_lines,
        "timestamp": data.get("timestamp"),
    }


def _format_influxdb_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """Format metrics data for InfluxDB ingestion."""
    influx_lines = []
    timestamp = data.get("timestamp", "")
    # Convert camera metrics to InfluxDB line protocol
    for camera_id, camera_data in data.get("cameras", {}).items():
        fields = []
        if "motion_events_1h" in camera_data:
            fields.append(f"motion_events_1h={camera_data['motion_events_1h']}")
        if "recording_duration_today" in camera_data:
            fields.append(f"recording_duration_today={camera_data['recording_duration_today']}")
        if "storage_used_mb" in camera_data:
            fields.append(f"storage_used_mb={camera_data['storage_used_mb']}")
        if fields:
            influx_lines.append(f"tapo_camera,camera={camera_id} {','.join(fields)} {timestamp}")
    # System metrics
    system = data.get("system", {})
    system_fields = [
        f"active_cameras={system.get('active_cameras', 0)}",
        f"total_cameras={system.get('total_cameras', 0)}",
        f"alerts_pending={system.get('alerts_pending', 0)}",
    ]
    influx_lines.append(f"tapo_system {','.join(system_fields)} {timestamp}")
    return {
        "format": "influxdb",
        "lines": influx_lines,
        "timestamp": timestamp,
    }
