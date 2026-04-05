# Quick Docker run script for Tapo Dashboard
# Usage: .\scripts\docker-run.ps1 [-Build] [-Detach] [-Logs]

param(
    [switch]$Build,    # Rebuild image before running
    [switch]$Detach,   # Run in background
    [switch]$Logs,     # Follow logs after starting
    [switch]$Stop,     # Stop the container
    [switch]$Restart   # Restart the container
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "🏠 Tapo Dashboard Docker Control" -ForegroundColor Cyan

if ($Stop) {
    Write-Host "Stopping containers..." -ForegroundColor Yellow
    docker compose down
    Write-Host "✅ Stopped" -ForegroundColor Green
    exit 0
}

if ($Restart) {
    Write-Host "Restarting containers..." -ForegroundColor Yellow
    docker compose restart
    Write-Host "✅ Restarted" -ForegroundColor Green
    if ($Logs) {
        docker compose logs -f
    }
    exit 0
}

# Check for .env file
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "⚠️  No .env file found. Creating from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "📝 Edit .env with your credentials before running!" -ForegroundColor Yellow
    }
}

if ($Build) {
    Write-Host "🔨 Building image..." -ForegroundColor Yellow
    docker compose build
}

$upArgs = @()
if ($Detach) {
    $upArgs += "-d"
}

Write-Host "STARTING dashboard..." -ForegroundColor Green
docker compose up @upArgs

if ($Detach -and $Logs) {
    Write-Host "📜 Following logs..." -ForegroundColor Cyan
    docker compose logs -f
}

if ($Detach -and -not $Logs) {
    Write-Host ""
    Write-Host "✅ Dashboard running at: http://localhost:7777" -ForegroundColor Green
    Write-Host "   Logs: docker compose logs -f" -ForegroundColor Gray
    Write-Host "   Stop: .\scripts\docker-run.ps1 -Stop" -ForegroundColor Gray
}
