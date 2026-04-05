# Camera Dashboard Notes (2025-11-12)

- Dashboard: `grafana/provisioning/dashboards/camera-overview.json`
- Datasource: `Prometheus` (`grafana/provisioning/datasources/prometheus.yaml`)
- Panels:
  - **Online Cameras** – `sum(tapo_camera_status{status="online"})`
  - **Offline Cameras** – Table of `tapo_camera_status{status!="online"}`
  - **Stream Bitrate** – Timeseries over `tapo_camera_stream_bitrate`
- Variable: `instance` derives from metric label to filter per edge site.
- Refresh interval: 30 seconds.

Next steps:

1. Ensure `metrics_service` exports `tapo_camera_status` and
   `tapo_camera_stream_bitrate`.
2. Embed camera thumbnails via custom plugin once stream metrics validated.
3. Add alert annotation stream after Alertmanager wiring is live.
