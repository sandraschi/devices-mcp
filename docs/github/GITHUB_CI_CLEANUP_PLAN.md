# GitHub `.github` cleanup plan (review only — do not apply until approved)

**Status:** PLAN ONLY — no files have been deleted as part of this document.

**Context:** 2025 Actions billable **$336.98** (consumed $415.10 − discounts $78.11). Top repositories:

| Repository | Gross (2025) | Notes |
|------------|--------------|--------|
| database-operations-mcp | **$259.25** | ~62% of total — see root-cause section |
| virtualization-mcp | $29.33 | industrial-launch + ci + test |
| MediaDashboards | $25.86 | Not in local `D:\Dev\repos` — verify on GitHub |
| advanced-memory-mcp | $21.10 | industrial-launch + ci.yml |
| nest-protect-mcp | $14.61 | ci + 3 scheduled maintenance-style workflows |

**Policy after cleanup:**

- **Public** code repos: at most one lean `ci.yml` on **`windows-latest`** (Python 3.12, `uv`, ruff + short pytest). `release.yml` **only** on tag `v*` (may stay Ubuntu for Linux/Tauri/MCPB build steps if needed).
- **Private** (e.g. `mcp-central-docs`): **no** workflows, or disable Actions in repo settings.
- **Never delete** `*.md` under `.github` (templates, `ci-improvements.md`, etc.) — disable workflows instead if you want to preserve docs.
- **No fleet batch scripts** — one repo at a time, commit, push, verify billing.

---

## Why `database-operations-mcp` cost ~$259

This repo is the fleet’s Actions furnace. It is **public now**, but 2025 charges almost certainly accrued while it was **private** (or before public-runner free tier applied to your account). Billable usage is tied to **when** jobs ran, not today’s visibility.

### 1. Two full CI pipelines on every push

Both run on `push` / `pull_request` to `main` / `master` / `develop`:

| File | What it does | Cost driver |
|------|----------------|-------------|
| **`ci-cd.yml`** | Matrix **3 Python × 3 OS** (Ubuntu, **Windows**, **macOS**) = **9 test jobs** per push; plus lint, build, TestPyPI, PyPI publish, GitHub release on tags | Windows ≈ **2×**, macOS ≈ **10×** minute multipliers vs Linux on private billing |
| **`ci.yml`** | Separate “full” pipeline: lint, **PowerShell lint on `windows-latest`**, tests on 3.11+3.12, **duplicate security** (bandit/safety), build, MCPB build, integration tests, quality gate | **~10+ jobs per push**, overlaps with `ci-cd.yml` |

**Every push to `main` ≈ 20+ jobs**, many on expensive OS runners, often running the same checks twice.

### 2. Scheduled workflows (run even when you don’t push)

| File | Schedule | Effect |
|------|----------|--------|
| **`beta-testing.yml`** | **Daily** `0 2 * * *` | Multiple jobs (quality, performance, …) every night |
| **`security.yml`** | **Weekly** Sunday 06:00 UTC | Full safety/bandit/semgrep + artifacts |
| **`dependency-updates.yml`** | **Weekly** Monday 02:00 UTC | `uv lock --upgrade`, pytest, **opens a PR** → each PR retriggers **both** CI pipelines |

### 3. Release / publish churn

| File | Trigger | Effect |
|------|---------|--------|
| **`release.yml`** | Tags `v*` + manual | Build, PyPI, GH release |
| **`manual-release.yml`** | `workflow_dispatch` | Extra release path |
| **`ci-cd.yml`** | Tags + develop/main | TestPyPI + PyPI + release jobs on tags |

### 4. Fleet / sync pushes

If automation pushes to `main` often (hourly fleet sync, doc bots, etc.), the above multiplies: **each sync ≈ full double pipeline**.

### Order-of-magnitude math (private billing)

Example: one push ≈ 400–600 **billable** minutes (9 matrix jobs with Win/Mac + ~10 jobs in `ci.yml`).

- At ~$0.008/min (Linux baseline; Win/Mac higher): **~$3–5 per push**
- **~50–80 pushes** in 2025 → **~$150–$400** (matches **$259.25**)

**Conclusion:** Cost is explained by **duplicate mega-CI + Windows/macOS matrix + daily/weekly cron + dependency PRs**, not a mystery leak.

---

## Recommended target state (all public MCP repos)

| Keep | Remove / disable |
|------|------------------|
| `ci.yml` — **1 job**, `windows-latest`, Python 3.12, `uv sync`, `ruff check`, `pytest tests/unit -q` | `ci-cd.yml`, second `ci.yml`, extra OS matrix jobs |
| `release.yml` — **only** `on: push: tags: ['v*']`, build MCPB + attach assets | `industrial-launch.yml`, `manual-release.yml` (merge into `release.yml` if needed) |
| Issue/PR templates, `*.md` docs | `dependabot.yml` (or keep disabled file) |
| | `security.yml`, `security-scan.yml`, `codeql.yml`, `semgrep.yml` |
| | `beta-testing.yml`, `megatest.yml`, `dependency-updates.yml`, `dependencies.yml` |
| | `ci-comprehensive.yml`, `docker.yml` (unless you actively publish images) |
| | `notifications.yml`, `maintenance.yml` (scheduled) |

Rename to `*.yml.disabled` if you want to keep files for later reinstatement **without** GitHub running them.

---

## Per-repository plan

Legend:

- **DELETE** — remove workflow file (or disable Actions for whole repo).
- **DISABLE** — rename to `.yml.disabled` or delete only the `on:` triggers (you prefer keeping MD/docs).
- **KEEP** — leave as-is or slim down in a second pass.
- **SLIM** — replace with minimal `ci.yml` / tag-only `release.yml`.

### Tier 1 — 2025 top spenders (do first)

#### `database-operations-mcp` (~$259)

| Path | Action | Reason |
|------|--------|--------|
| `.github/workflows/ci-cd.yml` | **DISABLE** | 9-job OS matrix + PyPI; duplicates `ci.yml` |
| `.github/workflows/ci.yml` | **SLIM** → **single `windows-latest` job** (merge PS lint + tests; drop duplicate security) | One pipeline only |
| `.github/workflows/security.yml` | **DISABLE** | Weekly cron + duplicate of security job in old `ci.yml` |
| `.github/workflows/beta-testing.yml` | **DISABLE** | **Daily** cron — major silent burn |
| `.github/workflows/dependency-updates.yml` | **DISABLE** | Weekly PR factory → retriggers CI |
| `.github/workflows/manual-release.yml` | **DISABLE** | Redundant with `release.yml` |
| `.github/workflows/release.yml` | **KEEP** (tag-only) | OK if only `v*`; remove `workflow_dispatch` if unused |
| `.github/dependabot.yml.disabled` | **KEEP** | Already disabled |
| `.github/ISSUE_TEMPLATE/*` | **KEEP** | Not billed |

#### `virtualization-mcp` (~$29)

| Path | Action | Reason |
|------|--------|--------|
| `.github/workflows/industrial-launch.yml` | **DISABLE** | Tag PyPI industrial pipeline |
| `.github/workflows/ci.yml` | **SLIM** | Active CI |
| `.github/workflows/test.yml` | **DISABLE** | Likely duplicate of ci |
| `.github/workflows/*.disabled` | **KEEP** | Already inactive (no runner cost) |
| `.github/release-drafter.yml` | **KEEP** | Low cost |

#### `MediaDashboards` (~$26)

Not found under `D:\Dev\repos`. **On GitHub:** Settings → Actions → Usage, then mirror Tier 1 rules (look for matrix, Win/Mac, `schedule:`).

#### `advanced-memory-mcp` (~$21)

| Path | Action | Reason |
|------|--------|--------|
| `.github/workflows/industrial-launch.yml` | **DISABLE** | Industrial PyPI |
| `.github/workflows/ci.yml` | **SLIM** | Only active CI |
| `.github/workflows/*.disabled` | **KEEP** | Inactive |
| `.github/stale.yml` | **REVIEW** | May open/close issues; usually low cost |

#### `nest-protect-mcp` (~$15)

| Path | Action | Reason |
|------|--------|--------|
| `.github/workflows/maintenance.yml` | **DISABLE** | **Scheduled** weekly |
| `.github/workflows/dependency.yml` | **DISABLE** | Scheduled / dep PRs |
| `.github/workflows/notifications.yml` | **DISABLE** | Likely scheduled |
| `.github/workflows/docker.yml` | **DISABLE** | Docker builds are expensive |
| `.github/workflows/ci.yml` | **SLIM** | Keep one check |
| `.github/workflows/release.yml` | **KEEP** (tag-only) | |

---

### Tier 2 — `devices-mcp` (formerly tapo-camera-mcp)

| Path | Action | Reason |
|------|--------|--------|
| `.github/workflows/ci-comprehensive.yml` | **DISABLE** | 25+ jobs, daily cron |
| `.github/workflows/industrial-launch.yml` | **DISABLE** | Duplicate of release / PyPI |
| `.github/workflows/ci.yml` | **SLIM** | One job: `windows-latest`, Python 3.12 only (no matrix) |
| `.github/workflows/release.yml` | **KEEP** | Tag releases (MCPB + `tauri.exe`) |
| `.github/workflows/ci-improvements.md` | **KEEP** | Documentation only |
| `.github/dependabot.yml` | **DISABLE** | Dependabot PRs trigger Actions |

---

### Tier 3 — Industrial Launch fleet (same pattern)

Apply to each: **DISABLE** `industrial-launch.yml`; **SLIM** or keep one `ci.yml`; **DISABLE** `ci-cd.yml` if present.

Repos with `industrial-launch.yml` locally:

- `email-mcp`, `virtualization-mcp`, `git-github-mcp`, `advanced-memory-mcp`, `windows-operations-mcp`, `robotics-mcp`, `filesystem-mcp`, `docker-mcp`, `unity3d-mcp`, `calibre-mcp`, `plex-mcp`, `devices-mcp`

---

### Tier 4 — Private / docs (no CI)

#### `mcp-central-docs` (and any must-stay-private repo)

| Path | Action |
|------|--------|
| Entire `.github/workflows/` | **DELETE** or repo Settings → **Disable Actions** |
| `dependabot.yml` | **DISABLE** |

---

### Tier 5 — Other MCP repos (default template)

For each remaining repo under `sandraschi/*` with `.github/workflows/`:

1. List workflows: `gh workflow list -R sandraschi/<repo>`
2. **DISABLE** any file matching: `codeql`, `security`, `semgrep`, `megatest`, `beta-testing`, `dependency`, `industrial-launch`, `ci-comprehensive`, `ci-cd` (if `ci.yml` exists), `docker` (unless needed)
3. **SLIM** remaining `ci.yml` to one **`windows-latest`** job
4. **KEEP** `*.md`, issue templates, `CODEOWNERS`

High-risk patterns to search (read-only):

```powershell
Select-String -Path D:\Dev\repos\<repo>\.github\workflows\*.yml -Pattern 'schedule:|windows-latest|macos-latest|matrix:'
```

---

## Fleet rule: single CI runs on Windows

- **One** workflow file: `ci.yml`
- **One** job on **`windows-latest`** (matches local dev on Windows; no Linux/macOS matrix)
- **No** second pipeline (`ci-cd.yml`, comprehensive, security cron, etc.)
- Private repos: still **no CI** (Windows runner costs more if repo is private — keep docs private repos Actions-off)

On **public** repos, standard `windows-latest` minutes are still **$0** per GitHub’s public-repo policy.

## Suggested minimal `ci.yml` (reference — not applied)

```yaml
name: CI
on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  check:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Lint and test
        shell: pwsh
        run: |
          uv python install 3.12
          uv sync --extra dev
          uv run ruff check .
          uv run ruff format --check .
          uv run pytest tests/unit -q --tb=line
        continue-on-error: false
```

Optional: add a single PowerShell `Invoke-ScriptAnalyzer` step in the same job if the repo has `.ps1` scripts (do **not** add a second Windows job).

---

## Execution checklist (after you approve)

1. Fix payment method + pay outstanding balance.
2. Set account Actions **spending limit = $0** (or low cap).
3. Start with **`database-operations-mcp`** only — disable files in Tier 1 table.
4. Wait 48h; confirm Usage by repository shows drop.
5. Repeat for virtualization-mcp, nest-protect-mcp, advanced-memory-mcp.
6. Audit **MediaDashboards** on GitHub UI.
7. Fleet repos one-by-one — no batch delete scripts.

---

## Account-level (not `.github` but related)

| Item | Action |
|------|--------|
| Expired card (06/25) | Update payment method |
| Dependabot security updates | Turn off org-wide if PRs retrigger CI |
| Codespaces / Packages / Copilot | Check Usage by products — your paste showed **Actions** focus; others were $0 in selector |
| Repos still private | Make public **or** disable all Actions |

---

*Generated for review. Edit this file with ✅/❌ per row before any deletions.*
