# Hardware, Ingestion, and Network Inventory

## Overview

This inventory captures the currently documented hardware, active ingestion
endpoints, and the known network layout for the home security surveillance
stack that the `devices-mcp` platform orchestrates. It reflects repository
documentation as of **2025-11-12** and highlights data gaps that need field
verification during onsite assessment.

## Hardware Inventory

| Device / Service           | Category            | Deployment Location | Ingestion Path               | Status (Repo Docs) | Notes |
|----------------------------|---------------------|---------------------|------------------------------|--------------------|-------|
| TP-Link Tapo C200 / C210   | IP Camera           | Living areas        | `devices_mcp` (RTSP/HTTPS) | Pending auth completion | Requires credential validation and stable RTSP connectivity. |
| USB Webcams (generic)      | USB Camera          | Workstations / NUC  | `devices_mcp` (OpenCV MJPEG) | Working            | Auto-discovered via `start.py dashboard`; provides baseline live feed. |
| Petcube Bites 2 Lite       | Pet Camera          | Pet area            | `devices_mcp` (REST + WebSocket) | Supported          | Full API access documented; alternative to Furbo. |
| Ring Doorbells / Cameras   | Security Camera     | Entry points        | Ring MCP (WebRTC/WebSocket)  | Experimental        | Requires Ring MCP node with WebRTC stream proxy. |
| Nest Protect               | Smoke / CO Sensor   | Hallways            | Nest Protect MCP (HTTPS)     | Integration Ready   | Uses dedicated MCP server; ingestion via REST polling + push alerts. |
| Tapo P115 Smart Plugs      | Energy Sensor       | Appliances          | Energy dashboard ingestion (HTTP polling) | Prototype          | Limited to current-day telemetry; Home Assistant recommended for history. |
| Netatmo Weather Station    | Environmental Sensor| Balcony / Outdoor   | Weather API module (`/weather`) | Planned             | Provides temp/humidity/CO₂ data for dashboards. |
| Prometheus Node Exporter   | Infra Metrics Agent | Each edge node      | Prometheus federation        | Pending             | Required for full stack observability. |
| Loki + Promtail Agents     | Log Pipeline        | Each edge node      | Central Loki cluster         | Pending             | Needed for structured log ingestion. |

> **Action Needed:** Confirm physical inventory onsite (serial numbers, IPs,
> switch ports), validate firmware versions, and record redundant power/network
> characteristics.

## Ingestion Endpoints

| Endpoint / Service                         | Protocols | Source Hardware          | Consumer(s)                | Status | Notes |
|--------------------------------------------|-----------|---------------------------|----------------------------|--------|-------|
| `devices_mcp.web.server` (`/api/*`)    | HTTP/JSON | All managed cameras       | Web dashboard, Grafana JSON datasource | Running | Serves camera lists, snapshots, and streaming helpers. |
| `devices_mcp.metrics_service`          | HTTP/JSON | Camera manager + PTZ telemetry | Grafana / Prometheus scrape | Prototype | Emits camera health metrics; needs integration with Prometheus. |
| `devices_mcp.ingest.tapo_p115`         | TCP/TLS (vendor API) | Tapo P115 smart plugs | Energy dashboards, Prometheus exporter | New | Uses `python-kasa`; configure devices under `energy.tapo_p115` in `config.yaml` or via `TAPO_P115_HOSTS`. |
| `RingWebRtcStream` proxy                    | WebRTC/HTTPS | Ring devices             | Dashboard video panels     | Experimental | Success log on startup indicates module is importable; runtime validation outstanding. |
| Nest Protect MCP REST API                  | HTTPS     | Nest Protect sensors      | Unified dashboard          | Pending | Requires OAuth flow finalization and periodic polling routine. |
| Energy dashboard ingest (`/energy`)        | HTTP/JSON | Tapo P115 smart plugs     | Web dashboard              | Prototype | Uses lightweight polling; lacks historical persistence. |
| Weather API module (`/weather` endpoint)   | HTTP/JSON | Netatmo station           | Web dashboard, Grafana     | Planned | API scaffolding exists; needs credential onboarding. |
| Planned Prometheus federation gateway      | HTTPS     | Node exporters, MCP metrics | Central observability stack | Not deployed | Defines target architecture for distributed metrics. |
| Planned Loki ingest endpoint               | HTTPS     | Promtail agents           | Central logging dashboards | Not deployed | Required for log exploration views. |

## Network Topology (Current Understanding)

- **Core Hub (Home Lab / Rack):**
  - Runs the primary `devices-mcp` application server and hosts the web dashboard on `http://localhost:7777`.
  - Will coordinate Prometheus, Loki, and Alertmanager once provisioned.

- **Edge Nodes:**
  - Mini PCs / Raspberry Pi devices colocated near camera clusters (front door, garage, backyard) intended to host lightweight collectors (future `edge-agents`).
  - Each node needs Promtail + Node Exporter once logging/metrics rollout begins.

- **Wireless Peripherals:**
  - TP-Link Tapo cameras on 2.4 GHz Wi-Fi (RTSP/HTTPS).
  - Ring and Nest devices on vendor clouds; require outbound internet plus local discovery for some automations.

- **Access & Remote Monitoring:**
  - Tailscale provides secure remote reachability for Grafana dashboards and MCP APIs.
  - Grafana nodes will expose dashboards aggregating metrics, logs, and live video embeddings.

> **Open Items for Network Mapping**
>
> - Document VLAN segmentation (IoT vs. management vs. monitoring).
> - Capture IP reservations / DHCP scopes for each device class.
> - Verify bandwidth headroom for simultaneous multi-stream video feeds.
> - Schedule wireless heatmap / signal-strength verification for camera AP coverage.

## Next Steps for `assess-hw`

1. Validate physical hardware list against onsite assets; update this inventory with verified device IDs and firmware.
2. Map actual IP addresses, subnets, and switch ports to finalize the network diagram.
3. Capture ingestion health by sampling each endpoint (camera stream, sensor data, mock vs. real).
4. Identify hardware gaps (UPS, PoE switches, storage arrays) required for high availability.

Once validated, promote this document to the central monitoring plan and use it as the baseline for the `audit-stack` and `gap-review` tasks.
