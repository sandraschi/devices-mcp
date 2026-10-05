"""Supvan transports: framing-aware wrappers plus a protocol-decoding mock device.

``SppTransport`` speaks the ``7E 5A`` framing used by Bluetooth and BLE and sits on top
of an :class:`SppPipe` (the raw link). ``UsbHidTransport`` speaks the ``C0 40`` framing.

``MockPipe`` is a simulated printer that *decodes what it is sent* (frame checksums,
LZMA, buffer headers, buffer checksums) and reassembles the page bitmap. It is the
test fixture for the print path and is also what ``mock://`` targets use. It proves the
host encoder is self-consistent; it cannot prove the real firmware accepts the bytes.

``BlePipe`` and the HID device wrapper are **unverified against hardware**: they port the
upstream transports, but this project has no printer to run them on.
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import supvan_proto as sp
from .raster import mono_to_pbm

logger = logging.getLogger(__name__)

SPP_BLOCK_SIZE = 512
BLE_CHUNK = 128
BLE_CHUNK_DELAY_S = 0.010
BLE_RESPONSE_TIMEOUT_S = 4.0
USB_RESPONSE_TIMEOUT_S = 2.0


class TransportError(RuntimeError):
    """The link failed (not connected, timed out, driver missing)."""


# --- abstract layers ---------------------------------------------------------


class SppPipe(ABC):
    """Raw byte link carrying already-framed Supvan frames."""

    acks_data_frames: bool = True

    @abstractmethod
    async def send_cmd_frame(self, frame: bytes) -> bytes | None: ...

    @abstractmethod
    async def send_data_frame(self, frame: bytes, read_response: bool) -> bytes | None: ...

    async def close(self) -> None:
        return None


class Transport(ABC):
    """What the print state machine needs, independent of framing."""

    name: str

    @abstractmethod
    async def send_cmd(self, cmd: int, param: int = 0) -> bytes | None: ...

    @abstractmethod
    async def send_cmd_two(self, cmd: int, p1: int, p2: int) -> bytes | None: ...

    @abstractmethod
    async def send_bulk_header(self, compressed_len: int, num_packets: int) -> bytes | None: ...

    @abstractmethod
    async def send_bulk_data(self, data: bytes, read_final_response: bool) -> bytes | None: ...

    @abstractmethod
    def parse_status(self, resp: bytes) -> sp.PrinterStatus | None: ...

    @abstractmethod
    def parse_material(self, resp: bytes) -> sp.MaterialInfo | None: ...

    @abstractmethod
    def validate_response(self, resp: bytes, expected_cmd: int) -> bool: ...

    @abstractmethod
    def parse_device_name(self, resp: bytes) -> str | None: ...

    async def close(self) -> None:
        return None


class SppTransport(Transport):
    """``7E 5A`` framing over any :class:`SppPipe` (Bluetooth RFCOMM or BLE GATT)."""

    def __init__(self, pipe: SppPipe, name: str = "spp") -> None:
        self.pipe = pipe
        self.name = name

    async def send_cmd(self, cmd: int, param: int = 0) -> bytes | None:
        return await self.pipe.send_cmd_frame(sp.make_cmd(cmd, param))

    async def send_cmd_two(self, cmd: int, p1: int, p2: int) -> bytes | None:
        return await self.pipe.send_cmd_frame(sp.make_cmd_start_trans(cmd, p1, p2))

    async def send_bulk_header(self, compressed_len: int, num_packets: int) -> bytes | None:
        return await self.send_cmd_two(sp.CMD_NEXT_ZIPPEDBULK, SPP_BLOCK_SIZE, num_packets)

    async def send_bulk_data(self, data: bytes, read_final_response: bool) -> bytes | None:
        # Classic SPP acks every data frame and the host must drain each ack; BLE never acks.
        frames = sp.build_data_frames(data)
        acked = self.pipe.acks_data_frames
        last: bytes | None = None
        for i, frame in enumerate(frames):
            is_last = i == len(frames) - 1
            resp = await self.pipe.send_data_frame(frame, acked and (not is_last or read_final_response))
            if is_last:
                last = resp
        return last

    def parse_status(self, resp: bytes) -> sp.PrinterStatus | None:
        return sp.parse_status(resp)

    def parse_material(self, resp: bytes) -> sp.MaterialInfo | None:
        return sp.parse_material(resp)

    def validate_response(self, resp: bytes, expected_cmd: int) -> bool:
        return sp.validate_response(resp, expected_cmd)

    def parse_device_name(self, resp: bytes) -> str | None:
        return sp.parse_device_name(resp)

    async def close(self) -> None:
        await self.pipe.close()


class UsbHidTransport(Transport):
    """``C0 40`` framing over a HID device (``write(bytes)`` / ``read(n, timeout_ms)`` sync API).

    UNVERIFIED on Windows: upstream drives ``/dev/hidraw``. With ``hidapi`` a report-ID byte
    (0) must prefix each write if the device uses unnumbered reports, handled in
    :class:`HidapiDevice`.
    """

    name = "usb_hid"

    def __init__(self, device: Any) -> None:
        self.device = device

    async def _send_and_recv(self, data: bytes) -> bytes | None:
        def io() -> bytes | None:
            self.device.write(data)
            return self.device.read(sp.HID_REPORT_SIZE, int(USB_RESPONSE_TIMEOUT_S * 1000)) or None

        return await asyncio.to_thread(io)

    async def send_cmd(self, cmd: int, param: int = 0) -> bytes | None:
        return await self._send_and_recv(sp.make_usb_cmd(cmd, param))

    async def send_cmd_two(self, cmd: int, p1: int, p2: int) -> bytes | None:
        return await self._send_and_recv(sp.make_usb_cmd_two(cmd, p1, p2))

    async def send_bulk_header(self, compressed_len: int, num_packets: int) -> bytes | None:
        # USB encodes NEXT_ZIPPEDBULK as the total compressed byte length.
        return await self.send_cmd(sp.CMD_NEXT_ZIPPEDBULK, compressed_len)

    async def send_bulk_data(self, data: bytes, read_final_response: bool) -> bytes | None:
        chunks = [data[i : i + sp.HID_REPORT_SIZE] for i in range(0, len(data), sp.HID_REPORT_SIZE)]

        def io() -> bytes | None:
            for i, chunk in enumerate(chunks):
                is_last = i == len(chunks) - 1
                self.device.write(chunk)
                if is_last and read_final_response:
                    return self.device.read(sp.HID_REPORT_SIZE, int(USB_RESPONSE_TIMEOUT_S * 1000)) or None
                if not is_last:
                    time.sleep(0.001)
            return None

        return await asyncio.to_thread(io)

    def parse_status(self, resp: bytes) -> sp.PrinterStatus | None:
        return sp.parse_usb_status(resp)

    def parse_material(self, resp: bytes) -> sp.MaterialInfo | None:
        return sp.parse_usb_material(resp)

    def validate_response(self, resp: bytes, expected_cmd: int) -> bool:
        # USB replies do not echo the command byte: any non-empty reply counts as an ack.
        return len(resp) > 0

    def parse_device_name(self, resp: bytes) -> str | None:
        return None  # the 8-byte USB reply has no string slot

    async def close(self) -> None:
        await asyncio.to_thread(self.device.close)


class HidapiDevice:
    """Adapter from the ``hidapi`` package to the minimal write/read/close API.

    UNVERIFIED against a real device.
    """

    def __init__(self, vid: int = 0x1820, path: bytes | None = None) -> None:
        try:
            import hid  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise TransportError("USB access needs the 'hidapi' package: uv pip install hidapi") from exc
        self._dev = hid.device()
        if path is not None:
            self._dev.open_path(path)
        else:
            self._dev.open(vid, 0)
        self._dev.set_nonblocking(False)

    @staticmethod
    def enumerate(vid: int = 0x1820) -> list[dict[str, Any]]:
        try:
            import hid  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise TransportError("USB discovery needs the 'hidapi' package: uv pip install hidapi") from exc
        return list(hid.enumerate(vid, 0))

    def write(self, data: bytes) -> None:
        padded = data.ljust(sp.HID_REPORT_SIZE, b"\x00")
        self._dev.write(b"\x00" + padded)  # leading report-ID byte for unnumbered reports

    def read(self, size: int, timeout_ms: int) -> bytes:
        return bytes(self._dev.read(size, timeout_ms))

    def close(self) -> None:
        self._dev.close()


# --- BLE pipe (unverified) ---------------------------------------------------

_SUPVAN_GATT: tuple[tuple[str, str, str], ...] = (
    # (service, notify, write)
    (
        "0000fee7-0000-1000-8000-00805f9b34fb",
        "0000fec1-0000-1000-8000-00805f9b34fb",
        "0000fec1-0000-1000-8000-00805f9b34fb",
    ),
    (
        "0000e0ff-3c17-d293-8e48-14fe2e4da212",
        "0000ffe1-0000-1000-8000-00805f9b34fb",
        "0000ffe9-0000-1000-8000-00805f9b34fb",
    ),
    (
        "0000ff00-0000-1000-8000-00805f9b34fb",
        "0000ff01-0000-1000-8000-00805f9b34fb",
        "0000ff02-0000-1000-8000-00805f9b34fb",
    ),
)


def chars_for_service(service_uuid: str) -> tuple[str, str] | None:
    """``(notify_char, write_char)`` for a known Supvan GATT service UUID, else None."""
    s = service_uuid.lower()
    for svc, notify, write in _SUPVAN_GATT:
        if s == svc:
            return notify, write
    return None


class BlePipe(SppPipe):
    """GATT byte pipe via ``bleak``. UNVERIFIED against hardware (ported from upstream's BlueZ code).

    Frames go out in 128-byte fragments 10 ms apart; command replies are notifications that
    echo the command byte at offset 7; bulk data frames are not acknowledged.
    """

    acks_data_frames = False

    def __init__(self, client: Any, write_char: str, notify_char: str, *, write_with_response: bool) -> None:
        self._client = client
        self._write_char = write_char
        self._notify_char = notify_char
        self._with_response = write_with_response
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()

    @classmethod
    async def connect(cls, address: str, *, write_with_response: bool = False, timeout_s: float = 20.0) -> BlePipe:
        try:
            from bleak import BleakClient  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise TransportError("BLE access needs the 'bleak' package: uv pip install bleak") from exc
        client = BleakClient(address, timeout=timeout_s)
        try:
            await client.connect()
        except Exception as exc:
            raise TransportError(f"BLE connect to {address} failed: {exc}") from exc
        chars = None
        for service in client.services:
            chars = chars_for_service(str(service.uuid))
            if chars:
                break
        if not chars:
            await client.disconnect()
            raise TransportError(f"{address} exposes no known Supvan GATT service")
        pipe = cls(client, chars[1], chars[0], write_with_response=write_with_response)
        await client.start_notify(chars[0], lambda _c, data: pipe._queue.put_nowait(bytes(data)))
        return pipe

    async def _write_chunked(self, data: bytes) -> None:
        for i in range(0, len(data), BLE_CHUNK):
            if i:
                await asyncio.sleep(BLE_CHUNK_DELAY_S)
            await self._client.write_gatt_char(self._write_char, data[i : i + BLE_CHUNK], response=self._with_response)

    async def send_cmd_frame(self, frame: bytes) -> bytes | None:
        while not self._queue.empty():  # drop stale notifications
            self._queue.get_nowait()
        await self._write_chunked(frame)
        deadline = time.monotonic() + BLE_RESPONSE_TIMEOUT_S
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                resp = await asyncio.wait_for(self._queue.get(), timeout=remaining)
            except TimeoutError:
                break
            if len(resp) > 7 and resp[7] == frame[7]:
                return resp
        return None

    async def send_data_frame(self, frame: bytes, read_response: bool) -> bytes | None:
        await self._write_chunked(frame)
        return None

    async def close(self) -> None:
        try:
            await self._client.disconnect()
        except Exception:
            logger.warning("BLE disconnect failed", exc_info=True)


# --- mock device -------------------------------------------------------------


@dataclass
class MockPage:
    """One page the mock printer 'printed'."""

    feed_cols: int
    head_dots: int
    buffers: int
    density_black: int
    density_red: int
    pbm_path: Path | None = None
    image: Any = None  # Pillow mode "1", head axis = rows


@dataclass
class MockPipe(SppPipe):
    """Simulated printer speaking the ``7E 5A`` protocol; decodes everything it is sent."""

    profile: sp.PrintProfile = sp.PrintProfile.E_SERIES
    device_name: str = "E11"
    head_dots: int | None = None
    label_width_mm: int = 15
    label_height_mm: int = 50
    dump_dir: Path | None = None
    initial_flags: frozenset[str] = frozenset()
    pages: list[MockPage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    commands_seen: list[int] = field(default_factory=list)

    acks_data_frames = False

    def __post_init__(self) -> None:
        self._params = sp.profile_params(self.profile)
        self._head_dots = self.head_dots or self._params.default_printhead_dots
        self._printing_polls = 0
        self._buf_full_polls = 0
        self._started = False
        self._print_count = 0
        self._rx_frames: dict[int, bytes] = {}
        self._rx_expected = 0
        self._block_pending = 0
        self._page_cols: list[bytes] = []
        self._page_buffers = 0
        self._page_density = (0, 0)
        self._page_bpl = 0
        self._page_done_pending = False

    # -- helpers

    def _reply(self, cmd: int, payload: bytes = b"") -> bytes:
        out = bytearray(22 + len(payload))
        out[0], out[1] = sp.MAGIC1, sp.MAGIC2
        struct.pack_into("<H", out, 2, len(out) - 4)
        out[4], out[5], out[6], out[7] = sp.PROTO_ID, 0x03, 0x55, cmd
        out[22 : 22 + len(payload)] = payload
        return bytes(out)

    def _status_regs(self) -> tuple[int, int, int, int]:
        b0 = b1 = b2 = b3 = 0
        flags = self.initial_flags
        if self._buf_full_polls > 0:
            b0 |= 0x01
        if "label_rw_error" in flags:
            b0 |= 0x02
        if "label_end" in flags:
            b0 |= 0x04
        if "label_mode_error" in flags or self.errors:
            b0 |= 0x08
        if self._printing_polls > 0:
            b2 |= 0x40
            b1 |= 0x04
        if "head_temp_high" in flags:
            b1 |= 0x08
        if "cover_open" in flags:
            b2 |= 0x08
        if "label_not_installed" in flags:
            b3 |= 0x01
        return b0, b1, b2, b3

    # -- SppPipe

    async def send_cmd_frame(self, frame: bytes) -> bytes | None:
        if len(frame) != 16 or frame[0] != sp.MAGIC1 or frame[1] != sp.MAGIC2:
            self.errors.append("malformed command frame")
            return None
        if struct.unpack_from("<H", frame, 8)[0] != sum(frame[10:16]) & 0xFFFF:
            self.errors.append(f"command 0x{frame[7]:02x}: bad frame checksum")
            return None
        cmd = frame[7]
        _p1, p2 = struct.unpack_from("<HH", frame, 12)
        self.commands_seen.append(cmd)

        if cmd == sp.CMD_INQUIRY_STA:
            b0, b1, b2, b3 = self._status_regs()
            resp = bytearray(self._reply(cmd))
            resp[14:18] = bytes([b0, b1, b2, b3])
            struct.pack_into("<H", resp, 18, self._print_count)
            self._tick()
            return bytes(resp)
        if cmd == sp.CMD_RETURN_MAT:
            payload = bytearray(25)
            payload[0:7] = bytes.fromhex("1D987800000000")[:7]
            struct.pack_into("<H", payload, 15, 1)
            payload[17] = 1
            payload[18], payload[19], payload[20] = self.label_width_mm, self.label_height_mm, 3
            struct.pack_into("<I", payload, 21, 42)
            return self._reply(cmd, bytes(payload))
        if cmd == sp.CMD_RD_DEV_NAME:
            name = self.device_name.encode()
            resp = bytearray(self._reply(cmd, name))
            struct.pack_into("<H", resp, 2, 18 + len(name))
            return bytes(resp)
        if cmd == sp.CMD_START_PRINT:
            self._started = True
            self._printing_polls = 1_000_000  # printing until the last buffer drains
            self._page_cols, self._page_buffers = [], 0
            return self._reply(cmd)
        if cmd == sp.CMD_STOP_PRINT:
            self._started = False
            self._printing_polls = 0
            return self._reply(cmd)
        if cmd == sp.CMD_NEXT_ZIPPEDBULK:
            self._rx_expected = p2
            self._rx_frames = {}
            return self._reply(cmd)
        if cmd == sp.CMD_BUF_FULL:
            self._finish_block()
            self._buf_full_polls = 1
            return self._reply(cmd)
        return self._reply(cmd)  # CHECK_DEVICE, PAPER_SKIP, vendor pre/post-start commands, ...

    async def send_data_frame(self, frame: bytes, read_response: bool) -> bytes | None:
        try:
            index, total, payload = sp.parse_data_frame(frame)
        except sp.ProtocolError as exc:
            self.errors.append(f"data frame rejected: {exc}")
            return None
        if self._rx_expected and total != self._rx_expected:
            self.errors.append(f"data frame says {total} packets, header announced {self._rx_expected}")
        self._rx_frames[index] = payload
        return None

    # -- decoding

    def _tick(self) -> None:
        if self._buf_full_polls > 0:
            self._buf_full_polls -= 1
        if self._page_done_pending and self._buf_full_polls == 0:
            self._printing_polls = 0
            self._page_done_pending = False
            self._started = False

    def _finish_block(self) -> None:
        if not self._started:
            self.errors.append("BUF_FULL before START_PRINT")
            return
        if len(self._rx_frames) != self._rx_expected or sorted(self._rx_frames) != list(range(self._rx_expected)):
            self.errors.append(f"block incomplete: got packets {sorted(self._rx_frames)}, expected {self._rx_expected}")
            return
        # Packets are zero-padded to 500 bytes. The LZMA header carries the true size and the
        # decoder stops at the end-of-stream marker, so trailing zeros are ignored.
        stream = b"".join(self._rx_frames[i] for i in range(self._rx_expected))
        try:
            raw = sp.decompress_lzma(stream)
        except Exception as exc:  # lzma.LZMAError, ProtocolError
            self.errors.append(f"LZMA decode failed: {exc}")
            return
        size = self._params.buf_size
        if len(raw) % size:
            self.errors.append(f"decoded block is {len(raw)} bytes, not a multiple of the {size}-byte buffer")
            return
        for off in range(0, len(raw), size):
            self._take_buffer(raw[off : off + size])

    def _take_buffer(self, buf: bytes) -> None:
        chk_in = struct.unpack_from("<H", buf, 0)[0]
        cols = struct.unpack_from("<H", buf, 4)[0]
        bpl = buf[6]
        data_end = cols * bpl + sp.PRINT_BUF_HEADER
        chk = sum(buf[2:14]) + sum(
            buf[i * sp.CHECKSUM_STRIDE - 1] for i in range(1, data_end // sp.CHECKSUM_STRIDE + 1)
        )
        if chk & 0xFFFF != chk_in:
            self.errors.append(f"print buffer checksum mismatch (got 0x{chk & 0xFFFF:04x}, header 0x{chk_in:04x})")
            return
        if bpl * 8 != self._head_dots:
            self.errors.append(f"buffer is {bpl * 8} dots wide, printhead is {self._head_dots}")
            return
        flags, b1 = buf[2], buf[3]
        if self._page_buffers == 0 and not flags & 0x02:
            self.errors.append("first buffer is missing the PageSt flag")
        self._page_cols.append(bytes(buf[sp.PRINT_BUF_HEADER : sp.PRINT_BUF_HEADER + cols * bpl]))
        self._page_buffers += 1
        self._page_bpl = bpl
        self._page_density = ((b1 >> 2) & 0x0F, buf[12])
        if flags & 0x04 and flags & 0x08:
            self._complete_page()

    def _complete_page(self) -> None:
        data = b"".join(self._page_cols)
        total_cols = len(data) // self._page_bpl
        image = sp.columns_to_image(data, total_cols, self._page_bpl)
        page = MockPage(
            feed_cols=total_cols,
            head_dots=self._head_dots,
            buffers=self._page_buffers,
            density_black=self._page_density[0],
            density_red=self._page_density[1],
            image=image,
        )
        if self.dump_dir:
            self.dump_dir.mkdir(parents=True, exist_ok=True)
            path = self.dump_dir / f"mock-page-{int(time.time() * 1000)}-{len(self.pages)}.pbm"
            path.write_bytes(mono_to_pbm(image))
            page.pbm_path = path
        self.pages.append(page)
        self._print_count += 1
        self._page_done_pending = True
