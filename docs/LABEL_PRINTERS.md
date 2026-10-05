# Label printers (Supvan / Katasymbol, Dymo)

Two MCP tools, `supvan_management` and `dymo_management`, plus `/api/dymo/*` web routes.
Code lives in `src/devices_mcp/integrations/label_printers/` and `integrations/dymo_client.py`.

## Verification status (read this first)

| Piece | Status |
|---|---|
| Supvan protocol encoding (frames, LZMA, buffers, checksums) | Tested against upstream's own test vectors and a mock printer that decodes every byte. Self-consistent; not proof a real firmware accepts it. |
| Supvan T50M Pro | Protocol verified on hardware by the upstream author (USB + Bluetooth). BLE for this model comes from a third-party web UI. |
| Supvan E11 | Verified on hardware by the E11 fork author. 96-dot print width is provisional. |
| Supvan E10 | One HCI capture of an E10pro; E10 itself unverified. |
| Supvan E16 | No capture and no hardware test. Assumed to share the E-series flow. |
| BLE / USB transports (`BlePipe`, `HidapiDevice`) | Ported, never run against a device. |
| Label orientation (which tape edge is head position 0) | Unknown. `flip_head_axis` exists for the first print. |
| Dymo spooler path | Never run against a DYMO printer. The error paths are tested; a successful print is not. |

Sources: [heeen/supvan-cups](https://github.com/heeen/supvan-cups),
[efcroasdell/supvan-cups](https://github.com/efcroasdell/supvan-cups).

## Setup

```bash
uv pip install -e ".[labels]"    # bleak + hidapi (Supvan BLE / USB). Dymo needs only pywin32.
```

## Trying it without hardware

```python
await supvan_management(action="print_label", target="mock://e11", text="Pantry")      # decodes and rebuilds the page
await supvan_management(action="print_label", target="mock://t50m_pro", text="x", dry_run=True)
await dymo_management(action="print_label", text="Flour", dry_run=True)                 # PNG preview only
```

Previews and mock pages are written to `%TEMP%\devices-mcp-labels` (override with `DEVICES_MCP_LABEL_DIR`).

## First print on real hardware: Supvan

1. `supvan_management(action="discover")`. If it reports `bleak is not installed`, install the extra.
2. `supvan_management(action="status", target="ble://<address>", model="e11")`. Expect the label width and no errors.
3. `print_label` with a short text. Check the output is not mirrored; if it is, repeat with `flip_head_axis=true`
   and tell us which setting was right so the default can be fixed.
4. For E10 / E16, expect surprises and report the printer's raw status registers (`status.raw_registers`).

Classic Bluetooth SPP (`bt://`) is not implemented and fails with `not_implemented`.

## First print on real hardware: Dymo MobileLabeler

1. Install DYMO Connect (or DYMO Label) so Windows has the driver; connect by USB or pair over Bluetooth.
2. `dymo_management(action="status")`. Note the `paper_forms` the driver reports: they decide the page geometry.
3. `dymo_management(action="print_label", text="Test", dry_run=True)` to see the preview, then print for real.
4. If the label comes out sideways or tiny, retry with `orientation="cw"`, `"ccw"` or `"none"`.

The spooler reports no tape size, tape remaining or firmware, so those fields are absent rather than invented.
