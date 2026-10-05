"""
Dymo Management Portmanteau Tool
Real Dymo label printing through the Windows print spooler (MobileLabeler, LabelManager).
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.integrations.dymo_client import DymoClient, DymoError

_MUTATING: dict[str, bool] = {}

logger = logging.getLogger(__name__)
DYMO_ACTIONS = {
    "status": "Find the installed DYMO printer and report its spooler status",
    "list_printers": "List every printer Windows knows about, flagging DYMO ones",
    "print_label": "Print a single text label (or preview it with dry_run)",
    "print_batch": "Print several labels, stopping at the first failure",
    "shopping_labels": "Print checkbox labels for a shopping list",
    "inventory_labels": "Print name / location / quantity labels",
}


def _failure(action: str, exc: DymoError) -> dict[str, Any]:
    return {
        "success": False,
        "action": action,
        "message": str(exc),
        "error": str(exc),
        "error_type": exc.error_type,
        "suggestions": exc.suggestions,
    }


def register_dymo_management_tool(mcp: FastMCP) -> None:
    """Register the Dymo management portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def dymo_management(
        action: Literal["status", "list_printers", "print_label", "print_batch", "shopping_labels", "inventory_labels"],
        text: str | None = None,
        labels: list[str] | None = None,
        items: list[Any] | None = None,
        tape_size: Literal["6mm", "9mm", "12mm", "19mm", "24mm"] = "12mm",
        include_checkboxes: bool = True,
        copies: int = 1,
        dry_run: bool = False,
        printer_name: str | None = None,
        orientation: Literal["auto", "none", "cw", "ccw"] = "auto",
    ) -> dict[str, Any]:
        """
        Print labels on a DYMO label printer (MobileLabeler, LabelManager) via the Windows spooler.

        [RATIONALE] One portmanteau tool instead of six: all operations share the same printer
        lookup, rendering and error contract. Labels are rendered as bitmaps and sent through the
        installed DYMO driver (USB or Bluetooth), so no vendor SDK is needed.

        Verification status: UNVERIFIED against a physical DYMO printer. Use dry_run=True to render a
        PNG preview without printing, and "status" to see the driver's paper forms before the first print.

        Args:
            action (Literal, required): One of:
                - "status": Locate the DYMO printer; returns driver, port, spooler flags, paper forms.
                - "list_printers": All Windows printers, with is_dymo flags.
                - "print_label": Print one label (requires: text).
                - "print_batch": Print many labels (requires: labels, max 50).
                - "shopping_labels": Checkbox labels (requires: labels or items).
                - "inventory_labels": Name/location/quantity labels (requires: items as list of dicts).
            text (str | None): Label text; newlines make extra lines. Required for: print_label.
            labels (list[str] | None): Label texts. Required for: print_batch, shopping_labels.
            items (list[Any] | None): Items for shopping_labels (strings) or inventory_labels
                ([{"name": "Item", "location": "A1", "quantity": "10"}]).
            tape_size (Literal): Tape width, sets the render height. The cassette in the printer decides the
                real tape; the colour of the print is the ribbon's, not a software setting. Default 12mm.
            include_checkboxes (bool): Prefix shopping labels with "[ ] ". Default True.
            copies (int): Copies of each label, 1-10. Default 1.
            dry_run (bool): Render and save a PNG preview, send nothing. Default False.
            printer_name (str | None): Exact Windows printer name; default is the first DYMO printer.
            orientation (Literal): Rotate the bitmap to the driver's page: "auto" rotates landscape
                labels onto portrait pages. Default "auto".

        ## Return Format
            {"success": bool, "action": str, "data": {...}, "message": str}
            Failures: {"success": False, "error": str, "error_type": str, "suggestions": [str]} with
            error_type one of device_not_found, printer_fault, invalid_job, dependency_missing,
            unsupported_platform, print_failed, driver_error. Success for a print means
            data["sent"] is true: the spooler accepted the job.

        ## Examples
            await dymo_management(action="status")
            await dymo_management(action="print_label", text="Flour\\n2026-10", dry_run=True)
            await dymo_management(action="shopping_labels", labels=["Milk", "Eggs"])
        """
        try:
            client = DymoClient(printer_name=printer_name)
            kw: dict[str, Any] = {
                "tape_size": tape_size,
                "copies": copies,
                "dry_run": dry_run,
                "orientation": orientation,
            }

            if action == "status":
                return {"success": True, "action": action, "data": await client.get_status()}
            if action == "list_printers":
                printers = await client.list_printers()
                return {"success": True, "action": action, "data": {"printers": printers, "count": len(printers)}}
            if action == "print_label":
                if not text:
                    raise DymoError("text is required for print_label", "invalid_job")
                data = await client.print_label(text, **kw)
                msg = "Label rendered (dry run, nothing printed)" if dry_run else f"Printed on {data['printer']}"
                return {"success": True, "action": action, "data": data, "message": msg}
            if action in ("print_batch", "shopping_labels"):
                targets = labels or [str(i) for i in (items or [])]
                if not targets:
                    raise DymoError(f"labels (or items) is required for {action}", "invalid_job")
                if action == "print_batch":
                    data = await client.print_batch(targets, **kw)
                else:
                    data = await client.create_shopping_labels(targets, include_checkboxes=include_checkboxes, **kw)
                return _batch_result(action, data)
            if action == "inventory_labels":
                if not items:
                    raise DymoError("items (list of dicts) is required for inventory_labels", "invalid_job")
                normalised = [i if isinstance(i, dict) else {"name": str(i)} for i in items]
                return _batch_result(action, await client.create_inventory_labels(normalised, **kw))
            raise DymoError(f"unknown action '{action}'", "invalid_job", [f"Use one of {sorted(DYMO_ACTIONS)}"])
        except DymoError as exc:
            return _failure(action, exc)
        except Exception as exc:
            logger.exception("dymo_management '%s' failed", action)
            return {
                "success": False,
                "action": action,
                "message": f"Unexpected error in '{action}': {exc!s}",
                "error": str(exc),
                "error_type": "unexpected",
                "suggestions": ["Check the devices-mcp log for the traceback"],
            }


def _batch_result(action: str, data: dict[str, Any]) -> dict[str, Any]:
    ok = bool(data.get("success"))
    message = f"Printed {data['printed']}/{data['total_labels']} labels"
    out: dict[str, Any] = {"success": ok, "action": action, "data": data, "message": message}
    if not ok:
        out.update({"error": data.get("error", message), "error_type": data.get("error_type", "print_failed")})
    return out
