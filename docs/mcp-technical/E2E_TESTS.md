# End-to-End Tests (2025-11-12)

- `tests/e2e/test_sensor_api.py` validates the sensor ingestion flow from the
  FastAPI web layer.
- Uses `WebServer` instance and monkeypatched `tapo_plug_manager` to emulate real
  device data.
- Coverage:
  - `/api/sensors/tapo-p115` returns structured device payload with host label.
  - `/api/sensors/tapo-p115/{device_id}/history` returns energy usage series.
- Acts as regression guard ensuring new ingestion adapters remain wired into the
  HTTP surface.
- Future additions:
  - Camera stream API verification (snapshot endpoints).
  - Combined metrics-to-dashboard checks once Prometheus exporter endpoints are
    finalized.
