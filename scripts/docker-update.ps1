#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick container update: rebuild and restart

.DESCRIPTION
    Rebuilds containers with cache (fast) and restarts them.
    Perfect for incremental code changes during development.

    USAGE AFTER CODE CHANGES:
    - After AI makes code edits, run this script
    - Or tell AI: "rebuild containers" / "update containers" / "fast build"
    - This uses Docker layer caching (only rebuilds changed code, not dependencies)

.EXAMPLE
    .\scripts\docker-update.ps1
    # Fast rebuild and restart (uses cache)
#>

$composeFile = "deploy/myhomecontrol/docker-compose.yml"

if (-not (Test-Path $composeFile)) {
    Write-Host "❌ Docker Compose file not found: $composeFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n🔄 Quick container update (with cache)..." -ForegroundColor Cyan
Write-Host "   ⚡ Reuses cached layers - no unnecessary downloads!`n" -ForegroundColor Gray

# Change to compose file directory
Push-Location (Split-Path $composeFile -Parent)

try {
    $startTime = Get-Date

    # Build with cache (fast)
    Write-Host "📦 Building (using cache)..." -ForegroundColor Cyan
    docker compose -f (Split-Path $composeFile -Leaf) build

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ Build failed!" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    # Restart containers
    Write-Host "`nRESTARTING containers..." -ForegroundColor Cyan
    docker compose -f (Split-Path $composeFile -Leaf) up -d

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ Restart failed!" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    $duration = (Get-Date) - $startTime

    Write-Host ""
    Write-Host "✅ Update complete in $([math]::Round($duration.TotalSeconds, 1))s!" -ForegroundColor Green
    Write-Host ""

} finally {
    Pop-Location
}
