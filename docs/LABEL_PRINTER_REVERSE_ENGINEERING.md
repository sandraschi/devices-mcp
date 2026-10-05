# Reverse engineering a label printer (DYMO MobileLabeler first)

Goal: talk to the printer without the vendor's desktop software, the way `supvan_management` does for Supvan.
This is a plan, not a result: no capture has been taken yet, and nothing below about the DYMO protocol is known
except where it says "from the manual".

Scope and ethics: this is the user's own device, for interoperability. Capture your own traffic, keep captures
and notes locally, and do not redistribute vendor software or firmware.

## What the manual tells us (DYMO MobileLabeler user guide)

| Fact | Consequence |
|---|---|
| Bluetooth **BR/EDR 2.1 or newer** (Classic, not Low Energy) | Windows pairs it as a serial-port (SPP/RFCOMM) device and creates COM ports. The Supvan BLE approach does not apply. |
| Advertises as `DYMO ML xxxx`, pairing code `0000`, up to two simultaneous connections, discoverable by default | Easy to pair with Windows; a phone and the PC can be connected at once. |
| USB 2.0 Full Speed, cable required for the desktop software's settings (discovery mode) | A USB capture is possible with the cable. |
| 300 dpi thermal transfer, max print width 19 mm, D1 tape 6/9/12/19/24 mm | 19 mm is about 224 dots across the head. (The renderer was assuming 180 dpi; fixed to 300.) |
| Mobile app: DYMO Connect (iOS and Android). Desktop: DYMO Label / DYMO Desktop software from support.dymo.com | Two independent traffic sources to capture: phone over Bluetooth, PC over USB. |
| Open source: labelle lists USB `0922:1009` (the MobileLabeler) as "no success yet" | Nobody has published a protocol. We start from sibling devices' protocols as a hypothesis only. |

Not in the manual: the command language, whether USB is printer-class or vendor-specific, how raster data is sent.

## Strategy: cheapest evidence first

1. **Bring-up** (no hacking): install the DYMO driver, `dymo_management action=diagnose` until `ready`. This also proves
   the printer works and gives a baseline label to compare against.
2. **USB capture** (Windows, USBPcap + Wireshark): the most direct view of the command stream. Start here.
3. **Raw send test**: replay a captured stream through the Windows spooler in RAW mode (no libusb driver swap needed).
4. **Bluetooth capture** only if USB and Bluetooth turn out to differ. Classic Bluetooth is hard to sniff on Windows;
   an Android phone's HCI snoop log is the practical source. With Windows already paired, you can simply write the
   USB-derived bytes to the SPP COM port and see whether it prints, which usually answers the question without a sniffer.

## Tools

| Tool | Needed for | Installed here | Install (winget, verified to exist) |
|---|---|---|---|
| Wireshark (tshark) | decode captures, export payload bytes | no | `winget install WiresharkFoundation.Wireshark` |
| USBPcap | live USB capture on Windows (filter driver; admin; may need a reboot) | no | `winget install desowin.USBPcap` |
| Android platform-tools (adb) | pull a phone's Bluetooth HCI snoop log | no | `winget install Google.PlatformTools` |
| Npcap | network capture only; not needed for USB or Bluetooth | no | comes with Wireshark if wanted |

The only phone seen on this PC's Bluetooth list is an iPhone. iOS has no simple HCI log: the route is Apple's
PacketLogger on a Mac, which this setup does not have. So Bluetooth sniffing needs an Android phone. Treat it as
optional.

Installing a capture driver needs administrator rights (UAC) and is system-level: ask before doing it.

## Phase 1: USB capture

1. Install the DYMO driver and confirm `diagnose` says `ready`.
2. Start USBPcapCMD (or Wireshark's USBPcap interface list) and pick the root hub the printer is on. Unplug and replug
   the printer while the list is open to see which hub it moves under.
3. Capture one **controlled experiment per file**, from the DYMO software, with the same tape cassette each time:

   | File | What to print | What it should reveal |
   |---|---|---|
   | `00-idle` | nothing, just open the software | status polling, handshake |
   | `01-blank` | an empty label | framing without image data |
   | `02-dot` | one black pixel in a corner | coordinate and bit order |
   | `03-column` | one vertical black line at the left, then the right | line direction, mirroring |
   | `04-bar` | a solid black bar, 1 mm tall | raster line format, line count |
   | `05-text-A` | the letter A | sanity check against a decoder |
   | `06-two` | two copies of the same label | job and cut separators |
   | `07-width-12` and `08-width-19` | same artwork on 12 mm and 19 mm tape | tape-size fields |

   Write a one-line note per file (what was printed, tape, time). Captures are evidence; unlabeled ones are noise.
4. Extract the host-to-device payload bytes. In tshark (field names can differ by version; check with
   `tshark -G fields | findstr usb`):

   ```powershell
   tshark -r 02-dot.pcapng -Y "usb.capdata && usb.endpoint_address.direction == 0" `
     -T fields -e frame.time_relative -e usb.endpoint_address -e usb.capdata
   ```

   Do the same with `direction == 1` for the printer's replies (status).
5. Diff experiments against each other: the bytes that change between `02-dot` and `04-bar` are the image data; the
   bytes that change between 12 mm and 19 mm are the tape fields.

## Phase 2: Decode

- Start from a **hypothesis**, not from scratch: sibling DYMO D1 printers (LabelManager 280/420P/PnP) are documented
  in the labelle and dymoprint sources (escape-sequence commands, one raster line per command). Check whether the
  MobileLabeler's stream resembles them. Do not assume it does.
- Find, in order: framing (start/end markers, lengths, checksums), the job header (tape width, length, density, copies),
  the raster (bytes per line, bit order, line order, mirroring), the end-of-job and cut command, and the status reply.
- Write the decoder **before** the encoder: a function that turns a captured stream back into a PBM. If it reproduces
  the label you printed, the format is understood.

## Phase 3: Encode and verify

1. Encoder test: for the same input image as a capture, our bytes must equal the captured payload (ignoring only
   fields proven to vary, such as a counter). Store sanitized captures as test fixtures.
2. Mock printer: reuse the Supvan pattern (`MockPipe`): a fake device that decodes what it receives and rebuilds the
   page. The print state machine is then testable without hardware.
3. Transport, in order of least intrusive:
   - **Windows spooler, RAW datatype**: `OpenPrinter` + `StartDocPrinter(..., "RAW")` + `WritePrinter` sends bytes
     through the installed driver's USB or Bluetooth port. No libusb, no driver replacement, and it keeps working
     when the driver is installed.
   - **SPP COM port** (Bluetooth Classic, after pairing): `pyserial`.
   - Direct USB (libusb/WinUSB) only if the above fail; it needs Zadig to swap the driver and breaks the vendor software.
4. Plug it in behind the existing `SpoolerBackend` seam as a second backend, so `dymo_management` keeps one interface.

## Safety rules (learned from the Supvan work)

- Send only streams you have captured or derived and verified. No fuzzing, no opcode sweeps.
- Never replay anything from a firmware-update or factory-reset capture. Do not capture those at all.
- Settings changes (discoverability, auto power-off) are persisted on the device. Capture them if curious, but do
  not replay them casually.
- Keep a baseline: a known-good label printed through the vendor software, so a failure can be told apart from
  a broken setup.
- Captures contain the printer's serial number and Bluetooth address. Keep raw captures out of git; commit only
  sanitized fixtures.

## Should this be its own MCP server?

No, not yet. The fleet already has **packetsniffer-mcp** (Scapy + tshark; `analyze_pcap`, `decode_pcap`, background
capture). It covers network traffic only: it has no USBPcap or HCI support today. The capture step is a few minutes
of a human operating a device and the printer's software, which an MCP cannot do for you. The hard part is reading
hex and writing a decoder, which is ordinary code plus a notes file.

If this becomes a pattern (Supvan, DYMO, the next printer), extend packetsniffer-mcp with: `usb_capture` (wraps
USBPcapCMD), `usb_payloads` and `btsnoop_payloads` (tshark field export as above), and a `diff_captures` helper.
That is a small addition to an existing server. A new repo would trigger the fleet's New Repo Gate and a full
standards pass for very little extra capability.

## Open questions the first capture answers

- Is the USB interface printer-class, or vendor-specific / serial-over-USB?
- Do USB and Bluetooth carry the same command language?
- Is there a status or tape-detection reply we can read (tape width, tape remaining)? The spooler cannot tell us.
- Does the 300 dpi head use 224 or 256 dots, and what is the exact printable width per tape size?
