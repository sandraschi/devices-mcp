# Edge Agent Design (2025-11-12)

## Goals

- Provide a lightweight collector framework that can run on camera/sensor edge
  nodes.
- Normalize metrics and logs before forwarding to central Prometheus/Loki
  instances.
- Keep deployment flexible: systemd service, Docker container, or Python script.

## Architecture

1. **Collector Abstraction** (`EdgeCollector`):
   - Wraps protocol-specific logic (HTTP scrape, SSH command, serial bus).
   - Emits metrics as Python dictionaries and structured logs as JSON entries.
2. **Agent Manager** (`EdgeAgentManager`):
   - Registers collectors.
   - Runs them concurrently with configurable scrape intervals.
   - Exposes `scrape_once()` for pull-based integrations (e.g., Prometheus
     exporter) and `start()` for push/streaming scenarios.
3. **Configuration** (`EdgeCollectorConfig`):
   - Captures host metadata, metric endpoints, log paths, and scrape interval.
   - Future extension: authentication tokens, TLS options, per-collector plugins.

```
┌─────────────────────┐   ┌────────────────────┐
│ EdgeAgentManager    │   │ Prometheus Exporter │  (pull)
│  - register()       │──▶│  scrape_once()      │
│  - start()/stop()   │   └────────────────────┘
│  - scrape_once()    │
└────────┬────────────┘
         │ (async run)
┌────────▼───────────┐
│ EdgeCollector      │
│  - collect_metrics │──▶ metrics -> federation / gateway
│  - collect_logs    │──▶ logs -> Loki via Promtail
└────────────────────┘
```

## Implementation Notes

- Located in `src/devices_mcp/edge/agents.py`.
- Collectors are intentionally abstract; upcoming work (`edge-agents` follow-up)
  will supply concrete implementations:
  - **System collector**: wraps Node Exporter or psutil for CPU/Disk/Memory.
  - **Camera collector**: monitors RTSP availability, stream bitrate, ping
    latency.
  - **Sensor collector**: pulls P115 / Netatmo telemetry using the ingestion
    adapters already built.
- Logs will be streamed as JSON objects suitable for Promtail's `http_push`
  interface, keeping Loki integration simple.

## Next Steps

1. Implement concrete collectors for camera, sensor, and system metrics.
2. Package the agent as a service template (systemd/PM2/Docker).
3. Add Prometheus HTTP exporter endpoint that calls `scrape_once()`.
4. Integrate credentials handling (per-node secret injection).
