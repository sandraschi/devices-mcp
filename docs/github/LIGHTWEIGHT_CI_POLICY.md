# Lightweight CI policy (fleet)

## Fleet rule (general)

**Single CI = `windows-latest`.** One job, one OS. No Ubuntu/macOS matrix for everyday CI.

| Use | Runner |
|-----|--------|
| `ci.yml` (lint + test on every push) | **`windows-latest`** |
| `release.yml` (tag builds, MCPB, Tauri installer) | `windows-latest` when building Windows assets; Ubuntu only if a step is Linux-only |

## Remove everywhere

- `.github/dependabot.yml` — use local `uv lock` / manual bumps; Dependabot PRs trigger Actions on private repos.
- `industrial-launch.yml` — PyPI OIDC mega-pipelines; use tag `release.yml` only where needed.
- `ci-comprehensive.yml`, `ci-cd.yml` — matrix / cron / security megatests.
- `codeql.yml`, `security-scan.yml`, `security.yml`, `semgrep.yml`
- `megatest.yml`, `beta-testing.yml`, `dependencies.yml`, scheduled `docker.yml`
- Extra `windows-latest` **jobs** in the same workflow (merge PS lint into the one CI job)

## Keep (public code repos only)

- One `ci.yml`: **`windows-latest`**, Python 3.12, `uv` + ruff + short pytest (`shell: pwsh`).
- `release.yml` on tag `v*` only (MCPB + optional `tauri.exe`).

## Private repos (e.g. mcp-central-docs)

- **No** `.github/workflows/` or disable Actions in repo settings (Windows minutes cost ~2× on private billing).

## Billing

- Public + standard runners: $0 Actions minutes (including `windows-latest`).
- Set account Actions spending limit to **$0** after clearing the overdue balance.

## How to change CI (manual only)

Do **not** run fleet-wide delete scripts. Per repo:

1. Review `.github/workflows/` in the GitHub UI or locally.
2. Disable heavy workflows one file at a time (prefer `*.yml.disabled`).
3. Keep `*.md` docs (e.g. `ci-improvements.md`) for future reinstatement.
4. Commit and push that repo only.

See [GITHUB_CI_CLEANUP_PLAN.md](GITHUB_CI_CLEANUP_PLAN.md) for per-repo disable lists.
