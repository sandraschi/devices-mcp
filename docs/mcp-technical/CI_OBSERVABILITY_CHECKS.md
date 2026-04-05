# CI Observability Checks (2025-11-12)

- GitHub Actions workflow `.github/workflows/ci.yml` now includes an
  `observability` job that validates:
  - Prometheus config (`promtool check config` + `promtool check rules`)
  - Loki config via `grafana/loki:2.9.0 -verify-config`
  - Promtail config via `grafana/promtail:2.9.0 -verify-config`
  - Alertmanager config via `prom/alertmanager:v0.27.0 --config.check`
  - Ansible linting for `infrastructure/ansible/playbooks/observability.yaml`
- Build job depends on the new validation stage.
- Docker is used to avoid installing binaries directly in the runner.
- Promtool is downloaded dynamically (`v2.52.0`) and cached per job run.
