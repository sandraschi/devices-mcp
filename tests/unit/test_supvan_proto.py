"""Supvan protocol tests.

Expected values marked "upstream" are copied from the unit tests of heeen/supvan-cups and
the efcroasdell E11 fork (Rust), so this port is checked against the reference
implementation's own vectors, not just against itself.
"""

import struct

import pytest
from PIL import Image

from devices_mcp.integrations.label_printers import supvan_proto as sp


def test_make_cmd_check_device_matches_upstream():
    pkt = sp.make_cmd(sp.CMD_CHECK_DEVICE, 0)
    assert len(pkt) == 16
    assert pkt[:8] == bytes([0x7E, 0x5A, 0x0C, 0x00, 0x10, 0x01, 0xAA, 0x12])
    assert pkt[10:16] == bytes([0x00, 0x01, 0, 0, 0, 0])
    assert pkt[8:10] == bytes([0x01, 0x00])  # checksum = sum(pkt[10:16]) = 1


def test_make_cmd_param_is_little_endian():
    pkt = sp.make_cmd(sp.CMD_INQUIRY_STA, 0x1234)
    assert pkt[12:14] == bytes([0x34, 0x12])
    assert struct.unpack_from("<H", pkt, 8)[0] == sum(pkt[10:16])


def test_start_trans_carries_size_and_count():
    pkt = sp.make_cmd_start_trans(sp.CMD_NEXT_ZIPPEDBULK, 512, 3)
    assert pkt[12:16] == bytes([0x00, 0x02, 0x03, 0x00])


def test_usb_cmd_is_big_endian():
    assert sp.make_usb_cmd(0x11, 0x1234) == bytes([0xC0, 0x40, 0x12, 0x34, 0x11, 0x00, 0x08, 0x00])
    assert sp.make_usb_cmd_two(0x10, 0x0102, 0x0304)[8:] == bytes([0x03, 0x04])


def test_data_packet_checksum_and_frame_layout():
    pkt = sp.make_data_packet(bytes([0x42] * 500), 0, 3)
    assert pkt[:2] == bytes([0xAA, 0xBB])
    assert pkt[4:6] == bytes([0, 3])
    assert struct.unpack_from("<H", pkt, 2)[0] == sum(pkt[4:506]) & 0xFFFF
    frame = sp.wrap_data_frame(pkt)
    assert len(frame) == 512
    assert frame[:6] == bytes([0x7E, 0x5A, 0xFC, 0x01, 0x10, 0x02])


def test_data_frames_roundtrip_and_detect_corruption():
    blob = bytes(range(256)) * 5
    frames = sp.build_data_frames(blob)
    assert len(frames) == 3
    rebuilt = b"".join(sp.parse_data_frame(f)[2] for f in frames)[: len(blob)]
    assert rebuilt == blob
    bad = bytearray(frames[0])
    bad[100] ^= 0xFF
    with pytest.raises(sp.ProtocolError, match="checksum"):
        sp.parse_data_frame(bytes(bad))


def test_status_decoding_matches_upstream_bits():
    resp = bytearray(20)
    resp[0], resp[1], resp[7] = 0x7E, 0x5A, sp.CMD_INQUIRY_STA
    resp[14], resp[16], resp[17] = 0x02, 0x08, 0x01
    resp[18] = 5
    s = sp.parse_status(bytes(resp))
    assert s is not None
    assert s.label_rw_error and s.cover_open and s.label_not_installed and s.print_count == 5
    assert set(s.error_flags()) >= {"label read/write error", "cover open", "label not installed"}


def test_status_rejects_short_and_wrong_magic():
    assert sp.parse_status(bytes(10)) is None
    resp = bytearray(20)
    resp[7] = sp.CMD_INQUIRY_STA
    assert sp.parse_status(bytes(resp)) is None


def test_ribbon_end_is_not_fatal_on_e_series():
    s = sp.decode_status_bits(0x20, 0, 0, 0, 0)
    assert s.ribbon_end
    assert "ribbon end" in s.error_flags(ribbon_end_is_fatal=True)
    assert s.error_flags(ribbon_end_is_fatal=False) == []


def test_usb_status_offsets():
    s = sp.parse_usb_status(bytes([0x08, 0x01, 0x04, 0x40, 0x00, 7, 0, 0]))
    assert s is not None and s.buf_full and s.device_busy and s.printing and s.print_count == 7


def test_material_payload_layout():
    payload = bytearray(25)
    payload[18:21] = bytes([15, 50, 3])
    struct.pack_into("<I", payload, 21, 99)
    m = sp.parse_material_payload(bytes(payload))
    assert m is not None
    assert (m.width_mm, m.height_mm, m.gap_mm, m.remaining) == (15, 50, 3, 99)


def test_usb_material_serial_is_ascii_at_offset_40():
    resp = bytearray(64)
    resp[19:22] = bytes([12, 40, 3])
    resp[40:56] = b"T0117A2410211517"
    m = sp.parse_usb_material(bytes(resp))
    assert m is not None and m.device_sn == "T0117A2410211517" and m.width_mm == 12


def test_page_reg_bits_match_upstream():
    assert sp.build_page_reg_bits(page_st=False, page_end=False, prt_end=False, nodu=4, mat=1) == bytes([0x00, 0x50])
    assert sp.build_page_reg_bits(page_st=True, page_end=True, prt_end=True, nodu=4, mat=1) == bytes([0x0E, 0x50])


def test_t_series_split_matches_upstream_geometry():
    # upstream: 48 bytes/line, 240 cols, margins 8+8 -> 224 printable -> 84 + 84 + 56 = 3 buffers
    bufs = sp.split_into_buffers(bytes(240 * 48), 48, 240, sp.PrintProfile.T_SERIES, sp.Density(4, 4))
    assert [struct.unpack_from("<H", b, 4)[0] for b in bufs] == [84, 84, 56]
    assert bufs[0][2] & 0x02 and not bufs[1][2] & 0x0E and bufs[2][2] & 0x0C == 0x0C
    assert all(len(b) == 4096 for b in bufs)
    assert all(b[8] == 8 and b[12] == 4 for b in bufs)


def test_e_series_split_matches_upstream_captured_geometry():
    # upstream e_series_split_matches_captured_geometry: 373 image cols + 2 margin, 12 B/line
    bufs = sp.split_into_buffers(bytes(375 * 12), 12, 375, sp.PrintProfile.E_SERIES, sp.Density(19, 19))
    assert len(bufs) == 2 and all(len(b) == 4000 for b in bufs)
    assert [struct.unpack_from("<H", b, 4)[0] for b in bufs] == [332, 41]
    assert bufs[0][3] == 0x10 and bufs[1][3] == 0x10  # nodu pinned to 4, mat 0
    assert (bufs[0][12], bufs[1][12]) == (19, 0)  # density only on the first buffer


def test_density_is_clamped_to_profile_maximum():
    t = sp.split_into_buffers(bytes(20 * 48), 48, 20, sp.PrintProfile.T_SERIES, sp.Density(99, 99))
    assert t[0][12] == 15


def test_lzma_header_matches_upstream():
    z = sp.compress_lzma(bytes(4096))
    assert z[0] == 0x5D
    assert z[1:5] == struct.pack("<I", 8192)
    assert z[5:13] == struct.pack("<Q", 4096)


def test_lzma_roundtrip():
    data = bytes([0x42]) * 1024
    assert sp.decompress_lzma(sp.compress_lzma(data)) == data


def test_t_series_packs_four_buffers_per_block():
    blocks, avg = sp.compress_buffers([bytes(4096)] * 9, sp.PrintProfile.T_SERIES)
    assert len(blocks) == 3 and avg > 0  # 4 + 4 + 1
    joined = b"".join(sp.decompress_lzma(b) for b in blocks)
    assert joined == bytes(4096) * 9


def test_incompressible_group_shrinks_to_fit():
    seed, bufs = 0x12345678, []
    for _ in range(4):
        b = bytearray(4096)
        for i in range(4096):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            b[i] = seed >> 24
        bufs.append(bytes(b))
    blocks, _ = sp.compress_buffers(bufs, sp.PrintProfile.T_SERIES)
    assert len(blocks) == 4
    assert b"".join(sp.decompress_lzma(b) for b in blocks) == b"".join(bufs)


def test_e_series_compresses_one_stream_per_buffer():
    blocks, _ = sp.compress_buffers([bytes([0x11]) * 4000, bytes([0x22]) * 4000], sp.PrintProfile.E_SERIES)
    assert len(blocks) == 2
    assert sp.decompress_lzma(blocks[1]) == bytes([0x22]) * 4000


@pytest.mark.parametrize(
    ("size", "speed"),
    [
        (4000, 10),
        (3001, 10),
        (3000, 15),
        (2801, 15),
        (2800, 20),
        (2500, 25),
        (2000, 40),
        (1500, 45),
        (1000, 55),
        (500, 60),
        (0, 60),
    ],
)
def test_calc_speed_thresholds_match_upstream(size, speed):
    assert sp.calc_speed(size) == speed


@pytest.mark.parametrize("name", ["E10pro", " e10 ", "E11", "e12", "E16"])
def test_e_series_names_route_to_e_profile(name):
    assert sp.profile_from_device_name(name) is sp.PrintProfile.E_SERIES


@pytest.mark.parametrize("name", ["", "E", "E1", "E20", "G15Mini", "T50M Pro"])
def test_other_names_never_route_to_e_profile(name):
    assert sp.profile_from_device_name(name) is sp.PrintProfile.T_SERIES


def test_resolve_model_uses_longest_prefix():
    assert sp.resolve_model("T0182A2507162197").key == "e11"
    assert sp.resolve_model("T0117A2410211517").key == "t50m_pro"
    assert sp.resolve_model("E16-1234").key == "e16"
    assert sp.resolve_model("Some Headphones") is None


def test_image_to_columns_centres_and_roundtrips():
    img = Image.new("1", (30, 40), 255)
    for x in range(30):
        img.putpixel((x, 0), 0)  # ink along the top edge
    data, cols, bpl = sp.image_to_columns(img, 96)
    assert (cols, bpl) == (30, 12)
    back = sp.columns_to_image(data, cols, bpl)
    assert back.size == (30, 96)
    offset = (96 - 40) // 2
    assert all(back.getpixel((x, offset)) == 0 for x in range(30))
    assert back.getpixel((0, offset + 1)) == 255


def test_image_wider_than_head_is_rejected_not_cropped():
    with pytest.raises(sp.ProtocolError, match="printhead carries 96"):
        sp.image_to_columns(Image.new("1", (10, 120), 255), 96)


def test_flip_head_axis_mirrors_across_tape():
    img = Image.new("1", (4, 8), 255)
    img.putpixel((0, 0), 0)
    normal = sp.columns_to_image(*sp.image_to_columns(img, 8))
    flipped = sp.columns_to_image(*sp.image_to_columns(img, 8, flip_head_axis=True))
    assert normal.getpixel((0, 0)) == 0 and flipped.getpixel((0, 7)) == 0
