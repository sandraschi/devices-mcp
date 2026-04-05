# Chaos Test Plan (2025-11-12)

## Objectives

- Validate resiliency of the home surveillance stack under failure scenarios.
- Ensure dashboards, alerts, and ingest pipelines recover gracefully.
- Provide repeatable experiments for regression testing.

## Target Components

1. **Camera Streams**
   - Simulate RTSP outage / disconnect.
   - Induce network latency spikes.
2. **Edge Agents**
   - Kill edge collector process unexpectedly.
   - Saturate CPU / memory.
3. **Prometheus / Loki**
   - Restart services mid-scrape.
   - Block storage directory temporarily.
4. **Alert Pipeline**
   - Drop webhook connectivity (Slack/Pager).
   - Delay email delivery.

## Tooling

- `chaos-mesh` or `litmuschaos` for Kubernetes deployments (future).
- For bare metal / containers:
  - `pumba` (Docker chaos).
  - `tc` (traffic control) via Ansible playbooks.
  - Custom Python scripts using `subprocess` to toggle services.

## Experiments (Phase 1)

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| CT-01 | Kill `devices-mcp` process | Alert triggers, dashboard shows offline, process restarts via supervisor. |
| CT-02 | Drop network between camera and hub for 60s | Camera status transitions to offline, alert fires, recovers after link restoration. |
| CT-03 | Fill Loki storage volume | Promtail backpressure observed, alerts for log ingestion latency. |
| CT-04 | Induce 500ms latency on Prometheus scrape | Dashboard shows delayed metrics, no data gaps >2 minutes. |

## Automation

- Add Ansible playbook tasks to trigger experiments (leveraging `shell` or `community.general.sysrq` modules).
- Integrate chaos scenarios into nightly pipeline once instrumentation stable.
- Capture metrics before/after experiment for reporting.

## Next Steps

1. Prototype CT-01 and CT-02 using simple shell scripts.
2. Instrument metrics to detect experiment start/stop (custom Prometheus push).
3. Document recovery procedures in runbooks.
4. Scale to CT-03/CT-04 once storage stack matured.
