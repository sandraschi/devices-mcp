#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== devices-mcp sidecar build ===" -ForegroundColor Cyan

Push-Location $Root
try {
    $pi = uv run pyinstaller --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "-> Installing PyInstaller..." -ForegroundColor Yellow
        uv pip install pyinstaller
    } else {
        Write-Host "-> PyInstaller: $pi" -ForegroundColor Gray
    }

    Write-Host "-> Building frontend (bundled into backend)..." -ForegroundColor Yellow
    Push-Location "$Root\web-sota\frontend"
    try {
        if (-not (Test-Path "node_modules")) {
            npm install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
        }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "vite build failed" }
    } finally {
        Pop-Location
    }

    Remove-Item -Recurse -Force "$Root\build\devices-mcp-backend" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$Root\build\devices-mcp-camera" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\devices-mcp-backend.exe" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\devices-mcp-camera.exe" -ErrorAction SilentlyContinue

    Write-Host "-> PyInstaller web backend..." -ForegroundColor Yellow
    uv run pyinstaller devices-mcp-backend.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "Backend PyInstaller failed (exit $LASTEXITCODE)" }

    Write-Host "-> PyInstaller camera helper (lean)..." -ForegroundColor Yellow
    uv run pyinstaller devices-mcp-camera.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "Camera PyInstaller failed (exit $LASTEXITCODE)" }

    $triple = "x86_64-pc-windows-msvc"
    $backendSrc = "$Root\dist\devices-mcp-backend.exe"
    $cameraSrc = "$Root\dist\devices-mcp-camera.exe"
    if (-not (Test-Path $backendSrc)) { throw "Missing $backendSrc" }
    if (-not (Test-Path $cameraSrc)) { throw "Missing $cameraSrc" }

    $resDir = "$Root\native\resources"
    New-Item -ItemType Directory -Path $resDir -Force | Out-Null
    Copy-Item $backendSrc "$resDir\devices-mcp-backend.exe" -Force
    Copy-Item $cameraSrc "$resDir\devices-mcp-camera.exe" -Force

    $binDir = "$Root\native\binaries"
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    Copy-Item $backendSrc "$binDir\devices-mcp-backend-$triple.exe" -Force

    $mbBe = [math]::Round((Get-Item "$resDir\devices-mcp-backend.exe").Length / 1MB, 1)
    $mbCam = [math]::Round((Get-Item "$resDir\devices-mcp-camera.exe").Length / 1MB, 1)
    Write-Host "=== Sidecars ready ===" -ForegroundColor Green
    Write-Host "  Backend: ${mbBe} MB" -ForegroundColor Cyan
    Write-Host "  Camera:  ${mbCam} MB (lean, no DNN/CUDA)" -ForegroundColor Cyan
} finally {
    Pop-Location
}
