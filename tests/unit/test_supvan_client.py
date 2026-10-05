"""Supvan client tests against the protocol-decoding mock printer (no hardware).

These prove the host encoder and the print state machine are self-consistent: the mock
decodes frames, LZMA, buffer headers and checksums and rebuilds the page, which must equal
the image that went in. They do not prove a real firmware accepts the bytes.
"""

import pytest
from PIL import Image, ImageChops

from devices_mcp.integrations.label_printers import supvan_client as sc
from devices_mcp.integrations.label_printers import supvan_proto as sp
from devices_mcp.integrations.label_printers.raster import render_text_label


def _expected_columns_image(mono: Image.Image, head: int) -> Image.Image:
    data, cols, bpl = sp.image_to_columns(mono, head)
    return sp.columns_to_image(data, cols, bpl)


def _same(a: Image.Image, b: Image.Image) -> bool:
    return a.size == b.size and ImageChops.difference(a.convert("L"), b.convert("L")).getbbox() is None


@pytest.mark.parametrize("model", ["e10", "e11", "e16", "t50m_pro"])
async def test_roundtrip_is_pixel_exact_for_each_model(model):
    conn = await sc.connect(f"mock://{model}")
    try:
        head = conn.model.printhead_dots
        mono = render_text_label("Hello label printer 0123456789", min(head, 96))
        blocks, speed, job = sp.build_job(mono, conn.model.profile, head_dots=head)
        await conn.printer.print_blocks(blocks, speed)
        assert conn.mock.errors == []
        assert len(conn.mock.pages) == 1
        assert _same(conn.mock.pages[0].image, _expected_columns_image(mono, head))
        assert job["buffers"] >= 1
    finally:
        await conn.close()


@pytest.mark.parametrize("model", ["e11", "t50m_pro"])
async def test_long_label_spans_multiple_buffers_and_still_roundtrips(model):
    conn = await sc.connect(f"mock://{model}")
    head = conn.model.printhead_dots
    mono = render_text_label("A" * 60, min(head, 96))
    blocks, speed, job = sp.build_job(mono, conn.model.profile, head_dots=head)
    assert job["buffers"] > 1
    await conn.printer.print_blocks(blocks, speed)
    assert conn.mock.errors == []
    assert conn.mock.pages[0].buffers == job["buffers"]
    assert _same(conn.mock.pages[0].image, _expected_columns_image(mono, head))
    # T-series packs buffers into shared blocks and slows the head for split pages
    if conn.model.profile is sp.PrintProfile.T_SERIES and job["blocks"] > 1:
        assert speed == sp.MULTI_BLOCK_SPEED


async def test_e_series_sends_vendor_pre_and_post_start_commands_in_order():
    conn = await sc.connect("mock://e11")
    mono = render_text_label("x", 96)
    blocks, speed, _ = sp.build_job(mono, conn.model.profile, head_dots=96)
    await conn.printer.print_blocks(blocks, speed)
    seen = conn.mock.commands_seen
    assert seen.index(0xC9) < seen.index(sp.CMD_START_PRINT) < seen.index(0xBA) < seen.index(sp.CMD_NEXT_ZIPPEDBULK)


async def test_t_series_does_not_send_e_series_commands():
    conn = await sc.connect("mock://t50m_pro")
    mono = render_text_label("x", 96)
    blocks, speed, _ = sp.build_job(mono, conn.model.profile, head_dots=384)
    await conn.printer.print_blocks(blocks, speed)
    assert 0xC9 not in conn.mock.commands_seen and 0xBA not in conn.mock.commands_seen


@pytest.mark.parametrize("flag", ["cover_open", "label_end", "label_not_installed", "head_temp_high"])
async def test_printer_fault_aborts_the_job(flag):
    conn = await sc.connect("mock://e11")
    conn.mock.initial_flags = frozenset({flag})
    blocks, speed, _ = sp.build_job(render_text_label("x", 96), conn.model.profile, head_dots=96)
    with pytest.raises(sc.SupvanError) as exc:
        await conn.printer.print_blocks(blocks, speed)
    assert exc.value.error_type == "printer_fault"
    assert conn.mock.pages == []


async def test_corrupt_block_is_rejected_by_the_mock_not_silently_printed():
    conn = await sc.connect("mock://e11")
    blocks, speed, _ = sp.build_job(render_text_label("hello", 96), conn.model.profile, head_dots=96)
    bad = bytearray(blocks[0])
    bad[20] ^= 0xFF
    with pytest.raises(sc.SupvanError) as exc:
        await conn.printer.print_blocks([bytes(bad), *blocks[1:]], speed)
    assert exc.value.error_type == "printer_fault"
    assert conn.mock.errors, "mock should have recorded a decode/checksum failure"
    assert conn.mock.pages == []


async def test_status_query_reports_label_and_no_errors():
    result = await sc.get_status("mock://e11")
    assert result["model"] == "e11"
    assert result["reported_name"] == "E11"
    assert result["label"]["width_mm"] == 15
    assert result["errors"] == []
    assert result["transport"] == "mock"


async def test_print_label_dry_run_sends_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVICES_MCP_LABEL_DIR", str(tmp_path))
    result = await sc.print_label("mock://e11", text="Pantry", dry_run=True)
    assert result["sent"] is False
    assert (tmp_path / result["preview_png"].rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).exists()
    assert result["orientation_confirmed_on_hardware"] is False
    assert "mock_pages" not in result


async def test_print_label_writes_a_pbm_dump_through_the_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVICES_MCP_LABEL_DIR", str(tmp_path))
    result = await sc.print_label("mock://t50m_pro", text="Shelf 3", copies=2)
    assert result["sent"] is True
    assert len(result["mock_pages"]) == 2
    first = (tmp_path / "mock-pages").glob("*.pbm")
    assert all(p.read_bytes().startswith(b"P4\n") for p in first)


@pytest.mark.parametrize(
    ("kwargs", "error_type"),
    [
        ({"text": "a", "image_path": "b.png"}, "invalid_job"),
        ({}, "invalid_job"),
        ({"text": "a", "copies": 0}, "invalid_job"),
        ({"text": "a", "copies": 99}, "invalid_job"),
        ({"text": "a", "density": 99}, "invalid_job"),
        ({"text": "   "}, "invalid_job"),
        ({"image_path": "does-not-exist.png"}, "invalid_job"),
    ],
)
async def test_invalid_jobs_fail_with_typed_errors(kwargs, error_type):
    with pytest.raises(sc.SupvanError) as exc:
        await sc.print_label("mock://e11", **kwargs)
    assert exc.value.error_type == error_type


@pytest.mark.parametrize(
    ("target", "model", "error_type"),
    [
        ("bt://AA:BB:CC:DD:EE:FF", "t50m_pro", "not_implemented"),
        ("serial://COM3", "e11", "invalid_target"),
        ("mock://nonsense", None, "invalid_model"),
        ("usb://", "e11", "unsupported_transport"),
        ("ble://AA:BB:CC:DD:EE:FF", None, "invalid_model"),
    ],
)
async def test_unsupported_targets_fail_explicitly(target, model, error_type):
    with pytest.raises(sc.SupvanError) as exc:
        await sc.connect(target, model)
    assert exc.value.error_type == error_type


async def test_ble_without_bleak_fails_with_connect_error_not_fake_success():
    pytest.importorskip("builtins")
    try:
        import bleak  # noqa: F401
    except ImportError:
        with pytest.raises(sc.SupvanError) as exc:
            await sc.connect("ble://AA:BB:CC:DD:EE:FF", "e11")
        assert exc.value.error_type == "connect_failed"
        assert "bleak" in str(exc.value)
    else:
        pytest.skip("bleak installed; connect would try real hardware")


async def test_text_too_tall_for_the_head_is_rejected():
    with pytest.raises(sp.ProtocolError):
        sp.image_to_columns(Image.new("1", (50, 200), 255), 96)


async def test_short_text_on_a_wide_head_is_not_poster_sized(tmp_path, monkeypatch):
    # Regression: text used to be sized to the whole 48 mm T50 head, giving a 200 mm label for "Hello 123".
    monkeypatch.setenv("DEVICES_MCP_LABEL_DIR", str(tmp_path))
    result = await sc.print_label("mock://t50m_pro", text="Hello 123", dry_run=True)
    assert result["job"]["feed_length_mm"] < 60
