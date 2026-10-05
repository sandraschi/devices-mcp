"""Dymo web route tests: real errors instead of the old mock's fake successes."""

import pytest
from backend.routes import dymo as dymo_route
from fastapi import FastAPI
from fastapi.testclient import TestClient

from devices_mcp.integrations import dymo_client as dc


class NoDymoSpooler:
    def list_printers(self):
        return [{"name": "Brother HL", "driver": "IPP", "port": "USB001", "status_bits": 0, "queued_jobs": 0}]

    def paper_forms(self, name, port):
        return []

    def print_image(self, *a, **k):
        raise AssertionError("must not print when no DYMO printer exists")


class OkSpooler:
    printed: list[str]

    def __init__(self):
        self.printed = []

    def list_printers(self):
        return [{"name": "DYMO MobileLabeler", "driver": "DYMO", "port": "USB002", "status_bits": 0, "queued_jobs": 0}]

    def paper_forms(self, name, port):
        return ["12mm"]

    def print_image(self, name, image, title, orientation):
        self.printed.append(name)
        return {"page_px": [1, 1], "drawn_px": [1, 1], "rotated_degrees": 0}


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVICES_MCP_LABEL_DIR", str(tmp_path))

    def build(spooler):
        monkeypatch.setattr(dymo_route._dymo_printer, "_client", dc.DymoClient(backend=spooler))
        app = FastAPI()
        app.include_router(dymo_route.router)
        return TestClient(app)

    return build


def test_status_without_a_dymo_printer_is_503_not_fake_ok(make_client):
    r = make_client(NoDymoSpooler()).get("/api/dymo/status")
    assert r.status_code == 503
    assert r.json()["detail"]["error_type"] == "device_not_found"


def test_print_without_a_dymo_printer_is_503_not_fake_ok(make_client):
    r = make_client(NoDymoSpooler()).post("/api/dymo/print", json={"text": "hello"})
    assert r.status_code == 503


def test_print_succeeds_only_when_the_spooler_took_the_job(make_client):
    spool = OkSpooler()
    r = make_client(spool).post("/api/dymo/print", json={"text": "hello", "tape_size": "12mm"})
    assert r.status_code == 200
    assert r.json()["result"]["sent"] is True and spool.printed == ["DYMO MobileLabeler"]


def test_status_has_no_fabricated_fields(make_client):
    body = make_client(OkSpooler()).get("/api/dymo/status").json()["status"]
    assert body["printer"] == "DYMO MobileLabeler"
    assert "tape_remaining" not in body and "firmware_version" not in body


def test_invalid_tape_size_is_422(make_client):
    r = make_client(OkSpooler()).post("/api/dymo/print", json={"text": "x", "tape_size": "99mm"})
    assert r.status_code == 422


def test_batch_reports_how_many_printed_on_partial_failure(make_client):
    class FailsSecond(OkSpooler):
        def print_image(self, name, image, title, orientation):
            if self.printed:
                raise dc.DymoError("jam", "print_failed")
            return super().print_image(name, image, title, orientation)

    r = make_client(FailsSecond()).post("/api/dymo/batch", json={"labels": ["a", "b", "c"]})
    assert r.status_code == 502
    assert r.json()["detail"]["printed"] == 1


def test_shopping_labels_use_a_font_safe_checkbox(make_client):
    spool = OkSpooler()
    r = make_client(spool).post("/api/dymo/shopping", json={"items": ["Milk"], "include_checkboxes": True})
    assert r.status_code == 200
    assert r.json()["result"]["results"][0]["label_text"] == "[ ] Milk"


def test_tape_colors_endpoint_says_colour_is_not_software_controlled(make_client):
    body = make_client(OkSpooler()).get("/api/dymo/tape_colors").json()
    assert "cassette" in body["note"]
