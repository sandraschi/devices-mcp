"""Dymo label printer client (Windows print spooler backend).

Prints through the Windows spooler using whatever DYMO driver is installed (DYMO Connect
or DYMO Label installs one for the MobileLabeler / LabelManager families, over USB or
Bluetooth). Labels are rendered with Pillow and sent to the printer as a bitmap, so no
vendor SDK or proprietary protocol is involved.

What this does NOT do, deliberately:

* It does not report tape size, tape remaining, firmware or any other value the Windows
  spooler cannot tell it. Those fields are absent from ``get_status`` rather than invented.
* It never reports a label as printed unless the spooler accepted the job.

Status of verification: the spooler path is unverified against a real DYMO device. The page
geometry the driver exposes (and therefore the right ``orientation``) is learned from the first
real ``get_status`` / ``print_label`` call, which is why ``dry_run`` and the ``paper_forms``
field exist. The earlier version of this module returned hardcoded success and a fabricated
"85% tape" for every call; that is gone.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from PIL import Image

from .label_printers.raster import LabelRenderError, render_text_label, save_preview, to_mono
from .label_printers.supvan_client import label_dir

logger = logging.getLogger(__name__)

TAPE_SIZES_MM: dict[str, int] = {"6mm": 6, "9mm": 9, "12mm": 12, "19mm": 19, "24mm": 24}
RENDER_DPI = 300  # MobileLabeler prints at 300 dpi (user guide); the driver scales down for 180 dpi models
MAX_COPIES = 10
MAX_BATCH = 50

Orientation = Literal["auto", "none", "cw", "ccw"]

# Windows PRINTER_STATUS_* bits worth surfacing.
_STATUS_BITS: tuple[tuple[int, str], ...] = (
    (0x00000001, "paused"),
    (0x00000002, "error"),
    (0x00000004, "pending_deletion"),
    (0x00000008, "paper_jam"),
    (0x00000010, "paper_out"),
    (0x00000020, "manual_feed"),
    (0x00000040, "paper_problem"),
    (0x00000080, "offline"),
    (0x00000200, "busy"),
    (0x00000400, "printing"),
    (0x00000800, "output_bin_full"),
    (0x00002000, "waiting"),
    (0x00040000, "toner_low"),
    (0x00080000, "no_toner"),
    (0x00400000, "door_open"),
    (0x00200000, "not_available"),
    (0x01000000, "power_save"),
)


class DymoError(RuntimeError):
    """A Dymo operation failed. ``error_type`` is stable and machine-readable."""

    def __init__(
        self,
        message: str,
        error_type: str = "device_error",
        suggestions: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.suggestions = suggestions or []
        self.details = details or {}


class SpoolerBackend(Protocol):
    """The slice of the Windows spooler this client uses (also the seam for tests).

    ``hardware()`` is optional: backends without it simply report no hardware diagnostics.
    """

    def list_printers(self) -> list[dict[str, Any]]: ...

    def paper_forms(self, name: str, port: str) -> list[str]: ...

    def print_image(self, name: str, image: Image.Image, title: str, orientation: Orientation) -> dict[str, Any]: ...


def decode_status(bits: int) -> list[str]:
    return [label for mask, label in _STATUS_BITS if bits & mask]


_DYMO_USB_VID = "VID_0922"
_PNP_QUERY = (
    "Get-PnpDevice -ErrorAction SilentlyContinue | "
    "Where-Object { $_.InstanceId -match 'VID_0922' -or $_.FriendlyName -match 'dymo|mobile ?labeler' } | "
    "Select-Object Status, Class, FriendlyName, InstanceId | ConvertTo-Json -Compress"
)


def parse_pnp_json(raw: str) -> dict[str, list[dict[str, str]]]:
    """Split PowerShell ``Get-PnpDevice`` JSON into USB and Bluetooth DYMO devices.

    ``present`` is true for Status ``OK`` (Windows currently sees the device); ``Unknown`` means Windows only
    remembers it, e.g. a Bluetooth printer that is paired but switched off.
    """
    text = (raw or "").strip()
    if not text:
        return {"usb": [], "bluetooth": []}
    data = json.loads(text)
    rows = data if isinstance(data, list) else [data]
    out: dict[str, list[dict[str, str]]] = {"usb": [], "bluetooth": []}
    for row in rows:
        instance = str(row.get("InstanceId") or "")
        entry = {
            "name": str(row.get("FriendlyName") or ""),
            "class": str(row.get("Class") or ""),
            "status": str(row.get("Status") or ""),
            "present": str(row.get("Status") or "") == "OK",
            "instance_id": instance,
        }
        upper = instance.upper()
        if upper.startswith(("USB", "HID")) and _DYMO_USB_VID in upper:
            out["usb"].append(entry)
        elif upper.startswith("BTH"):
            out["bluetooth"].append(entry)
    return out


class Win32Spooler:
    """Real backend: pywin32 (win32print / win32ui) plus Pillow's ImageWin. Windows only."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise DymoError(
                "the Dymo spooler backend only works on Windows",
                "unsupported_platform",
                ["Run devices-mcp on the Windows PC the printer is attached to"],
            )
        try:
            import win32print  # noqa: F401
            import win32ui  # noqa: F401
        except ImportError as exc:
            raise DymoError("pywin32 is not installed", "dependency_missing", ["uv pip install pywin32"]) from exc

    def list_printers(self) -> list[dict[str, Any]]:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        out = []
        for _flags, _desc, name, _comment in win32print.EnumPrinters(flags, None, 1):
            handle = win32print.OpenPrinter(name)
            try:
                info = win32print.GetPrinter(handle, 2)
            finally:
                win32print.ClosePrinter(handle)
            out.append(
                {
                    "name": name,
                    "driver": info.get("pDriverName", ""),
                    "port": info.get("pPortName", ""),
                    "status_bits": int(info.get("Status", 0)),
                    "queued_jobs": int(info.get("cJobs", 0)),
                }
            )
        return out

    def hardware(self) -> dict[str, list[dict[str, str]]]:
        """DYMO USB / Bluetooth devices Windows knows about, whether or not a driver or queue exists."""
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PNP_QUERY],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.returncode != 0:
                # An empty result must mean "looked, found nothing", never "the query failed".
                raise DymoError(
                    f"device query failed (exit {proc.returncode}): {proc.stderr.strip()[:200]}", "diagnostics_failed"
                )
            return parse_pnp_json(proc.stdout)
        except DymoError:
            raise
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise DymoError(f"could not query Windows devices: {exc}", "diagnostics_failed") from exc

    def paper_forms(self, name: str, port: str) -> list[str]:
        import win32con
        import win32print

        try:
            names = win32print.DeviceCapabilities(name, port, win32con.DC_PAPERNAMES)
        except Exception:
            logger.warning("DeviceCapabilities(DC_PAPERNAMES) failed for %s", name, exc_info=True)
            return []
        return [str(n).strip("\x00") for n in (names or []) if str(n).strip("\x00")]

    def print_image(self, name: str, image: Image.Image, title: str, orientation: Orientation) -> dict[str, Any]:
        import win32con
        import win32ui
        from PIL import ImageWin

        dc = win32ui.CreateDC()
        dc.CreatePrinterDC(name)
        try:
            page_w = dc.GetDeviceCaps(win32con.HORZRES)
            page_h = dc.GetDeviceCaps(win32con.VERTRES)
            if page_w <= 0 or page_h <= 0:
                raise DymoError(f"driver reported an empty printable area ({page_w}x{page_h})", "driver_error")

            img = image.convert("RGB")
            landscape_img = img.width >= img.height
            rotate = {"none": None, "cw": -90, "ccw": 90}.get(orientation)
            if orientation == "auto" and landscape_img and page_h > page_w:
                rotate = -90
            if rotate is not None:
                img = img.rotate(rotate, expand=True)

            scale = min(page_w / img.width, page_h / img.height)
            w, h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
            img = img.resize((w, h), Image.Resampling.NEAREST)
            left, top = (page_w - w) // 2, (page_h - h) // 2

            dc.StartDoc(title)
            dc.StartPage()
            ImageWin.Dib(img).draw(dc.GetHandleOutput(), (left, top, left + w, top + h))
            dc.EndPage()
            dc.EndDoc()
            return {"page_px": [page_w, page_h], "drawn_px": [w, h], "rotated_degrees": rotate or 0}
        except DymoError:
            raise
        except Exception as exc:
            raise DymoError(f"the spooler rejected the job: {exc}", "print_failed") from exc
        finally:
            dc.DeleteDC()


def _verdict(
    hardware: dict[str, list[dict[str, str]]], printer_count: int, wanted: str | None
) -> tuple[str, str, list[str]]:
    """Classify a missing printer queue using what Windows can see of the hardware."""
    if wanted:
        return (
            "printer_not_installed",
            f"printer '{wanted}' is not installed in Windows",
            ["Check the exact name with dymo_management action=list_printers"],
        )
    attached = [d for d in hardware["usb"] + hardware["bluetooth"] if d["present"]]
    remembered = [d for d in hardware["usb"] + hardware["bluetooth"] if not d["present"]]
    if attached:
        names = ", ".join(sorted({d["name"] or d["instance_id"] for d in attached}))
        return (
            "driver_missing",
            f"a DYMO device is connected to Windows ({names}) but there is no DYMO printer queue: the driver is not installed",
            [
                "Install DYMO Connect (or DYMO Label) from dymo.com; it adds the MobileLabeler driver",
                "Re-run dymo_management action=diagnose afterwards",
            ],
        )
    if remembered:
        return (
            "device_off_or_out_of_range",
            "Windows remembers a DYMO device but it is not connected right now",
            ["Switch the printer on, plug in the USB cable or bring it into Bluetooth range", "Then re-run diagnose"],
        )
    return (
        "nothing_detected",
        f"no DYMO device is attached or paired and no DYMO printer is installed (Windows has {printer_count} other printers)",
        [
            "Charge or power the MobileLabeler and plug it in by USB (or pair it over Bluetooth in Windows settings)",
            "Run dymo_management action=diagnose again",
            "Then install DYMO Connect (or DYMO Label) for the driver",
        ],
    )


@dataclass
class _Selected:
    name: str
    driver: str
    port: str
    status_bits: int


class DymoClient:
    """Render and print labels on a DYMO printer through the Windows spooler."""

    def __init__(self, printer_name: str | None = None, backend: SpoolerBackend | None = None) -> None:
        self._printer_name = printer_name
        self._backend = backend

    def _spooler(self) -> SpoolerBackend:
        if self._backend is None:
            self._backend = Win32Spooler()
        return self._backend

    def _find(self) -> _Selected:
        printers = self._spooler().list_printers()
        wanted = (self._printer_name or "").lower()
        if wanted:
            hits = [p for p in printers if p["name"].lower() == wanted]
        else:
            hits = [p for p in printers if "dymo" in p["name"].lower() or "dymo" in p["driver"].lower()]
        if not hits:
            hardware = self._hardware()
            verdict, message, steps = _verdict(hardware, len(printers), self._printer_name)
            raise DymoError(message, "device_not_found", steps, {"verdict": verdict, "hardware": hardware})
        p = hits[0]
        return _Selected(p["name"], p["driver"], p["port"], p["status_bits"])

    def _hardware(self) -> dict[str, list[dict[str, str]]]:
        """Hardware diagnostics, or empty lists when the backend cannot provide them."""
        probe = getattr(self._spooler(), "hardware", None)
        if probe is None:
            return {"usb": [], "bluetooth": []}
        try:
            return probe()
        except DymoError:
            logger.warning("DYMO hardware diagnostics failed", exc_info=True)
            return {"usb": [], "bluetooth": []}

    async def diagnose(self) -> dict[str, Any]:
        """Where bring-up stands: printer queue, attached USB / paired Bluetooth hardware, and what to do next."""
        printers = await asyncio.to_thread(self._spooler().list_printers)
        hardware = await asyncio.to_thread(self._hardware)
        dymo = [p for p in printers if "dymo" in (p["name"] + p["driver"]).lower()]
        if dymo:
            return {
                "verdict": "ready" if "offline" not in decode_status(dymo[0]["status_bits"]) else "printer_offline",
                "printers": [{**p, "status": decode_status(p["status_bits"])} for p in dymo],
                "hardware": hardware,
                "next_steps": ["dymo_management action=print_label with dry_run=true, then a real print"],
            }
        verdict, message, steps = _verdict(hardware, len(printers), None)
        return {
            "verdict": verdict,
            "message": message,
            "printers": [],
            "hardware": hardware,
            "next_steps": steps,
        }

    # -- queries ---------------------------------------------------------------

    async def list_printers(self) -> list[dict[str, Any]]:
        printers = await asyncio.to_thread(self._spooler().list_printers)
        return [
            {**p, "status": decode_status(p["status_bits"]), "is_dymo": "dymo" in (p["name"] + p["driver"]).lower()}
            for p in printers
        ]

    async def get_status(self) -> dict[str, Any]:
        sel = await asyncio.to_thread(self._find)
        forms = await asyncio.to_thread(self._spooler().paper_forms, sel.name, sel.port)
        flags = decode_status(sel.status_bits)
        return {
            "printer": sel.name,
            "driver": sel.driver,
            "port": sel.port,
            "connected": "offline" not in flags and "not_available" not in flags,
            "status": flags,
            "paper_forms": forms[:30],
            "note": "tape size and remaining length are not available through the Windows spooler",
        }

    # -- rendering and printing ------------------------------------------------

    def render(self, text: str, tape_size: str = "12mm") -> Image.Image:
        if tape_size not in TAPE_SIZES_MM:
            raise DymoError(f"unknown tape size '{tape_size}'", "invalid_job", [f"Use one of {sorted(TAPE_SIZES_MM)}"])
        height_px = round(TAPE_SIZES_MM[tape_size] / 25.4 * RENDER_DPI)
        try:
            # Cap the glyph height at 12 mm so text on 19/24 mm tape is not poster-sized.
            cap_px = round(12 / 25.4 * RENDER_DPI)
            return to_mono(render_text_label(text, height_px, padding_px=10, max_font_px=cap_px))
        except LabelRenderError as exc:
            raise DymoError(str(exc), "invalid_job") from exc

    def _preview_path(self) -> Path:
        return label_dir() / f"dymo-preview-{time.time_ns() // 1_000_000}.png"

    async def print_label(
        self,
        text: str,
        *,
        tape_size: str = "12mm",
        copies: int = 1,
        dry_run: bool = False,
        orientation: Orientation = "auto",
    ) -> dict[str, Any]:
        if not 1 <= copies <= MAX_COPIES:
            raise DymoError(f"copies must be 1-{MAX_COPIES}", "invalid_job")
        image = self.render(text, tape_size)
        preview = save_preview(image, self._preview_path())
        result: dict[str, Any] = {
            "label_text": text,
            "tape_size": tape_size,
            "copies": copies,
            "image_px": list(image.size),
            "preview_png": str(preview),
            "sent": False,
        }
        if dry_run:
            return result

        sel = await asyncio.to_thread(self._find)
        flags = decode_status(sel.status_bits)
        blocking = [
            f for f in flags if f in {"offline", "paper_out", "paper_jam", "door_open", "error", "not_available"}
        ]
        if blocking:
            raise DymoError(
                f"printer '{sel.name}' reports: {', '.join(blocking)}",
                "printer_fault",
                ["Check power, cable or Bluetooth link, and the tape cassette"],
            )
        for _ in range(copies):
            geometry = await asyncio.to_thread(
                self._spooler().print_image, sel.name, image, "devices-mcp label", orientation
            )
        result.update({"sent": True, "printer": sel.name, "geometry": geometry})
        return result

    async def print_batch(self, labels: list[str], **kwargs: Any) -> dict[str, Any]:
        if not labels:
            raise DymoError("labels list is empty", "invalid_job")
        if len(labels) > MAX_BATCH:
            raise DymoError(f"at most {MAX_BATCH} labels per batch", "invalid_job")
        results: list[dict[str, Any]] = []
        for i, text in enumerate(labels):
            try:
                results.append({**await self.print_label(text, **kwargs), "batch_index": i})
            except DymoError as exc:
                # Stop at the first failure: later labels would fail the same way, and the
                # caller needs to know exactly how many physically printed.
                results.append({"label_text": text, "batch_index": i, "sent": False, "error": str(exc)})
                return {
                    "success": False,
                    "printed": sum(1 for r in results if r["sent"]),
                    "total_labels": len(labels),
                    "error_type": exc.error_type,
                    "error": str(exc),
                    "results": results,
                }
        return {
            "success": True,
            "printed": sum(1 for r in results if r["sent"]),
            "total_labels": len(labels),
            "results": results,
        }

    async def create_shopping_labels(
        self, items: list[str], *, include_checkboxes: bool = True, **kwargs: Any
    ) -> dict[str, Any]:
        prefix = "[ ] " if include_checkboxes else ""
        return await self.print_batch([f"{prefix}{item}" for item in items], **kwargs)

    async def create_inventory_labels(self, items: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        texts = []
        for item in items:
            name = item.get("name") or "Unknown"
            texts.append(f"{name}\nLoc: {item.get('location') or 'N/A'} | Qty: {item.get('quantity') or '?'}")
        return await self.print_batch(texts, **kwargs)
