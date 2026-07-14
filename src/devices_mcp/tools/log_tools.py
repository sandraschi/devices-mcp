"""MCP tools for querying the in-memory message/log store with filters."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

_READ_ONLY = {"readOnly": True}


def register_log_tools(mcp: FastMCP) -> None:
    """Register log query tools with the FastMCP instance."""

    @mcp.tool(annotations=_READ_ONLY, version="0.1.0")
    async def query_logs(
        source: str | None = None,
        level: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Query the in-memory message/log store. Filters by source, level, or keyword.

        ## Parameters
        - source: Filter by log source (device ID or component name)
        - level: Filter by level (info, warning, alarm)
        - search: Case-insensitive keyword search in message text
        - limit: Max entries to return (default 50, max 500)

        ## Return Format
        {"success": bool, "logs": list, "count": int, "filtered_by": dict}

        ## Examples
        await query_logs(level="alarm", limit=10)
        await query_logs(source="camera_1")
        await query_logs(search="offline")
        """
        from devices_mcp.core.messaging_service import get_messaging_service

        svc = get_messaging_service()
        messages = list(svc.messages)

        filtered = messages
        if source:
            filtered = [m for m in filtered if m.source == source]
        if level:
            filtered = [m for m in filtered if m.severity.value == level.lower()]
        if search:
            search_lower = search.lower()
            filtered = [m for m in filtered if search_lower in (m.title + " " + m.description).lower()]

        truncated = filtered[-limit:] if len(filtered) > limit else filtered

        entries = [
            {
                "timestamp": m.timestamp.isoformat(),
                "level": m.severity.value,
                "source": m.source,
                "message": f"{m.title}: {m.description}",
                "category": m.category.value,
                "id": m.id,
            }
            for m in truncated
        ]

        return {
            "success": True,
            "logs": entries,
            "count": len(entries),
            "total_matching": len(filtered),
            "filtered_by": {"source": source, "level": level, "search": search, "limit": limit},
        }
