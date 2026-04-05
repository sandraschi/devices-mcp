# Configuration Management Plan (2025-11-12)

## Strategy

- Use Ansible for idempotent deployment of Prometheus, Loki, Promtail, and
  Alertmanager.
- Maintain configuration manifests within repository (`deploy/` directory).
- Support future GitOps workflows (Flux/Argo) by keeping manifests declarative.

## Assets

- `infrastructure/ansible/playbooks/observability.yaml` – entry point for
  provisioning observability stack.
- Roles (to be implemented):
  - `roles/prometheus/`
  - `roles/loki/`
  - `roles/promtail/`
  - `roles/alertmanager/`
- Inventory groups:
  - `observability`: hub server(s).
  - `edge_nodes`: per-node agents (for Promtail + edge collectors).

## Immediate Tasks

1. Create Ansible roles that:
   - Install binaries (apt or container).
   - Deploy configs from `deploy/`.
   - Manage systemd services (enable + start).
2. Add inventory example documenting hosts and variables.
3. Integrate playbook execution into CI (`ci-cd` task) via lint/test (ansible-lint).
4. Provide README with setup instructions and secrets handling guidance.

## Future Automation

- Evaluate Terraform or Pulumi if infrastructure moves to cloud.
- Consider GitOps with Flux once remote repository hosting is ready.
- Hook into `runbooks` to describe operational procedures (rollbacks, upgrades).
