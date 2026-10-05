"""Dymo client and label-printer tool tests.

The spooler is replaced by a recording fake (the only test seam); there is no simulated-success
path in production code. The honesty tests pin the behaviour the old stub got wrong: no printer
means an explicit error, never ``success: True``.
"""

import sys

import pytest
from fastmcp import Client, FastMCP
from PIL import Image

from devices_mcp.integrations import dymo_client as dc
from devices_mcp.tools.portmanteau.dymo_management import register_dymo_management_tool
from devices_mcp.tools.portmanteau.supvan_management import register_supvan_management_tool


class FakeSpooler:
    def __init__(self, printers=None, fail_on_call: int | None = None):
        self.printers = printers if printers is not None else []
        self.printed: list[tuple[str, Image.Image, str, str]] = []
        self.fail_on_call = fail_on_call

    def list_printers(self):
        return self.printers

    def paper_forms(self, name, port):
        return ["12mm D1", "19mm D1"]

    def print_image(self, name, image, title, orientation):
        if self.fail_on_call is not None and len(self.printed) + 1 == self.fail_on_call:
            raise dc.DymoError("the spooler rejected the job: boom", "print_failed")
        self.printed.append((name, image, title, orientation))
        return {"page_px": [100, 500], "drawn_px": [80, 400], "rotated_degrees": -90}


def _dymo(status_bits=0, name="DYMO MobileLabeler"):
    return {
        "name": name,
        "driver": "DYMO MobileLabeler",
        "port": "USB002",
        "status_bits": status_bits,
        "queued_jobs": 0,
    }


@pytest.fixture(autouse=True)
def _label_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVICES_MCP_LABEL_DIR", str(tmp_path))


async def test_no_dymo_installed_is_an_explicit_error_not_fake_success():
    client = dc.DymoClient(backend=FakeSpooler(printers=[{**_dymo(), "name": "Brother HL", "driver": "IPP"}]))
    with pytest.raises(dc.DymoError) as exc:
        await client.print_label("hello")
    assert exc.value.error_type == "device_not_found"
    assert exc.value.suggestions


async def test_status_reports_only_what_the_spooler_knows():
    client = dc.DymoClient(backend=FakeSpooler(printers=[_dymo()]))
    status = await client.get_status()
    assert status["printer"] == "DYMO MobileLabeler" and status["connected"] is True
    assert status["paper_forms"] == ["12mm D1", "19mm D1"]
    for invented in ("tape_remaining", "tape_size", "firmware_version", "tape_color"):
        assert invented not in status


async def test_offline_printer_is_reported_disconnected_and_blocks_printing():
    client = dc.DymoClient(backend=FakeSpooler(printers=[_dymo(status_bits=0x80)]))
    assert (await client.get_status())["connected"] is False
    with pytest.raises(dc.DymoError) as exc:
        await client.print_label("x")
    assert exc.value.error_type == "printer_fault"


async def test_print_label_sends_rendered_bitmap_per_copy():
    spool = FakeSpooler(printers=[_dymo()])
    result = await dc.DymoClient(backend=spool).print_label("Flour", tape_size="12mm", copies=2)
    assert result["sent"] is True and len(spool.printed) == 2
    name, image, _title, orientation = spool.printed[0]
    assert name == "DYMO MobileLabeler" and orientation == "auto"
    assert image.mode == "1" and image.size[1] == round(12 / 25.4 * 180)
    assert any(image.getpixel((x, y)) == 0 for x in range(image.size[0]) for y in range(image.size[1])), "no ink drawn"


async def test_dry_run_renders_but_never_touches_the_printer():
    spool = FakeSpooler(printers=[_dymo()])
    result = await dc.DymoClient(backend=spool).print_label("Flour", dry_run=True)
    assert result["sent"] is False and spool.printed == []
    assert result["preview_png"].endswith(".png")


async def test_dry_run_works_with_no_printer_installed():
    result = await dc.DymoClient(backend=FakeSpooler()).print_label("Flour", dry_run=True)
    assert result["sent"] is False


async def test_batch_stops_at_first_failure_and_counts_what_really_printed():
    spool = FakeSpooler(printers=[_dymo()], fail_on_call=3)
    result = await dc.DymoClient(backend=spool).print_batch(["a", "b", "c", "d"])
    assert result["success"] is False
    assert result["printed"] == 2 and len(spool.printed) == 2
    assert result["error_type"] == "print_failed"


async def test_shopping_and_inventory_labels_format_text():
    spool = FakeSpooler(printers=[_dymo()])
    client = dc.DymoClient(backend=spool)
    shopping = await client.create_shopping_labels(["Milk"], include_checkboxes=True)
    inventory = await client.create_inventory_labels([{"name": "M3 screws", "location": "A1", "quantity": 40}])
    assert shopping["results"][0]["label_text"] == "[ ] Milk"
    assert inventory["results"][0]["label_text"] == "M3 screws\nLoc: A1 | Qty: 40"


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.print_label("x", tape_size="99mm"),
        lambda c: c.print_label("x", copies=0),
        lambda c: c.print_label("   "),
        lambda c: c.print_batch([]),
        lambda c: c.print_batch(["x"] * 51),
    ],
)
async def test_invalid_jobs_raise_typed_errors(call):
    with pytest.raises(dc.DymoError) as exc:
        await call(dc.DymoClient(backend=FakeSpooler(printers=[_dymo()])))
    assert exc.value.error_type == "invalid_job"


def test_status_bits_decode():
    assert dc.decode_status(0x80 | 0x10) == ["paper_out", "offline"]
    assert dc.decode_status(0) == []


# --- through the MCP layer ----------------------------------------------------


def _server() -> FastMCP:
    mcp = FastMCP("label-test")
    register_dymo_management_tool(mcp)
    register_supvan_management_tool(mcp)
    return mcp


async def _call(name, **args):
    async with Client(_server()) as client:
        result = await client.call_tool(name, args, raise_on_error=False)
        return result.structured_content or result.data


async def test_supvan_tool_prints_through_the_mock_and_reports_sent():
    data = await _call("supvan_management", action="print_label", target="mock://e11", text="Pantry")
    assert data["success"] is True and data["data"]["sent"] is True
    assert data["data"]["orientation_confirmed_on_hardware"] is False


async def test_supvan_tool_models_lists_verification_per_model():
    data = await _call("supvan_management", action="models")
    by_key = {m["key"]: m for m in data["data"]["models"]}
    assert set(by_key) == {"e10", "e11", "e16", "t50m_pro"}
    assert "UNVERIFIED" in by_key["e16"]["verification"]


async def test_supvan_tool_unimplemented_classic_bluetooth_fails_explicitly():
    data = await _call("supvan_management", action="status", target="bt://AA:BB:CC:DD:EE:FF", model="t50m_pro")
    assert data["success"] is False and data["error_type"] == "not_implemented"


async def test_dymo_tool_dry_run_needs_no_hardware():
    data = await _call("dymo_management", action="print_label", text="Hello", dry_run=True)
    assert data["success"] is True and data["data"]["sent"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="real spooler lookup is Windows-only")
async def test_dymo_tool_status_against_the_real_spooler_never_fakes_a_printer():
    data = await _call("dymo_management", action="status")
    # Either a real DYMO printer is installed on this machine, or the answer is an honest error.
    if data["success"]:
        assert "dymo" in (data["data"]["printer"] + data["data"]["driver"]).lower()
    else:
        assert data["error_type"] == "device_not_found"


# --- diagnostics --------------------------------------------------------------------------

USB_DYMO = {
    "Status": "OK",
    "Class": "USB",
    "FriendlyName": "DYMO MobileLabeler",
    "InstanceId": "USB\\VID_0922&PID_1009\1234",
}
BT_DYMO_OFF = {
    "Status": "Unknown",
    "Class": "Bluetooth",
    "FriendlyName": "DYMO MobileLabeler",
    "InstanceId": "BTHENUM\\DEV_001122334455\7&1",
}


def test_parse_pnp_json_splits_usb_and_bluetooth_and_marks_presence():
    import json

    parsed = dc.parse_pnp_json(json.dumps([USB_DYMO, BT_DYMO_OFF]))
    assert [d["present"] for d in parsed["usb"]] == [True]
    assert [(d["name"], d["present"]) for d in parsed["bluetooth"]] == [("DYMO MobileLabeler", False)]


def test_parse_pnp_json_handles_single_object_empty_and_unrelated_usb():
    import json

    assert (
        len(dc.parse_pnp_json(json.dumps(USB_DYMO))["usb"]) == 1
    )  # PowerShell emits an object, not a list, for one hit
    assert dc.parse_pnp_json("") == {"usb": [], "bluetooth": []}
    other = {**USB_DYMO, "InstanceId": "USB\\VID_046D&PID_C52B\1"}  # a Logitech receiver named like a match
    assert dc.parse_pnp_json(json.dumps(other))["usb"] == []


class HwSpooler(FakeSpooler):
    def __init__(self, hardware, printers=None):
        super().__init__(printers=printers)
        self._hw = hardware

    def hardware(self):
        return self._hw


def _hw(*, usb=(), bt=()):
    import json

    return dc.parse_pnp_json(json.dumps([*usb, *bt]))


async def test_diagnose_nothing_detected():
    d = await dc.DymoClient(backend=HwSpooler(_hw())).diagnose()
    assert d["verdict"] == "nothing_detected" and "plug it in" in d["next_steps"][0]


async def test_diagnose_usb_attached_but_no_driver():
    d = await dc.DymoClient(backend=HwSpooler(_hw(usb=[USB_DYMO]))).diagnose()
    assert d["verdict"] == "driver_missing"
    assert "DYMO Connect" in " ".join(d["next_steps"]) and "MobileLabeler" in d["message"]


async def test_diagnose_bluetooth_paired_but_off():
    d = await dc.DymoClient(backend=HwSpooler(_hw(bt=[BT_DYMO_OFF]))).diagnose()
    assert d["verdict"] == "device_off_or_out_of_range"


async def test_diagnose_ready_when_a_dymo_queue_exists():
    d = await dc.DymoClient(backend=HwSpooler(_hw(usb=[USB_DYMO]), printers=[_dymo()])).diagnose()
    assert d["verdict"] == "ready" and d["printers"][0]["name"] == "DYMO MobileLabeler"


async def test_not_found_error_carries_the_verdict_and_hardware():
    client = dc.DymoClient(backend=HwSpooler(_hw(usb=[USB_DYMO])))
    with pytest.raises(dc.DymoError) as exc:
        await client.print_label("x")
    assert exc.value.details["verdict"] == "driver_missing"
    assert exc.value.details["hardware"]["usb"][0]["name"] == "DYMO MobileLabeler"


async def test_diagnose_tool_via_mcp_never_fails_without_a_printer():
    data = await _call("dymo_management", action="diagnose")
    assert data["success"] is True
    assert data["data"]["verdict"] in {"nothing_detected", "driver_missing", "device_off_or_out_of_range", "ready"}
