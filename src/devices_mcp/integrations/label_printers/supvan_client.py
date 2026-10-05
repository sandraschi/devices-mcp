"""High-level Supvan / Katasymbol label printer client.

Targets (``target`` argument):

* ``mock://<model>``   simulated printer that decodes the bytes it receives (no hardware)
* ``ble://<address>``  Bluetooth LE (E10/E11/E16, T50M Pro) via ``bleak``   -- UNVERIFIED
* ``usb://``           USB-HID, vendor id 0x1820 (T-series) via ``hidapi``  -- UNVERIFIED

Anything that is not implemented or not installed fails with an explicit, machine-readable
error. Nothing here ever reports a print as successful unless the printer (or the mock)
acknowledged and completed the job.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import supvan_proto as sp
from .raster import LabelRenderError, render_text_label, save_preview, to_mono
from .supvan_transport import (
    BlePipe,
    HidapiDevice,
    MockPipe,
    SppTransport,
    Transport,
    TransportError,
    UsbHidTransport,
)

logger = logging.getLogger(__name__)

BLOCK_SETTLE_S = 0.1
READY_ATTEMPTS = 60
PRINTING_ATTEMPTS = 60
BUFFER_READY_ATTEMPTS = 200
COMPLETION_POLLS = 300
MAX_COPIES = 10


class SupvanError(RuntimeError):
    """A print or query failed. ``error_type`` is stable and machine-readable."""

    def __init__(self, message: str, error_type: str = "device_error", suggestions: list[str] | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.suggestions = suggestions or []


def label_dir() -> Path:
    """Where previews and mock dumps are written (``DEVICES_MCP_LABEL_DIR`` overrides)."""
    return Path(os.environ.get("DEVICES_MCP_LABEL_DIR") or Path(tempfile.gettempdir()) / "devices-mcp-labels")


# --- print state machine -----------------------------------------------------


class SupvanPrinter:
    """The print flow from the vendor app: check, ready, start, per-block transfer, wait."""

    def __init__(self, transport: Transport, profile: sp.PrintProfile, poll_interval_s: float = 0.1) -> None:
        self.transport = transport
        self.profile = profile
        self._params = sp.profile_params(profile)
        self._poll = poll_interval_s

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds if self._poll > 0 else 0)

    async def check_device(self) -> bool:
        resp = await self.transport.send_cmd(sp.CMD_CHECK_DEVICE, 0)
        return resp is not None and self.transport.validate_response(resp, sp.CMD_CHECK_DEVICE)

    async def query_status(self) -> sp.PrinterStatus | None:
        resp = await self.transport.send_cmd(sp.CMD_INQUIRY_STA, 0)
        return self.transport.parse_status(resp) if resp else None

    async def query_material(self) -> sp.MaterialInfo | None:
        resp = await self.transport.send_cmd(sp.CMD_RETURN_MAT, 0)
        return self.transport.parse_material(resp) if resp else None

    async def read_device_name(self) -> str | None:
        resp = await self.transport.send_cmd(sp.CMD_RD_DEV_NAME, 0)
        return self.transport.parse_device_name(resp) if resp else None

    def _fatal(self, status: sp.PrinterStatus) -> list[str]:
        return status.error_flags(ribbon_end_is_fatal=self._params.ribbon_end_is_fatal)

    async def _wait(self, predicate, attempts: int, what: str, *, pre_delay: float = 0.0) -> sp.PrinterStatus:
        for _ in range(attempts):
            if pre_delay:
                await self._sleep(pre_delay)
            status = await self.query_status()
            if status is not None:
                errors = self._fatal(status)
                if errors:
                    raise SupvanError(f"printer error while {what}: {', '.join(errors)}", "printer_fault")
                if predicate(status):
                    return status
            await self._sleep(self._poll)
        raise SupvanError(f"timed out {what}", "timeout")

    async def _transfer_block(self, block: bytes, speed: int) -> None:
        if len(block) > 0xFFFF:
            raise SupvanError(f"compressed block is {len(block)} bytes; the length field is 16-bit", "invalid_job")
        packets = sp.packet_count(len(block))
        if await self.transport.send_bulk_header(len(block), packets) is None:
            raise SupvanError("no response to NEXT_ZIPPEDBULK", "no_response")
        await self.transport.send_bulk_data(block, False)
        # Let the firmware drain the packets before BUF_FULL, and again before reading buf_full.
        await self._sleep(BLOCK_SETTLE_S)
        length, spd = (len(block), speed) if self._params.buf_full_reports_length else (0, 0)
        await self.transport.send_cmd_two(sp.CMD_BUF_FULL, length, spd)
        await self._sleep(BLOCK_SETTLE_S)

    async def print_blocks(self, blocks: list[bytes], speed: int) -> None:
        if not await self.check_device():
            raise SupvanError("CHECK_DEVICE failed: printer did not answer", "no_response")
        await self._wait(lambda s: not s.device_busy and not s.printing, READY_ATTEMPTS, "waiting for ready")

        if self._params.pre_start_cmd:
            await self.transport.send_cmd(*self._params.pre_start_cmd)
        await self.transport.send_cmd(sp.CMD_START_PRINT, 0)
        await self._wait(lambda s: s.printing, PRINTING_ATTEMPTS, "waiting for the print station")
        if self._params.post_start_cmd:
            await self.transport.send_cmd(*self._params.post_start_cmd)

        try:
            for i, block in enumerate(blocks):
                await self._wait(
                    lambda s: not s.buf_full,
                    BUFFER_READY_ATTEMPTS,
                    f"waiting for buffer space before block {i + 1}/{len(blocks)}",
                    pre_delay=0.02 if self._poll else 0.0,
                )
                await self._transfer_block(block, speed)
        except SupvanError:
            await self.transport.send_cmd(sp.CMD_STOP_PRINT, 0)
            raise

        # Completion needs the buffer drained too: a stuck buf_full means the page was
        # accepted but never printed.
        for _ in range(COMPLETION_POLLS):
            await self._sleep(self._poll)
            status = await self.query_status()
            if status is None:
                continue
            errors = self._fatal(status)
            if errors:
                raise SupvanError(f"printer error while printing: {', '.join(errors)}", "printer_fault")
            if not status.printing and not status.device_busy and not status.buf_full:
                return
        raise SupvanError("print did not complete within the time budget", "timeout")


# --- connection --------------------------------------------------------------


@dataclass
class Connection:
    transport: Transport
    model: sp.ModelInfo
    printer: SupvanPrinter
    mock: MockPipe | None = None

    async def close(self) -> None:
        await self.transport.close()


def _require_model(key: str | None, advertised: str | None = None) -> sp.ModelInfo:
    if key:
        model = sp.MODELS.get(key.lower())
        if model is None:
            raise SupvanError(
                f"unknown model '{key}'", "invalid_model", [f"Use one of: {', '.join(sorted(sp.MODELS))}"]
            )
        return model
    if advertised and (model := sp.resolve_model(advertised)):
        return model
    raise SupvanError(
        "cannot tell which Supvan model this is",
        "invalid_model",
        [f"Pass model= one of: {', '.join(sorted(sp.MODELS))}"],
    )


async def connect(target: str, model: str | None = None, *, dump_dir: Path | None = None) -> Connection:
    """Open ``target`` and return a ready connection (see module docstring for target forms)."""
    if target.startswith("mock://"):
        info = _require_model(model or target.removeprefix("mock://") or None)
        mock = MockPipe(
            profile=info.profile,
            device_name=info.marketing_name.split()[0].split("/")[0],
            head_dots=info.printhead_dots,
            dump_dir=dump_dir,
        )
        transport = SppTransport(mock, name="mock")
        return Connection(transport, info, SupvanPrinter(transport, info.profile, poll_interval_s=0), mock)

    if target.startswith("ble://"):
        address = target.removeprefix("ble://")
        info = _require_model(model)
        if "ble" not in info.transports:
            raise SupvanError(f"{info.marketing_name} is not known to support BLE", "unsupported_transport")
        try:
            pipe = await BlePipe.connect(address)
        except TransportError as exc:
            raise SupvanError(
                str(exc), "connect_failed", ["Is the printer on and in range?", "uv pip install bleak"]
            ) from exc
        transport = SppTransport(pipe, name="ble")
        return Connection(transport, info, SupvanPrinter(transport, info.profile))

    if target.startswith("usb://"):
        info = _require_model(model)
        if "usb_hid" not in info.transports:
            raise SupvanError(f"{info.marketing_name} has no USB interface", "unsupported_transport")
        try:
            device = await asyncio.to_thread(HidapiDevice)
        except (TransportError, OSError) as exc:
            raise SupvanError(
                str(exc), "connect_failed", ["Plug in the printer via USB", "uv pip install hidapi"]
            ) from exc
        transport = UsbHidTransport(device)
        return Connection(transport, info, SupvanPrinter(transport, info.profile))

    if target.startswith("bt://"):
        raise SupvanError(
            "Classic Bluetooth SPP (RFCOMM) is not implemented",
            "not_implemented",
            ["Use ble:// (E-series, T50M Pro) or usb:// (T-series)"],
        )
    raise SupvanError(
        f"unrecognised target '{target}'", "invalid_target", ["Use mock://<model>, ble://<address> or usb://"]
    )


# --- discovery ---------------------------------------------------------------


async def discover(timeout_s: float = 6.0) -> dict[str, Any]:
    """Scan BLE and USB for Supvan printers. Reports what could not be scanned and why."""
    found: list[dict[str, Any]] = []
    unavailable: dict[str, str] = {}

    try:
        from bleak import BleakScanner  # type: ignore[import-not-found]
    except ImportError:
        unavailable["ble"] = "bleak is not installed (uv pip install bleak)"
    else:
        try:
            for dev, adv in (await BleakScanner.discover(timeout=timeout_s, return_adv=True)).values():
                name = adv.local_name or dev.name or ""
                if (model := sp.resolve_model(name)) is not None:
                    found.append(
                        {
                            "transport": "ble",
                            "target": f"ble://{dev.address}",
                            "advertised_name": name,
                            "model": model.key,
                            "verification": model.verification,
                            "rssi": adv.rssi,
                        }
                    )
        except Exception as exc:
            logger.warning("BLE scan failed", exc_info=True)
            unavailable["ble"] = f"scan failed: {exc}"

    try:
        for entry in await asyncio.to_thread(HidapiDevice.enumerate):
            found.append(
                {
                    "transport": "usb_hid",
                    "target": "usb://",
                    "product": entry.get("product_string"),
                    "serial": entry.get("serial_number"),
                    "model": None,
                    "verification": "pass model= when connecting; USB product IDs are not mapped to models",
                }
            )
    except TransportError as exc:
        unavailable["usb"] = str(exc)
    except Exception as exc:
        logger.warning("USB enumeration failed", exc_info=True)
        unavailable["usb"] = f"enumeration failed: {exc}"

    return {"printers": found, "scanned": sorted({"ble", "usb"} - set(unavailable)), "unavailable": unavailable}


# --- high-level operations ---------------------------------------------------


async def get_status(target: str, model: str | None = None) -> dict[str, Any]:
    conn = await connect(target, model)
    try:
        name = await conn.printer.read_device_name()
        status = await conn.printer.query_status()
        material = await conn.printer.query_material()
    finally:
        await conn.close()
    if status is None and material is None:
        raise SupvanError("printer connected but did not answer status queries", "no_response")
    return {
        "model": conn.model.key,
        "marketing_name": conn.model.marketing_name,
        "verification": conn.model.verification,
        "transport": conn.transport.name,
        "reported_name": name,
        "status": status.to_dict() if status else None,
        "errors": status.error_flags(ribbon_end_is_fatal=sp.profile_params(conn.model.profile).ribbon_end_is_fatal)
        if status
        else [],
        "label": material.to_dict() if material else None,
    }


def _render(
    text: str | None, image_path: str | None, model: sp.ModelInfo, label_width_mm: int | None, length_mm: int | None
):
    head = model.printhead_dots
    across = min((label_width_mm or model.default_label_width_mm) * sp.DOTS_PER_MM, head)
    try:
        if text is not None:
            return render_text_label(text, across, min_length_px=(length_mm or 0) * sp.DOTS_PER_MM)
        from PIL import Image

        path = Path(image_path or "")
        if not path.is_file():
            raise LabelRenderError(f"image not found: {image_path}")
        with Image.open(path) as src:
            scale = across / src.size[1]
            resized = src.convert("RGBA").resize((max(1, round(src.size[0] * scale)), across))
        return to_mono(resized, dither=True)
    except LabelRenderError as exc:
        raise SupvanError(str(exc), "invalid_job") from exc


async def print_label(
    target: str,
    *,
    text: str | None = None,
    image_path: str | None = None,
    model: str | None = None,
    label_width_mm: int | None = None,
    length_mm: int | None = None,
    density: int = 4,
    copies: int = 1,
    dry_run: bool = False,
    flip_head_axis: bool = False,
) -> dict[str, Any]:
    """Render and print a label; ``dry_run`` renders and encodes but sends nothing."""
    if (text is None) == (image_path is None):
        raise SupvanError("pass exactly one of text or image_path", "invalid_job")
    if not 1 <= copies <= MAX_COPIES:
        raise SupvanError(f"copies must be 1-{MAX_COPIES}", "invalid_job")

    info = _require_model(model or (target.removeprefix("mock://") if target.startswith("mock://") else None))
    params = sp.profile_params(info.profile)
    if not 0 <= density <= params.max_density:
        raise SupvanError(f"density must be 0-{params.max_density} for {info.marketing_name}", "invalid_job")

    mono = _render(text, image_path, info, label_width_mm, length_mm)
    blocks, speed, job = sp.build_job(
        mono,
        info.profile,
        head_dots=info.printhead_dots,
        density=sp.Density(black=density, red=density),
        flip_head_axis=flip_head_axis,
    )
    preview = save_preview(mono, label_dir() / f"supvan-preview-{time.time_ns() // 1_000_000}.png")
    result: dict[str, Any] = {
        "model": info.key,
        "verification": info.verification,
        "job": job,
        "preview_png": str(preview),
        "copies": copies,
        "orientation_confirmed_on_hardware": False,
    }
    if dry_run:
        result["sent"] = False
        return result

    conn = await connect(target, info.key, dump_dir=label_dir() / "mock-pages")
    try:
        for _ in range(copies):
            await conn.printer.print_blocks(blocks, speed)
        if conn.mock is not None:
            if conn.mock.errors:
                raise SupvanError(f"mock printer rejected the job: {conn.mock.errors[0]}", "protocol_error")
            result["mock_pages"] = [str(p.pbm_path) for p in conn.mock.pages if p.pbm_path]
    finally:
        await conn.close()
    result["sent"] = True
    return result
