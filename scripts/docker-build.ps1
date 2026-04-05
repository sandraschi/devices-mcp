#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build Docker containers with smart caching

.DESCRIPTION
    Builds Docker containers using layer caching for faster incremental builds.
    Use --no-cache only when you need a completely fresh build (e.g., after
    dependency changes or when debugging build issues).

.PARAMETER NoCache
    Force a complete rebuild without using cache (slower but ensures fresh build)

.PARAMETER Service
    Specific service to build (default: all services)

.EXAMPLE
    .\scripts\docker-build.ps1
    # Fast incremental build using cache

.EXAMPLE
    .\scripts\docker-build.ps1 -NoCache
    # Complete rebuild without cache (use when dependencies change)
#>

param(
    [switch]$NoCache = $false,
    [string]$Service = ""
)

$composeFile = "deploy/myhomecontrol/docker-compose.yml"

if (-not (Test-Path $composeFile)) {
    Write-Host "❌ Docker Compose file not found: $composeFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          🐳 Docker Build (Smart Caching) 🐳            ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

if ($NoCache) {
    Write-Host "⚠️  Building WITHOUT cache (slower but fresh)" -ForegroundColor Yellow
    Write-Host "   Use this when:" -ForegroundColor Gray
    Write-Host "   - Dependencies changed" -ForegroundColor Gray
    Write-Host "   - Debugging build issues" -ForegroundColor Gray
    Write-Host "   - Need completely fresh build`n" -ForegroundColor Gray
    $buildArgs = @("--no-cache")
} else {
    Write-Host "✅ Building WITH cache (faster incremental builds)" -ForegroundColor Green
    Write-Host "   Docker will reuse cached layers when possible" -ForegroundColor Gray
    Write-Host "   ⚡ Avoids re-downloading packages and system deps`n" -ForegroundColor Gray
    $buildArgs = @()
}

if ($Service) {
    Write-Host "📦 Building service: $Service" -ForegroundColor Cyan
    $buildArgs += $Service
} else {
    Write-Host "📦 Building all services" -ForegroundColor Cyan
}

Write-Host ""

# Change to compose file directory
Push-Location (Split-Path $composeFile -Parent)

try {
    $buildStart = Get-Date

    if ($buildArgs.Count -gt 0) {
        docker compose -f (Split-Path $composeFile -Leaf) build @buildArgs
    } else {
        docker compose -f (Split-Path $composeFile -Leaf) build
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ Build failed!" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    $buildDuration = (Get-Date) - $buildStart

    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              ✅ Build Complete! ✅                       ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "⏱️  Build time: $([math]::Round($buildDuration.TotalSeconds, 1))s" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Next steps:" -ForegroundColor White
    Write-Host "   docker compose -f deploy/myhomecontrol/docker-compose.yml up -d" -ForegroundColor Gray
    Write-Host ""

} finally {
    Pop-Location
}
