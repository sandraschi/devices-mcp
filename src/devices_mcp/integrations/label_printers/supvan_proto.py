"""Supvan / Katasymbol thermal label printer wire protocol (pure functions, no I/O).

Python port of the reverse-engineered protocol in ``heeen/supvan-cups`` (T-series,
USB-HID + Bluetooth) and the ``efcroasdell/supvan-cups`` E11 fork (BLE E-series).
Both were reverse-engineered from the vendor Android app; nothing here comes from
vendor documentation.

Verification status of what is ported (see ``MODEL_VERIFICATION``):

* T-series framing/buffers/compression: verified on a T50M Pro by the upstream author.
* E-series profile: derived from one HCI capture of an E10pro, hardware-verified on
  an E11 by the fork author. E10 and E16 are *not* independently verified.
* Nothing in this module has been run against a physical printer by this project.
"""

from __future__ import annotations

import lzma
import struct
from dataclasses import dataclass
from enum import Enum

# --- framing constants -------------------------------------------------------

MAGIC1 = 0x7E
MAGIC2 = 0x5A
PROTO_ID = 0x10
PROTO_VER = 0x01
MARKER_AA = 0xAA
DATA_TYPE = 0x02
CMD_PAYLOAD_LEN = 0x0C

USB_MAGIC1 = 0xC0
USB_MAGIC2 = 0x40
HID_REPORT_SIZE = 64

DATA_MAGIC1 = 0xAA
DATA_MAGIC2 = 0xBB
DATA_PAYLOAD_SIZE = 500
DATA_PACKET_SIZE = 506
DATA_FRAME_SIZE = 512
DATA_FRAME_PAYLOAD_LEN = 508
BT_RESP_HEADER_LEN = 22

# --- commands ----------------------------------------------------------------

CMD_BUF_FULL = 0x10
CMD_INQUIRY_STA = 0x11
CMD_CHECK_DEVICE = 0x12
CMD_START_PRINT = 0x13
CMD_STOP_PRINT = 0x14
CMD_RD_DEV_NAME = 0x16
CMD_READ_REV = 0x17
CMD_PAPER_SKIP = 0x2E
CMD_RETURN_MAT = 0x30
CMD_NEXT_ZIPPEDBULK = 0x5C
CMD_READ_FWVER = 0xC5

# --- print buffer constants --------------------------------------------------

PRINT_BUF_SIZE = 4096
PRINT_BUF_HEADER = 14
MAX_BUF_DATA = 4074
MARGIN_MAX_DOTS = 900
CHECKSUM_STRIDE = 256
BUFFER_MAX_COUNT = 4
MAX_COMPRESSED_BLOCK = PRINT_BUF_SIZE
DOTS_PER_MM = 8


class ProtocolError(ValueError):
    """Malformed frame, impossible geometry, or an unsupported request."""


# --- command frames ----------------------------------------------------------


def make_cmd_start_trans(cmd: int, block_size: int, block_count: int) -> bytes:
    """Build a 16-byte ``7E 5A`` command frame (Bluetooth / BLE framing)."""
    pkt = bytearray(16)
    pkt[0] = MAGIC1
    pkt[1] = MAGIC2
    pkt[2] = CMD_PAYLOAD_LEN
    pkt[4] = PROTO_ID
    pkt[5] = PROTO_VER
    pkt[6] = MARKER_AA
    pkt[7] = cmd
    pkt[11] = 0x01
    pkt[12:14] = struct.pack("<H", block_size & 0xFFFF)
    pkt[14:16] = struct.pack("<H", block_count & 0xFFFF)
    pkt[8:10] = struct.pack("<H", sum(pkt[10:16]) & 0xFFFF)
    return bytes(pkt)


def make_cmd(cmd: int, param: int = 0) -> bytes:
    """A plain command is a start-trans frame with ``block_count`` 0."""
    return make_cmd_start_trans(cmd, param, 0)


def make_usb_cmd(cmd: int, param: int = 0) -> bytes:
    """8-byte USB-HID command; the parameter is big-endian (opposite of Bluetooth)."""
    return bytes([USB_MAGIC1, USB_MAGIC2, (param >> 8) & 0xFF, param & 0xFF, cmd, 0x00, 0x08, 0x00])


def make_usb_cmd_two(cmd: int, param1: int, param2: int) -> bytes:
    """10-byte USB-HID command for the two-parameter commands (BUF_FULL)."""
    return make_usb_cmd(cmd, param1) + bytes([(param2 >> 8) & 0xFF, param2 & 0xFF])


# --- data frames -------------------------------------------------------------


def make_data_packet(chunk: bytes, index: int, total: int) -> bytes:
    """506-byte ``AA BB`` packet: checksum over bytes [4..506], 500-byte payload slot."""
    if len(chunk) > DATA_PAYLOAD_SIZE:
        raise ProtocolError(f"data chunk is {len(chunk)} bytes, max {DATA_PAYLOAD_SIZE}")
    pkt = bytearray(DATA_PACKET_SIZE)
    pkt[0] = DATA_MAGIC1
    pkt[1] = DATA_MAGIC2
    pkt[4] = index
    pkt[5] = total
    pkt[6 : 6 + len(chunk)] = chunk
    pkt[2:4] = struct.pack("<H", sum(pkt[4:DATA_PACKET_SIZE]) & 0xFFFF)
    return bytes(pkt)


def wrap_data_frame(packet: bytes) -> bytes:
    """Wrap a 506-byte packet into the 512-byte transfer frame."""
    if len(packet) != DATA_PACKET_SIZE:
        raise ProtocolError(f"data packet must be {DATA_PACKET_SIZE} bytes, got {len(packet)}")
    frame = bytearray(DATA_FRAME_SIZE)
    frame[0] = MAGIC1
    frame[1] = MAGIC2
    frame[2:4] = struct.pack("<H", DATA_FRAME_PAYLOAD_LEN)
    frame[4] = PROTO_ID
    frame[5] = DATA_TYPE
    frame[6:] = packet
    return bytes(frame)


def packet_count(compressed_len: int) -> int:
    return -(-compressed_len // DATA_PAYLOAD_SIZE)


def build_data_frames(compressed: bytes) -> list[bytes]:
    """Split a compressed block into 512-byte frames (500 payload bytes each)."""
    total = packet_count(len(compressed))
    if total > 255:
        raise ProtocolError(f"block needs {total} packets; the packet counter is one byte")
    frames = []
    for i in range(total):
        chunk = compressed[i * DATA_PAYLOAD_SIZE : (i + 1) * DATA_PAYLOAD_SIZE]
        frames.append(wrap_data_frame(make_data_packet(chunk, i, total)))
    return frames


def parse_data_frame(frame: bytes) -> tuple[int, int, bytes]:
    """Validate a 512-byte data frame; return ``(index, total, payload500)``."""
    if len(frame) != DATA_FRAME_SIZE:
        raise ProtocolError(f"data frame must be {DATA_FRAME_SIZE} bytes, got {len(frame)}")
    if frame[0] != MAGIC1 or frame[1] != MAGIC2 or frame[4] != PROTO_ID or frame[5] != DATA_TYPE:
        raise ProtocolError("bad data frame header")
    pkt = frame[6:]
    if pkt[0] != DATA_MAGIC1 or pkt[1] != DATA_MAGIC2:
        raise ProtocolError("bad data packet magic")
    expected = sum(pkt[4:DATA_PACKET_SIZE]) & 0xFFFF
    if struct.unpack_from("<H", pkt, 2)[0] != expected:
        raise ProtocolError("data packet checksum mismatch")
    return pkt[4], pkt[5], bytes(pkt[6:DATA_PACKET_SIZE])


# --- print profiles ----------------------------------------------------------


class PrintProfile(Enum):
    T_SERIES = "t_series"
    E_SERIES = "e_series"


@dataclass(frozen=True)
class ProfileParams:
    buf_size: int
    max_buf_data: int
    margin_dots: int
    mat: int
    nodu: int | None
    max_density: int
    density_on_first_buffer_only: bool
    per_buffer_transfer: bool
    buf_full_reports_length: bool
    pre_start_cmd: tuple[int, int] | None
    post_start_cmd: tuple[int, int] | None
    default_printhead_dots: int
    ribbon_end_is_fatal: bool


_PARAMS: dict[PrintProfile, ProfileParams] = {
    PrintProfile.T_SERIES: ProfileParams(
        buf_size=PRINT_BUF_SIZE,
        max_buf_data=MAX_BUF_DATA,
        margin_dots=8,
        mat=1,
        nodu=None,
        max_density=15,
        density_on_first_buffer_only=False,
        per_buffer_transfer=False,
        buf_full_reports_length=True,
        pre_start_cmd=None,
        post_start_cmd=None,
        default_printhead_dots=384,
        ribbon_end_is_fatal=True,
    ),
    # Every E-series value was decoded from one E10pro HCI capture; the meaning of the
    # pre/post start commands (0xC9 / 0xBA) is unknown, the captured parameters did not vary.
    PrintProfile.E_SERIES: ProfileParams(
        buf_size=4000,
        max_buf_data=4000 - PRINT_BUF_HEADER,
        margin_dots=1,
        mat=0,
        nodu=4,
        max_density=19,
        density_on_first_buffer_only=True,
        per_buffer_transfer=True,
        buf_full_reports_length=False,
        pre_start_cmd=(0xC9, 110),
        post_start_cmd=(0xBA, 29),
        default_printhead_dots=96,
        ribbon_end_is_fatal=False,
    ),
}


def profile_params(profile: PrintProfile) -> ProfileParams:
    return _PARAMS[profile]


def profile_from_device_name(name: str) -> PrintProfile:
    """E-series iff the firmware name is ``E`` ``1`` ``<digit>``... (E10, E10pro, E11, E12, E16).

    Tight on purpose: an empty or unreadable name must never route a T50 onto the E-series
    flow, which would print blank.
    """
    n = name.strip().lower()
    if len(n) >= 3 and n[0] == "e" and n[1] == "1" and n[2].isdigit():
        return PrintProfile.E_SERIES
    return PrintProfile.T_SERIES


# --- model registry ----------------------------------------------------------


@dataclass(frozen=True)
class ModelInfo:
    key: str
    marketing_name: str
    profile: PrintProfile
    printhead_dots: int
    dpi: int
    transports: tuple[str, ...]
    verification: str
    bt_prefixes: tuple[str, ...]


# Advertised-name prefixes are transcribed from supvan-cups data/models.toml. A printer
# advertises a firmware serial (E11 -> "T0182A..."), not its marketing name.
MODELS: dict[str, ModelInfo] = {
    "t50m_pro": ModelInfo(
        key="t50m_pro",
        marketing_name="T50M Pro",
        profile=PrintProfile.T_SERIES,
        printhead_dots=384,
        dpi=203,
        transports=("usb_hid", "ble"),
        verification="upstream-verified on hardware (USB + Bluetooth); BLE per a third-party web UI",
        bt_prefixes=(
            "t50m pro",
            "t0096a",
            "t0117a",
            "t0118a",
            "t0129a",
            "t0147b",
            "t0148b",
            "t0162b",
            "t0163b",
            "t0170b",
            "t0178b",
            "t0205",
            "t0211b",
            "t0212b",
            "t0213b",
        ),
    ),
    "e10": ModelInfo(
        key="e10",
        marketing_name="E10 / T10",
        profile=PrintProfile.E_SERIES,
        printhead_dots=96,
        dpi=203,
        transports=("ble",),
        verification="single HCI capture of an E10pro; E10 itself unverified",
        bt_prefixes=("e10", "t10", "t0007", "t0010", "t0011", "t0012", "t0017", "t0025", "t0026", "t0027"),
    ),
    "e11": ModelInfo(
        key="e11",
        marketing_name="E11",
        profile=PrintProfile.E_SERIES,
        printhead_dots=96,
        dpi=203,
        transports=("ble",),
        verification="verified on hardware by the E11 fork author (96-dot width is provisional)",
        bt_prefixes=("e11", "t0138", "t0139", "t0181", "t0182", "t0183", "t0184", "t0216", "t0217", "t0218", "t0219"),
    ),
    "e16": ModelInfo(
        key="e16",
        marketing_name="E16 / T16",
        profile=PrintProfile.E_SERIES,
        printhead_dots=96,
        dpi=203,
        transports=("ble",),
        verification="UNVERIFIED: no capture or hardware test exists; assumed to share the E-series flow",
        bt_prefixes=("e16", "t16", "t0053", "t0054", "t0055", "t0105", "t0106", "t0107", "t0122", "t0123"),
    ),
}


def resolve_model(advertised_name: str) -> ModelInfo | None:
    """Longest-prefix match of a BLE advertised name against the model table."""
    n = advertised_name.strip().lower()
    best: tuple[int, ModelInfo] | None = None
    for model in MODELS.values():
        for prefix in model.bt_prefixes:
            if n.startswith(prefix) and (best is None or len(prefix) > best[0]):
                best = (len(prefix), model)
    return best[1] if best else None


# --- status / material parsing ----------------------------------------------


@dataclass
class PrinterStatus:
    buf_full: bool = False
    label_rw_error: bool = False
    label_end: bool = False
    label_mode_error: bool = False
    ribbon_rw_error: bool = False
    ribbon_end: bool = False
    low_battery: bool = False
    device_busy: bool = False
    head_temp_high: bool = False
    cover_open: bool = False
    insert_usb: bool = False
    printing: bool = False
    label_not_installed: bool = False
    print_count: int = 0
    regs: tuple[int, int, int, int] = (0, 0, 0, 0)

    def error_flags(self, *, ribbon_end_is_fatal: bool = True) -> list[str]:
        flags = [
            (self.label_rw_error, "label read/write error"),
            (self.label_end, "label roll end"),
            (self.label_mode_error, "label mode mismatch"),
            (self.ribbon_rw_error, "ribbon read/write error"),
            (self.ribbon_end and ribbon_end_is_fatal, "ribbon end"),
            (self.cover_open, "cover open"),
            (self.head_temp_high, "printhead temperature too high"),
            (self.label_not_installed, "label not installed"),
        ]
        return [msg for on, msg in flags if on]

    def to_dict(self) -> dict:
        return {
            "buf_full": self.buf_full,
            "device_busy": self.device_busy,
            "printing": self.printing,
            "cover_open": self.cover_open,
            "label_not_installed": self.label_not_installed,
            "label_end": self.label_end,
            "label_rw_error": self.label_rw_error,
            "label_mode_error": self.label_mode_error,
            "ribbon_end": self.ribbon_end,
            "head_temp_high": self.head_temp_high,
            "low_battery": self.low_battery,
            "print_count": self.print_count,
            "raw_registers": [f"{r:02x}" for r in self.regs],
        }


@dataclass
class MaterialInfo:
    uuid: str
    code: str
    sn: int
    label_type: int
    width_mm: int
    height_mm: int
    gap_mm: int
    remaining: int | None = None
    device_sn: str | None = None

    def to_dict(self) -> dict:
        return {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "gap_mm": self.gap_mm,
            "label_type": self.label_type,
            "remaining_labels": self.remaining,
            "roll_uuid": self.uuid,
            "device_serial": self.device_sn,
        }


def decode_status_bits(b0: int, b1: int, b2: int, b3: int, print_count: int) -> PrinterStatus:
    return PrinterStatus(
        buf_full=bool(b0 & 0x01),
        label_rw_error=bool(b0 & 0x02),
        label_end=bool(b0 & 0x04),
        label_mode_error=bool(b0 & 0x08),
        ribbon_rw_error=bool(b0 & 0x10),
        ribbon_end=bool(b0 & 0x20),
        low_battery=bool(b0 & 0x40),
        device_busy=bool(b1 & 0x04),
        head_temp_high=bool(b1 & 0x08),
        cover_open=bool(b2 & 0x08),
        insert_usb=bool(b2 & 0x10),
        printing=bool(b2 & 0x40),
        label_not_installed=bool(b3 & 0x01),
        print_count=print_count,
        regs=(b0, b1, b2, b3),
    )


def _check_header(data: bytes, min_len: int, cmd: int) -> bool:
    return len(data) >= min_len and data[0] == MAGIC1 and data[1] == MAGIC2 and data[7] == cmd


def validate_response(data: bytes, expected_cmd: int) -> bool:
    return _check_header(data, 8, expected_cmd)


def parse_status(data: bytes) -> PrinterStatus | None:
    """Parse a Bluetooth/BLE ``INQUIRY_STA`` response (>= 20 bytes)."""
    if len(data) < 20 or not _check_header(data, 20, CMD_INQUIRY_STA):
        return None
    return decode_status_bits(data[14], data[15], data[16], data[17], struct.unpack_from("<H", data, 18)[0])


def parse_usb_status(resp: bytes) -> PrinterStatus | None:
    """Parse the fixed 8-byte USB-HID status reply (status bytes at offsets 1..6)."""
    if len(resp) < 7:
        return None
    return decode_status_bits(resp[1], resp[2], resp[3], resp[4], struct.unpack_from("<H", resp, 5)[0])


def parse_material_payload(p: bytes, device_sn: str | None = None) -> MaterialInfo | None:
    if len(p) < 21:
        return None
    return MaterialInfo(
        uuid=p[0:7].hex().upper(),
        code=p[7:15].hex().upper(),
        sn=struct.unpack_from("<H", p, 15)[0],
        label_type=p[17],
        width_mm=p[18],
        height_mm=p[19],
        gap_mm=p[20],
        remaining=struct.unpack_from("<I", p, 21)[0] if len(p) >= 25 else None,
        device_sn=device_sn,
    )


def parse_material(data: bytes) -> MaterialInfo | None:
    """Parse a Bluetooth/BLE ``RETURN_MAT`` response (22-byte header, then the payload)."""
    if not _check_header(data, BT_RESP_HEADER_LEN, CMD_RETURN_MAT):
        return None
    return parse_material_payload(data[BT_RESP_HEADER_LEN:])


def parse_usb_material(resp: bytes) -> MaterialInfo | None:
    """Parse the 64-byte USB-HID material report; the device serial is ASCII at offset 40."""
    if len(resp) < 22:
        return None
    serial = None
    if len(resp) > 40:
        tail = resp[40:]
        end = tail.find(b"\x00")
        text = tail[: end if end >= 0 else len(tail)].decode("ascii", errors="replace")
        serial = text or None
    return parse_material_payload(resp[1:], serial)


def parse_device_name(data: bytes) -> str | None:
    if not _check_header(data, BT_RESP_HEADER_LEN + 1, CMD_RD_DEV_NAME):
        return None
    payload_len = struct.unpack_from("<H", data, 2)[0]
    data_len = max(payload_len - 18, 0)
    if data_len == 0 or data_len > len(data) - BT_RESP_HEADER_LEN:
        return None
    name = data[BT_RESP_HEADER_LEN : BT_RESP_HEADER_LEN + data_len].decode("utf-8", errors="replace").rstrip("\x00")
    return name or None


# --- raster packing ----------------------------------------------------------


def image_to_columns(mono, head_dots: int, *, flip_head_axis: bool = False) -> tuple[bytes, int, int]:
    """Pack a reading-orientation mono image into the printer's column-major raster.

    ``mono`` is a Pillow mode-``"1"`` image: width = feed direction, height = across the tape.
    Returns ``(data, total_cols, bytes_per_line)`` where ``total_cols`` is the feed length in
    dots and each column is ``head_dots / 8`` bytes, LSB-first, label centred on the head.

    Which physical edge of the tape head position 0 sits on has not been confirmed on
    hardware. ``flip_head_axis`` mirrors across the tape so the first real print can be
    corrected without touching the protocol code.
    """
    if head_dots <= 0 or head_dots % 8:
        raise ProtocolError(f"printhead width {head_dots} must be a positive multiple of 8 dots")
    feed_len, label_w = mono.size
    if feed_len < 1 or label_w < 1:
        raise ProtocolError("image is empty")
    bpl = head_dots // 8
    offset = max((head_dots - label_w) // 2, 0)
    if label_w > head_dots:
        raise ProtocolError(
            f"label is {label_w} dots across the tape but the printhead carries {head_dots}; "
            "reduce the height or choose a smaller font"
        )
    px = mono.load()
    out = bytearray(feed_len * bpl)
    for col in range(feed_len):
        base = col * bpl
        for y in range(label_w):
            if px[col, y] == 0:  # black pixel = ink
                head = offset + (label_w - 1 - y if flip_head_axis else y)
                out[base + (head >> 3)] |= 1 << (head & 7)
    return bytes(out), feed_len, bpl


def columns_to_image(data: bytes, total_cols: int, bpl: int):
    """Inverse of :func:`image_to_columns` (head position -> row), for the mock device and tests."""
    from PIL import Image

    head_dots = bpl * 8
    img = Image.new("1", (total_cols, head_dots), 255)
    px = img.load()
    for col in range(total_cols):
        base = col * bpl
        for head in range(head_dots):
            if data[base + (head >> 3)] & (1 << (head & 7)):
                px[col, head] = 0
    return img


# --- print buffers -----------------------------------------------------------


@dataclass(frozen=True)
class Density:
    black: int = 4
    red: int = 4


def build_page_reg_bits(
    *, page_st: bool, page_end: bool, prt_end: bool, nodu: int, mat: int, first_cut: int = 0, cut: int = 0
) -> bytes:
    b0 = 0
    if page_st:
        b0 |= 0x02
    if page_end:
        b0 |= 0x04
    if prt_end:
        b0 |= 0x08
    b0 |= (cut & 0x07) << 4
    b1 = (first_cut & 0x03) | ((nodu & 0x0F) << 2) | ((mat & 0x03) << 6)
    return bytes([b0, b1])


def build_print_buffer(
    image_data: bytes,
    per_line_byte: int,
    cols_in_buf: int,
    *,
    page_st: bool,
    page_end: bool,
    prt_end: bool,
    margin_top: int,
    margin_bottom: int,
    density: Density,
    profile: PrintProfile,
    first_buffer: bool,
) -> bytes:
    """Build one print buffer (header + column data + checksum)."""
    params = profile_params(profile)
    buf = bytearray(params.buf_size)

    black = min(density.black, params.max_density)
    red = min(density.red, params.max_density) if (first_buffer or not params.density_on_first_buffer_only) else 0

    bits = build_page_reg_bits(
        page_st=page_st,
        page_end=page_end,
        prt_end=prt_end,
        nodu=params.nodu if params.nodu is not None else black,
        mat=params.mat,
    )
    buf[2:4] = bits
    buf[4:6] = struct.pack("<H", cols_in_buf)
    buf[6] = per_line_byte
    buf[8:10] = struct.pack("<H", min(max(margin_top, 1), MARGIN_MAX_DOTS))
    buf[10:12] = struct.pack("<H", min(max(margin_bottom, 1), MARGIN_MAX_DOTS))
    buf[12] = red

    data_len = min(len(image_data), params.max_buf_data)
    buf[PRINT_BUF_HEADER : PRINT_BUF_HEADER + data_len] = image_data[:data_len]

    data_end = cols_in_buf * per_line_byte + PRINT_BUF_HEADER
    chk = sum(buf[2:14])
    for i in range(1, data_end // CHECKSUM_STRIDE + 1):
        idx = i * CHECKSUM_STRIDE - 1
        if idx < len(buf):
            chk += buf[idx]
    buf[0:2] = struct.pack("<H", chk & 0xFFFF)
    return bytes(buf)


def split_into_buffers(
    image_data: bytes,
    per_line_byte: int,
    total_cols: int,
    profile: PrintProfile,
    density: Density = Density(),
) -> list[bytes]:
    """Split column-major data (margins already included as blank columns) into print buffers."""
    params = profile_params(profile)
    margin = params.margin_dots
    printable = total_cols - 2 * margin
    if printable <= 0:
        raise ProtocolError(f"{total_cols} columns leaves nothing after {margin}-dot margins")
    max_cols = params.max_buf_data // per_line_byte
    if max_cols < 1:
        raise ProtocolError(f"{per_line_byte} bytes per line cannot fit a buffer")

    buffers: list[bytes] = []
    current = 0
    remaining = printable
    while remaining > 0:
        cols = min(remaining, max_cols)
        is_first = current == 0
        is_last = remaining <= max_cols
        start = (margin + current) * per_line_byte
        chunk = image_data[start : start + cols * per_line_byte]
        buffers.append(
            build_print_buffer(
                chunk,
                per_line_byte,
                cols,
                page_st=is_first,
                page_end=is_last,
                prt_end=is_last,
                margin_top=margin,
                margin_bottom=margin,
                density=density,
                profile=profile,
                first_buffer=is_first,
            )
        )
        current += cols
        remaining -= cols
    return buffers


# --- compression -------------------------------------------------------------

_LZMA_FILTERS = [{"id": lzma.FILTER_LZMA1, "preset": 6, "dict_size": 8192, "lc": 3, "lp": 0, "pb": 2, "nice_len": 128}]


def compress_lzma(data: bytes) -> bytes:
    """LZMA1 'alone' stream with the printer's parameters; header carries the real size.

    dict_size 8192 / lc 3 / lp 0 / pb 2 come from the vendor app; the firmware has little RAM
    and rejects larger dictionaries.
    """
    out = bytearray(lzma.compress(data, format=lzma.FORMAT_ALONE, filters=_LZMA_FILTERS))
    out[5:13] = struct.pack("<Q", len(data))
    return bytes(out)


def decompress_lzma(data: bytes) -> bytes:
    """Inverse of :func:`compress_lzma` (restores the unknown-size sentinel liblzma wants)."""
    if len(data) < 13:
        raise ProtocolError(f"lzma stream too short: {len(data)} bytes")
    fixed = bytearray(data)
    fixed[5:13] = struct.pack("<Q", 0xFFFFFFFFFFFFFFFF)
    # Not lzma.decompress(): it would try to read the zero padding after the stream as a second one.
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    out = decoder.decompress(bytes(fixed))
    if not decoder.eof:
        raise ProtocolError("lzma stream ended before its end-of-stream marker")
    return out


def compress_buffers(buffers: list[bytes], profile: PrintProfile) -> tuple[list[bytes], int]:
    """Compress print buffers into the blocks the firmware expects.

    T-series: pack up to four buffers per LZMA block, shrinking the group until the block
    fits the 4096-byte receive buffer. E-series: exactly one stream per buffer.
    Returns ``(blocks, mean_compressed_size_per_buffer)``.
    """
    if not buffers:
        raise ProtocolError("no buffers to compress")
    blocks: list[bytes] = []
    if profile_params(profile).per_buffer_transfer:
        blocks = [compress_lzma(b) for b in buffers]
    else:
        nxt = 0
        while nxt < len(buffers):
            take = min(BUFFER_MAX_COUNT, len(buffers) - nxt)
            while True:
                z = compress_lzma(b"".join(buffers[nxt : nxt + take]))
                if len(z) <= MAX_COMPRESSED_BLOCK or take == 1:
                    break
                take -= 1
            blocks.append(z)
            nxt += take
    return blocks, sum(len(b) for b in blocks) // len(buffers)


def calc_speed(compressed_size: int) -> int:
    """Print speed from mean compressed bytes per buffer (``T50PlusPrint.multiCompression``)."""
    for limit, speed in ((3000, 10), (2800, 15), (2500, 20), (2000, 25), (1500, 40), (1000, 45), (500, 55)):
        if compressed_size > limit:
            return speed
    return 60


MULTI_BLOCK_SPEED = 20


def build_job(
    mono,
    profile: PrintProfile,
    *,
    head_dots: int | None = None,
    density: Density = Density(),
    flip_head_axis: bool = False,
) -> tuple[list[bytes], int, dict]:
    """Reading-orientation mono image -> ``(compressed_blocks, speed, info)``."""
    params = profile_params(profile)
    head = head_dots or params.default_printhead_dots
    margin = params.margin_dots
    cols_data, feed_len, bpl = image_to_columns(mono, head, flip_head_axis=flip_head_axis)
    # Blank margin columns before and after the image, as the buffer header advertises them.
    padded = bytes(margin * bpl) + cols_data + bytes(margin * bpl)
    buffers = split_into_buffers(padded, bpl, feed_len + 2 * margin, profile, density)
    blocks, avg = compress_buffers(buffers, profile)
    speed = calc_speed(avg)
    if len(blocks) > 1 and not params.per_buffer_transfer:
        speed = MULTI_BLOCK_SPEED
    info = {
        "feed_length_dots": feed_len,
        "feed_length_mm": round(feed_len / DOTS_PER_MM, 1),
        "head_dots": head,
        "buffers": len(buffers),
        "blocks": len(blocks),
        "compressed_bytes": sum(len(b) for b in blocks),
        "speed": speed,
        "profile": profile.value,
    }
    return blocks, speed, info
