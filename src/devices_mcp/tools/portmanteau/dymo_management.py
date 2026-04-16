"""
Dymo Management Portmanteau Tool

Consolidates all Dymo LabelManager PnP operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.integrations.dymo_client import DymoClient

logger = logging.getLogger(__name__)

DYMO_ACTIONS = {
    "status": "Get printer status and tape info",
    "print_label": "Print a single label",
    "print_batch": "Print multiple labels",
    "shopping_labels": "Create shopping list labels",
    "inventory_labels": "Create inventory labels",
}


def register_dymo_management_tool(mcp: FastMCP) -> None:
    """Register the Dymo management portmanteau tool."""

    @mcp.tool()
    async def dymo_management(
        action: Literal[
            "status",
            "print_label",
            "print_batch",
            "shopping_labels",
            "inventory_labels",
        ],
        text: str | None = None,
        labels: list[str] | None = None,
        items: list[Any] | None = None,
        tape_size: Literal["6mm", "9mm", "12mm", "19mm", "24mm"] = "12mm",
        tape_color: str = "black_on_white",
        include_checkboxes: bool = True,
    ) -> dict[str, Any]:
        """
        Comprehensive Dymo LabelManager PnP management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 5+ separate tools (one per operation), this tool consolidates related
        label printing operations into a single interface. Prevents tool explosion (5+ tools -> 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.

        Args:
            action (Literal, required): The operation to perform. Must be one of:
                - "status": Get printer connectivity and tape status.
                - "print_label": Print a single text label (requires: text).
                - "print_batch": Print multiple labels (requires: labels).
                - "shopping_labels": Create labels with check-boxes for shopping (requires: labels or items).
                - "inventory_labels": Create labels with location/quantity (requires: items as list of dicts).

            text (str | None): Text for a single label. Required for: print_label.

            labels (List[str] | None): List of strings for batch/shopping labels.

            items (List[Dict] | None): List of items for inventory labels.
                Format: [{"name": "Item", "location": "A1", "quantity": "10"}]

            tape_size (Literal): Tape width in mm. Default: 12mm.

            tape_color (str): Tape color combination. Default: black_on_white.

            include_checkboxes (bool): Add checkboxes to shopping labels. Default: True.

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False

        Examples:
            # Check printer status
            result = await dymo_management(action="status")

            # Print a single label
            result = await dymo_management(action="print_label", text="LAB SAMPLES")

            # Create shopping labels
            result = await dymo_management(action="shopping_labels", labels=["Milk", "Eggs", "Bread"])
        """
        try:
            client = DymoClient()

            if action == "status":
                data = await client.get_status()
                return {"success": True, "action": action, "data": data}

            if action == "print_label":
                if not text:
                    return {
                        "success": False,
                        "error": "text is required for print_label action",
                    }
                data = await client.print_label(text, tape_size=tape_size, tape_color=tape_color)
                return {"success": True, "action": action, "data": data}

            if action == "print_batch":
                if not labels:
                    return {
                        "success": False,
                        "error": "labels list is required for print_batch action",
                    }
                data = await client.print_batch(labels, tape_size=tape_size, tape_color=tape_color)
                return {"success": True, "action": action, "data": data}

            if action == "shopping_labels":
                target_labels = labels or []
                if not target_labels and items:
                    target_labels = [str(i) for i in items]

                if not target_labels:
                    return {
                        "success": False,
                        "error": "labels or items list is required for shopping_labels action",
                    }

                data = await client.create_shopping_labels(
                    target_labels,
                    tape_size=tape_size,
                    tape_color=tape_color,
                    include_checkboxes=include_checkboxes,
                )
                return {"success": True, "action": action, "data": data}

            if action == "inventory_labels":
                if not items:
                    return {
                        "success": False,
                        "error": "items list (of dicts) is required for inventory_labels action",
                    }

                # Basic validation of items
                processed_items = []
                for item in items:
                    if isinstance(item, dict):
                        processed_items.append(item)
                    else:
                        processed_items.append({"name": str(item)})

                data = await client.create_inventory_labels(processed_items, tape_size=tape_size, tape_color=tape_color)
                return {"success": True, "action": action, "data": data}

            return {"success": False, "error": f"Action '{action}' not implemented"}

        except Exception as e:
            logger.exception("Error in dymo management action '{action}':")
            return {
                "success": False,
                "error": f"Failed to execute action '{action}': {e!s}",
            }
