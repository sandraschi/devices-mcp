"""
Messages Portmanteau Tool - real operations on the device messaging store.

Consolidates status, query, ack and clear for
``devices_mcp.core.messaging_service`` - the same store the webapp and the
fleet priority feed use. Replaces the previous mock implementation.
"""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from devices_mcp.core.messaging_service import (
    MessageCategory,
    MessageSeverity,
    get_messaging_service,
)

logger = logging.getLogger(__name__)

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

MESSAGES_ACTIONS = {
    "status": "Summary of the message store (counts per severity, unacked totals)",
    "list": "Query messages with optional severity/category/source/acknowledged filters",
    "ack": "Acknowledge a message by id, all of a severity, or everything (severity='all')",
    "clear": "Delete messages by id, by severity, or everything (clear_all + confirm=True)",
}


def register_messages_management_tool(mcp: FastMCP) -> None:
    """Register the messages management portmanteau tool (real store)."""

    @mcp.tool(annotations=_MUTATING)
    async def messages_management(
        action: str,
        message_id: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 50,
        acknowledged: bool | None = None,
        clear_all: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """
        [RATIONALE] Device messaging store operations consolidated into one
        tool: the store (status/query/ack/clear) is small and always used
        together; separate tools would bloat the registry for no gain.

        Operations:
        - status: counts per severity (info/warning/alarm), unacked total and
          unacked alarms, oldest/newest timestamp.
        - list: query messages; filters severity, category, source,
          acknowledged (true/false), limit. Returns newest first.
        - ack: mark as acknowledged. message_id for one, severity for all of
          a severity, or severity='all' for everything.
        - clear: DESTRUCTIVE. Delete by message_id, by severity, or all
          (clear_all=True). Deleting everything requires confirm=True.

        Args:
            action (str, required): "status", "list", "ack", "clear".
            message_id (str | None): target message for ack/clear.
            severity (str | None): filter ("info"/"warning"/"alarm") for
              list/ack/clear; "all" for ack everything.
            category (str | None): filter for list (e.g. "device_connection").
            source (str | None): filter for list (device id).
            limit (int): max messages for list (default 50, max 500).
            acknowledged (bool | None): list filter; None = both.
            clear_all (bool): clear everything (needs confirm=True).
            confirm (bool): required for clear_all.

        ## Return Format
        {"success": bool, "message": str, "action": str,
         "data": {...operation-specific}}

        ## Examples
        messages_management(action="status")
        messages_management(action="list", severity="alarm", acknowledged=False, limit=20)
        messages_management(action="ack", message_id="msg_1_1234")
        messages_management(action="clear", clear_all=True, confirm=True)
        """
        try:
            if action not in MESSAGES_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(MESSAGES_ACTIONS)}",
                    "action": action,
                }
            messaging = get_messaging_service()

            if action == "status":
                msgs = list(messaging.messages)
                sev_counts = {"info": 0, "warning": 0, "alarm": 0}
                unacked_alarms = 0
                unacked_total = 0
                for m in msgs:
                    sev_counts[m.severity.value] = sev_counts.get(m.severity.value, 0) + 1
                    if not m.acknowledged:
                        unacked_total += 1
                        if m.severity == MessageSeverity.ALARM:
                            unacked_alarms += 1
                timestamps = [m.timestamp for m in msgs]
                return {
                    "success": True,
                    "message": f"Store: {len(msgs)} messages, {unacked_alarms} unacked alarms",
                    "action": action,
                    "data": {
                        "total": len(msgs),
                        "by_severity": sev_counts,
                        "unacked_total": unacked_total,
                        "unacked_alarms": unacked_alarms,
                        "oldest": min(timestamps).isoformat() if timestamps else None,
                        "newest": max(timestamps).isoformat() if timestamps else None,
                    },
                }

            if action == "list":
                sev = MessageSeverity(severity) if severity else None
                cat = MessageCategory(category) if category else None
                msgs = messaging.get_messages(
                    severity=sev,
                    category=cat,
                    source=source,
                    limit=max(1, min(limit, 500)),
                    acknowledged=acknowledged,
                )
                return {
                    "success": True,
                    "message": f"{len(msgs)} messages",
                    "action": action,
                    "data": {"count": len(msgs), "messages": [m.to_dict() for m in msgs]},
                }

            if action == "ack":
                count = 0
                if message_id:
                    count = 1 if messaging.acknowledge_message(message_id) else 0
                elif severity and severity == "all":
                    count = messaging.acknowledge_all()
                elif severity:
                    count = messaging.acknowledge_all(severity=MessageSeverity(severity))
                else:
                    return {
                        "success": False,
                        "message": "ack requires message_id, severity, or severity='all'",
                        "action": action,
                    }
                return {
                    "success": True,
                    "message": f"Acknowledged {count} message(s)",
                    "action": action,
                    "data": {"acknowledged_count": count},
                }

            if action == "clear":
                if clear_all and not confirm:
                    return {
                        "success": False,
                        "message": "clear_all requires confirm=True (destructive, not reversible)",
                        "action": action,
                    }
                count = 0
                for m in list(messaging.messages):
                    if clear_all:
                        drop = True
                    elif message_id:
                        drop = m.id == message_id
                    elif severity:
                        drop = m.severity.value == severity
                    else:
                        drop = False
                    if drop:
                        messaging.delete_message(m.id)
                        count += 1
                return {
                    "success": True,
                    "message": f"Cleared {count} message(s)",
                    "action": action,
                    "data": {"cleared_count": count},
                }

            return {"success": False, "message": f"Unhandled action '{action}'", "action": action}
        except ValueError as exc:
            return {"success": False, "message": str(exc), "action": action}
        except Exception as exc:
            logger.exception("messages_management %s failed", action)
            return {"success": False, "message": str(exc), "action": action}
