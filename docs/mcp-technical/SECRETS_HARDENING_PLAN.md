# Secrets Hardening Plan (2025-11-12)

## Objectives

- Centralize storage of sensitive credentials (Tapo, Ring, Nest, Slack, email).
- Provide environment-agnostic mechanism (Vault or encrypted `.env`).
- Enforce rotation policy and audit trail.

## Approach

1. **Secret Storage**
   - Adopt 1Password CLI or Hashicorp Vault for long-term secret storage.
   - For interim local dev, use `deploy/secrets/.env.example` (encrypted in Git
     using `sops` once configured).
2. **Application Consumption**
   - Load secrets via environment variables or config manager injection.
   - Update `metrics_service`/ingestion modules to accept credentials through
     secure provider (avoid plain text config files).
3. **Rotation**
   - Document rotation schedule (quarterly for service accounts).
   - Automate through Ansible role once secret backend is hooked up.

## Immediate Actions

- Generate `.env.example` with placeholders for required variables.
- Update documentation to instruct developers on retrieving secrets.
- Integrate secrets loading into startup scripts (`start.py` to read `.env`).

## Future Enhancements

- Implement `sops` with age/PGP keys for encrypted repo-stored secrets.
- Add CI checks to prevent committing plain text secrets.
- Provide audit logging for secret access (Vault policy).
