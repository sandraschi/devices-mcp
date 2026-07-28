set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

MCP_CENTRAL_DIR := "..\\mcp-central-docs"
WEBROOT := "web-sota"

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Dev ───────────────────────────────────────────────────────────────────────

# Start web-sota dev server (frontend + backend)
dev:
    Set-Location "{{justfile_directory()}}\{{WEBROOT}}"
    .\start.ps1

# Run frontend TypeScript type-check
typecheck:
    Set-Location "{{justfile_directory()}}\{{WEBROOT}}\frontend"
    npx tsc --noEmit

# Build frontend for production
build:
    Set-Location "{{justfile_directory()}}\{{WEBROOT}}\frontend"
    npm run build

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff linting
lint:
    Set-Location "{{justfile_directory()}}"
    uv run ruff check .

# Execute Ruff fix and formatting
fix:
    Set-Location "{{justfile_directory()}}"
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location "{{justfile_directory()}}"
    uv run bandit -r src\

# Execute safety audit of dependencies
audit-deps:
    Set-Location "{{justfile_directory()}}"
    uv run safety check

# ── Native Desktop ────────────────────────────────────────────────────────────

# Build Tauri NSIS desktop installer
build-native:
    Set-Location '{{justfile_directory()}}\native'; $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"; & .\build.ps1

# ── Testing ───────────────────────────────────────────────────────────────────

# Run e2e Playwright tests
e2e:
    powershell.exe -NoProfile -NoProfile -ExecutionPolicy Bypass -File "D:\Dev\repos\mcp-central-docs\scripts\playwright-audit.ps1" -RepoPath "{{justfile_directory()}}"
