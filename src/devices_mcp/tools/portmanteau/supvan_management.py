"""
Supvan / Katasymbol Management Portmanteau Tool
Label printing on Supvan E10/E11/E16 and T50M Pro printers, over BLE or USB.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.integrations.label_printers import supvan_client as sc
from devices_mcp.integrations.label_printers import supvan_proto as sp

_MUTATING: dict[str, bool] = {}

logger = logging.getLogger(__name__)
SUPVAN_ACTIONS = {
    "models": "List supported models with their verification status",
    "discover": "Scan BLE and USB for Supvan printers",
    "status": "Query a printer: name, status flags, loaded label",
    "print_label": "Render and print a text or image label (or preview with dry_run)",
}


def _failure(action: str, exc: sc.SupvanError) -> dict[str, Any]:
    return {
        "success": False,
        "action": action,
        "message": str(exc),
        "error": str(exc),
        "error_type": exc.error_type,
        "suggestions": exc.suggestions,
    }


def register_supvan_management_tool(mcp: FastMCP) -> None:
    """Register the Supvan management portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def supvan_management(
        action: Literal["models", "discover", "status", "print_label"],
        target: str | None = None,
        model: Literal["e10", "e11", "e16", "t50m_pro"] | None = None,
        text: str | None = None,
        image_path: str | None = None,
        label_width_mm: int | None = None,
        length_mm: int | None = None,
        density: int = 4,
        copies: int = 1,
        dry_run: bool = False,
        flip_head_axis: bool = False,
        scan_seconds: float = 6.0,
    ) -> dict[str, Any]:
        """
        Control Supvan / Katasymbol thermal label printers (E10, E11, E16, T50M Pro) without the vendor app.

        [RATIONALE] One portmanteau tool for discovery, status and printing: the three steps share
        the target/model resolution and the error contract. The wire protocol is a Python port of the
        reverse-engineered heeen/supvan-cups and efcroasdell/supvan-cups drivers.

        Verification status: the protocol and print path are tested against a mock printer that decodes
        every byte (target "mock://<model>"). Real BLE and USB transports are UNVERIFIED on hardware, as
        is the label orientation; check the first print and use flip_head_axis if it is mirrored. The E16
        has no capture or hardware test at all. Use "models" to see per-model verification.

        Args:
            action (Literal, required): One of:
                - "models": Supported models and what has been verified for each.
                - "discover": Scan BLE and USB (scan_seconds long). Reports what could not be scanned and why.
                - "status": Query a printer (requires: target; model for usb://, ble:// without a known name).
                - "print_label": Print a label (requires: target, exactly one of text / image_path, model).
            target (str | None): "mock://<model>", "ble://<address>" or "usb://". Required for: status, print_label.
            model (Literal | None): e10, e11, e16 or t50m_pro. Required for ble:// and usb:// targets.
            text (str | None): Label text (newlines make extra lines). For print_label.
            image_path (str | None): Local image file, scaled to the tape width and dithered. For print_label.
            label_width_mm (int | None): Label width across the tape in mm; default E-series 12 mm, T50M Pro 30 mm.
            length_mm (int | None): Minimum label length in mm; default fits the content.
            density (int): Burn density 0-15 (T-series) or 0-19 (E-series). Default 4.
            copies (int): Copies, 1-10. Default 1.
            dry_run (bool): Render and encode the job, save a PNG preview, send nothing. Default False.
            flip_head_axis (bool): Mirror the label across the tape if the first print is flipped. Default False.
            scan_seconds (float): BLE scan duration for discover. Default 6.

        ## Return Format
            {"success": bool, "action": str, "data": {...}, "message": str}
            Failures: {"success": False, "error": str, "error_type": str, "suggestions": [str]} with error_type
            one of invalid_job, invalid_model, invalid_target, unsupported_transport, not_implemented,
            connect_failed, no_response, printer_fault, timeout, protocol_error. For print_label,
            data["sent"] is true only after the printer reported the job complete.

        ## Examples
            await supvan_management(action="models")
            await supvan_management(action="print_label", target="mock://e11", text="Pantry", dry_run=True)
            await supvan_management(action="print_label", target="ble://AA:BB:CC:DD:EE:FF", model="e11", text="Hi")
        """
        try:
            if action == "models":
                models = [
                    {
                        "key": m.key,
                        "name": m.marketing_name,
                        "transports": list(m.transports),
                        "printhead_dots": m.printhead_dots,
                        "verification": m.verification,
                    }
                    for m in sp.MODELS.values()
                ]
                return {"success": True, "action": action, "data": {"models": models}}
            if action == "discover":
                return {"success": True, "action": action, "data": await sc.discover(scan_seconds)}
            if not target:
                raise sc.SupvanError(
                    "target is required", "invalid_target", ["Use mock://<model>, ble://<address> or usb://"]
                )
            if action == "status":
                return {"success": True, "action": action, "data": await sc.get_status(target, model)}
            if action == "print_label":
                data = await sc.print_label(
                    target,
                    text=text,
                    image_path=image_path,
                    model=model,
                    label_width_mm=label_width_mm,
                    length_mm=length_mm,
                    density=density,
                    copies=copies,
                    dry_run=dry_run,
                    flip_head_axis=flip_head_axis,
                )
                message = "Job encoded (dry run, nothing sent)" if dry_run else f"Printed {copies} label(s)"
                return {"success": True, "action": action, "data": data, "message": message}
            raise sc.SupvanError(f"unknown action '{action}'", "invalid_job", [f"Use one of {sorted(SUPVAN_ACTIONS)}"])
        except sc.SupvanError as exc:
            return _failure(action, exc)
        except Exception as exc:
            logger.exception("supvan_management '%s' failed", action)
            return {
                "success": False,
                "action": action,
                "message": f"Unexpected error in '{action}': {exc!s}",
                "error": str(exc),
                "error_type": "unexpected",
                "suggestions": ["Check the devices-mcp log for the traceback"],
            }
