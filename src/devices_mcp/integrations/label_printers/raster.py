"""Shared label rendering: text and images to 1-bit bitmaps.

Conventions used throughout this package:

* "Reading orientation": the label as a person reads it. ``width`` runs along the
  feed direction (the long axis of a tape label), ``height`` runs across the tape.
* Pillow mode ``"1"``: pixel value 0 is black (ink), 255 is white (no ink).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_WINDOWS_FONT_CANDIDATES = ("arial.ttf", "segoeui.ttf", "calibri.ttf", "DejaVuSans.ttf")
_MAX_TEXT_CHARS = 500
_MAX_LABEL_LENGTH_PX = 4000


class LabelRenderError(ValueError):
    """Raised when text or an image cannot be turned into a printable bitmap."""


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _WINDOWS_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    logger.debug("No TrueType font found; falling back to Pillow's built-in font")
    return ImageFont.load_default(size=size)


def to_mono(image: Image.Image, threshold: int = 128, dither: bool = False) -> Image.Image:
    """Convert any image to mode ``"1"``.

    Transparent pixels are treated as white. ``dither`` selects Floyd-Steinberg
    halftoning, which suits photos; text and barcodes want the hard threshold.
    """
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, rgba)
    gray = image.convert("L")
    if dither:
        return gray.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    return gray.point(lambda p: 255 if p >= threshold else 0, mode="1")


def render_text_label(
    text: str,
    height_px: int,
    *,
    min_length_px: int = 0,
    max_length_px: int = _MAX_LABEL_LENGTH_PX,
    padding_px: int = 4,
    font_size_px: int | None = None,
    max_font_px: int = 96,
) -> Image.Image:
    """Render (multi-line) text to a mono bitmap in reading orientation.

    The font is sized to fill ``height_px`` (capped at ``max_font_px`` so a wide label does not
    get a poster-sized single word) unless ``font_size_px`` is given. The
    result is ``height_px`` tall and as long as the text needs, clamped to
    ``[min_length_px, max_length_px]``. Text that does not fit raises rather than
    silently printing a cut-off label.
    """
    if not text or not text.strip():
        raise LabelRenderError("label text is empty")
    if len(text) > _MAX_TEXT_CHARS:
        raise LabelRenderError(f"label text too long ({len(text)} chars, max {_MAX_TEXT_CHARS})")
    if height_px < 8:
        raise LabelRenderError(f"label height {height_px}px is too small to print")

    lines = text.splitlines() or [text]
    usable_h = height_px - 2 * padding_px
    line_h = usable_h // len(lines)
    size = font_size_px or min(max(line_h, 6), max_font_px)

    font = _load_font(size)
    probe = ImageDraw.Draw(Image.new("1", (1, 1), 255))
    # Shrink until every line fits the height budget (ascender+descender included).
    while True:
        boxes = [probe.textbbox((0, 0), ln or " ", font=font) for ln in lines]
        total_h = sum(b[3] - b[1] for b in boxes) + max(len(lines) - 1, 0) * 2
        if total_h <= usable_h or size <= 6:
            break
        size -= 1
        font = _load_font(size)

    text_w = max(b[2] - b[0] for b in boxes)
    length = max(text_w + 2 * padding_px, min_length_px)
    if length > max_length_px:
        raise LabelRenderError(
            f"rendered label would be {length}px long (max {max_length_px}px); shorten the text or use a smaller font"
        )

    img = Image.new("1", (length, height_px), 255)
    draw = ImageDraw.Draw(img)
    y = padding_px + max((usable_h - total_h) // 2, 0)
    for ln, box in zip(lines, boxes, strict=True):
        draw.text((padding_px - box[0], y - box[1]), ln, font=font, fill=0)
        y += (box[3] - box[1]) + 2
    return img


def mono_to_pbm(image: Image.Image) -> bytes:
    """Serialise a mode-``"1"`` image as binary PBM (P4), 1 = black."""
    mono = image if image.mode == "1" else to_mono(image)
    width, height = mono.size
    row_bytes = (width + 7) // 8
    out = bytearray(f"P4\n{width} {height}\n".encode("ascii"))
    px = mono.load()
    for y in range(height):
        row = bytearray(row_bytes)
        for x in range(width):
            if px[x, y] == 0:
                row[x >> 3] |= 0x80 >> (x & 7)
        out += row
    return bytes(out)


def save_preview(image: Image.Image, path: Path) -> Path:
    """Write a PNG preview (upscaled so 1-px detail is visible) and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scale = max(1, 400 // max(image.size[1], 1))
    preview = image.convert("L").resize((image.size[0] * scale, image.size[1] * scale), Image.Resampling.NEAREST)
    preview.save(path)
    return path
