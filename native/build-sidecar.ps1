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

    Remove-Item -Recurse -Force "$Root\build\devices-mcp-camera" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$Root\build\devices-mcp-backend" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\devices-mcp-camera.exe" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\devices-mcp-backend.exe" -ErrorAction SilentlyContinue

    Write-Host "-> PyInstaller camera helper..." -ForegroundColor Yellow
    uv run pyinstaller devices-mcp-camera.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "Camera PyInstaller failed (exit $LASTEXITCODE)" }

    Write-Host "-> PyInstaller web backend..." -ForegroundColor Yellow
    uv run pyinstaller devices-mcp-backend.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "Backend PyInstaller failed (exit $LASTEXITCODE)" }

    $triple = "x86_64-pc-windows-msvc"
    $dstDir = "$Root\native\binaries"
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null

    $cameraSrc = "$Root\dist\devices-mcp-camera.exe"
    $backendSrc = "$Root\dist\devices-mcp-backend.exe"
    if (-not (Test-Path $cameraSrc)) { throw "Missing $cameraSrc" }
    if (-not (Test-Path $backendSrc)) { throw "Missing $backendSrc" }

    Copy-Item $cameraSrc "$dstDir\devices-mcp-camera-$triple.exe" -Force
    Copy-Item $backendSrc "$dstDir\devices-mcp-backend-$triple.exe" -Force

    Write-Host "=== Sidecars ready ===" -ForegroundColor Green
    Write-Host "  $dstDir\devices-mcp-camera-$triple.exe" -ForegroundColor Cyan
    Write-Host "  $dstDir\devices-mcp-backend-$triple.exe" -ForegroundColor Cyan
} finally {
    Pop-Location
}
