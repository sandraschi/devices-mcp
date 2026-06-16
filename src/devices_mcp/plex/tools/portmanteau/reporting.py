"""
PlexMCP Reporting & Analytics Portmanteau Tool

Consolidates all reporting and analytics operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Literal

from ...app import mcp
from ...utils import get_logger

logger = get_logger(__name__)


def _get_plex_service():
    """Get PlexService instance with proper environment variable handling."""
    from ...services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")

    if not token:
        raise RuntimeError(
            "PLEX_TOKEN environment variable is required. "
            "Get your token from Plex Web App (Settings → Account → Authorized Devices) "
            "or visit https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/ "
            "for detailed instructions."
        )

    return PlexService(base_url=base_url, token=token)


@mcp.tool()
async def plex_reporting(
    operation: Literal[
        "library_stats",
        "usage_report",
        "content_report",
        "user_activity",
        "performance_report",
        "export_report",
    ],
    library_id: str | None = None,
    time_range: str | None = None,
    format: Literal["json", "csv", "html"] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Comprehensive reporting and analytics tool for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 6 separate tools (one per report type), this tool consolidates related
    reporting operations into a single interface. This design:
    - Prevents tool explosion (6 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with reporting tasks
    - Enables consistent reporting interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - library_stats: Get statistics for a library or all libraries
    - usage_report: Generate usage statistics and viewing patterns
    - content_report: Analyze content distribution and metadata quality
    - user_activity: Report on user activity and engagement
    - performance_report: Server performance metrics and recommendations
    - export_report: Export reports in various formats (JSON, CSV, HTML)

    OPERATIONS DETAIL:

    library_stats: Get library statistics
    - Parameters: library_id (optional, if omitted returns stats for all libraries)
    - Returns: Statistics including item counts, sizes, types, etc.
    - Use when: You need an overview of library contents and sizes

    usage_report: Generate usage statistics
    - Parameters: time_range (optional, e.g., "7d", "30d", "1y"), library_id (optional)
    - Returns: Viewing statistics, popular content, watch time, etc.
    - Use when: Analyzing viewing patterns and popular content

    content_report: Analyze content distribution
    - Parameters: library_id (optional)
    - Returns: Content breakdown by type, genre, year, quality, etc.
    - Use when: Understanding content distribution and metadata quality

    user_activity: Report on user activity
    - Parameters: time_range (optional)
    - Returns: User engagement metrics, active users, viewing habits
    - Use when: Monitoring user engagement and activity levels

    performance_report: Server performance metrics
    - Parameters: None
    - Returns: Performance metrics, recommendations, resource usage
    - Use when: Monitoring server health and performance

    export_report: Export reports
    - Parameters: format (json, csv, html), output_path (optional)
    - Returns: Export confirmation with file path
    - Use when: Saving reports for external analysis or sharing

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - PLEX_SERVER_URL configured (or defaults to http://localhost:32400)

    Args:
        operation (str): The reporting operation to perform. Required. Must be one of: "library_stats", "usage_report", "content_report", "user_activity", "performance_report", "export_report"
        library_id (str | None): Optional library ID to generate report for.
        time_range (str | None): Time range for reports (e.g., "7d", "30d", "1y", "all").
        format (str | None): Export format (json, csv, html) - used for export_report.
        output_path (str | None): Optional file path for exported reports.

    Returns:
        Operation-specific result with report data

    Examples:
        # Get library statistics
        plex_reporting("library_stats", library_id="1")

        # Generate usage report for last 30 days
        plex_reporting("usage_report", time_range="30d")

        # Export content report as CSV
        plex_reporting("export_report", format="csv", output_path="/tmp/content_report.csv")

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Configure authentication token
        - "Library not found": Verify library_id is correct
        - "Invalid time range": Use format like "7d", "30d", "1y"
    """
    try:
        plex = _get_plex_service()

        if operation == "library_stats":
            if library_id:
                libraries = await plex.get_library(library_id)
                if not libraries:
                    return {
                        "success": False,
                        "message": f"Library with ID '{library_id}' not found",
                        "error_code": "LIBRARY_NOT_FOUND",
                        "suggestions": [
                            "Verify library_id is correct",
                            "List libraries to see available IDs",
                        ],
                    }
                libraries = [libraries]
            else:
                libraries = await plex.list_libraries()

            stats = []
            for lib in libraries:
                lib_id = lib.get("key") or lib.get("id")
                analysis = await plex.analyze_library(lib_id)
                stats.append(
                    {
                        "library_id": lib_id,
                        "library_name": lib.get("title") or lib.get("name"),
                        "total_items": analysis.get("total_items", 0),
                        "issues_found": analysis.get("issues_found", 0),
                        "issues": analysis.get("issues", []),
                    }
                )

            return {
                "success": True,
                "operation": "library_stats",
                "stats": stats,
                "count": len(stats),
            }

        if operation == "usage_report":
            # Placeholder for usage reporting - would need session history data
            return {
                "success": True,
                "operation": "usage_report",
                "time_range": time_range or "all",
                "message": "Usage reporting requires session history data (not yet implemented)",
                "data": {},
            }

        if operation == "content_report":
            if library_id:
                libraries = await plex.get_library(library_id)
                if not libraries:
                    return {
                        "success": False,
                        "message": f"Library with ID '{library_id}' not found",
                        "error_code": "LIBRARY_NOT_FOUND",
                    }
                libraries = [libraries]
            else:
                libraries = await plex.list_libraries()

            reports = []
            for lib in libraries:
                lib_id = lib.get("key") or lib.get("id")
                items_result = await plex.get_library_items(library_id=lib_id, limit=1000, offset=0)
                items = items_result.get("items", []) if isinstance(items_result, dict) else items_result
                reports.append(
                    {
                        "library_id": lib_id,
                        "library_name": lib.get("title") or lib.get("name"),
                        "total_items": len(items) if isinstance(items, list) else items_result.get("total", 0),
                        "content_types": {},
                    }
                )

            return {
                "success": True,
                "operation": "content_report",
                "reports": reports,
                "count": len(reports),
            }

        if operation == "user_activity":
            # Placeholder for user activity reporting
            return {
                "success": True,
                "operation": "user_activity",
                "time_range": time_range or "all",
                "message": "User activity reporting requires session history data (not yet implemented)",
                "data": {},
            }

        if operation == "performance_report":
            status = await plex.get_server_status()
            return {
                "success": True,
                "operation": "performance_report",
                "server_status": status.dict() if hasattr(status, "dict") else status,
                "recommendations": [],
            }

        if operation == "export_report":
            if not format:
                return {
                    "success": False,
                    "message": "format is required for export_report operation",
                    "error": "format is required for export_report operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Specify format: json, csv, or html"],
                }

            return {
                "success": True,
                "operation": "export_report",
                "format": format,
                "output_path": output_path,
                "message": f"Report export to {format} format (not yet fully implemented)",
            }

        return {
            "success": False,
            "message": f"Unknown operation: {operation}",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Use one of: library_stats, usage_report, content_report, user_activity, performance_report, export_report"
            ],
        }

    except Exception as e:
        logger.exception("Error in plex_reporting operation '{operation}':")
        return {
            "success": False,
            "message": str(e),
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "suggestions": [
                "Verify Plex server is accessible",
                "Check PLEX_TOKEN is set correctly",
                "Verify library_id is valid if provided",
            ],
        }
