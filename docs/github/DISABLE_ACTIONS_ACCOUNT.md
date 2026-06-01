# Disable GitHub Actions (account-wide stop)

GitHub has **no single switch** on a **personal** account to turn off Actions for every repository at once. You combine:

1. **Billing** (stops paid / blocked runners — you already hit this with the expired card)
2. **Spending limit $0** (no new overage)
3. **Per-repository disable** (stops workflows from running, including on public repos)

Organizations can set a default policy; personal accounts must use per-repo settings or the API script below.

## Do this first (billing)

1. [Billing → Payment information](https://github.com/settings/billing/payment_information) — update card if you plan to pay the ~$337 balance.
2. [Billing → Spending limits](https://github.com/settings/billing/spending_limit) — set **Actions** to **$0** so overage cannot accrue after payment is fixed.

## Disable Actions on every repo (manual)

Per repo: **Settings → Actions → General → Disable actions** → Save.

Fine for a handful of repos; not practical for 100+.

## Safe bulk disable (personal account)

Script: `scripts/disable-github-actions.ps1` in this repo.

- **Default: dry-run** (lists repos only).
- **Requires `-Confirm`** to call the API.
- Writes `scripts/github-actions-state.json` so you can re-enable later with `-Enable -Confirm`.

```powershell
# Preview (no changes)
pwsh -File scripts/disable-github-actions.ps1

# Disable Actions on all sandraschi repos you can admin
pwsh -File scripts/disable-github-actions.ps1 -Confirm

# Later: restore from state file
pwsh -File scripts/disable-github-actions.ps1 -Enable -Confirm
```

**Does not** delete `.github/workflows/` — workflows remain in git but **do not run** until you re-enable Actions.

## When you want CI again

1. Re-enable Actions on specific public repos only.
2. Apply [LIGHTWEIGHT_CI_POLICY.md](LIGHTWEIGHT_CI_POLICY.md) (one `windows-latest` job).
3. Keep private docs repos disabled.

## Dependabot

Disabling Actions stops workflow runs; **Dependabot security updates** can still open PRs. Turn off under **Settings → Code security** per repo or org if PR noise continues.
