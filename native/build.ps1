#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== devices-mcp Tauri release build ===" -ForegroundColor Cyan

Write-Host "-> [1/4] Tauri icons..." -ForegroundColor Yellow
pwsh -NoLogo -File "$Root\scripts\generate-tauri-icon.ps1"
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path "icons\icon.ico")) {
        npx --yes @tauri-apps/cli icon icons/icon.png
    }
} finally {
    Pop-Location
}

Write-Host "-> [2/4] PyInstaller sidecars..." -ForegroundColor Yellow
pwsh -NoLogo -File "$PSScriptRoot\build-sidecar.ps1"

Write-Host "-> [3/4] npm install (native CLI)..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install in native/ failed" }
} finally {
    Pop-Location
}

Write-Host "-> [4/4] Tauri bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
try {
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build
    if ($LASTEXITCODE -ne 0) { throw "tauri build failed" }
} finally {
    Pop-Location
}

$releaseDir = "$Root\dist"
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

$appExe = "$PSScriptRoot\target\release\devices-mcp-native.exe"
if (-not (Test-Path $appExe)) {
    $appExe = Get-ChildItem "$PSScriptRoot\target\release\*.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notmatch '^(WebView2|msiexec)' } |
        Sort-Object Length -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $appExe -or -not (Test-Path $appExe)) {
    throw "Tauri app executable not found under native/target/release"
}
Copy-Item $appExe "$releaseDir\tauri.exe" -Force
Write-Host "Release asset: $releaseDir\tauri.exe" -ForegroundColor Cyan

$nsis = Get-ChildItem "$PSScriptRoot\target\release\bundle\nsis\*-setup.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
Write-Host "=== Build complete ===" -ForegroundColor Green
if ($nsis) {
    Write-Host "Installer: $($nsis.FullName)" -ForegroundColor Cyan
}
