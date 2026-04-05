# Start Windows Camera Server for USB cameras
# This server provides HTTP access to USB cameras for the Docker container

Write-Host "Starting Windows Camera Server..." -ForegroundColor Green

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Python not found. Please install Python 3.8+." -ForegroundColor Red
    exit 1
}

# Repo root (parent of this script if script lives in repo root)
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot
$env:PYTHONPATH = "$repoRoot;$repoRoot\src"

# Start the Windows camera server (listens on 10715 — must match WINDOWS_CAMERA_SERVER_URL / backend proxy)
Write-Host "Starting camera server on http://127.0.0.1:10715 ..." -ForegroundColor Yellow
uv run python scripts/windows_camera_server.py
