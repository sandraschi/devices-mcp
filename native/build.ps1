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

Write-Host "-> [2/4] npm install (native CLI)..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install in native/ failed" }
} finally {
    Pop-Location
}

Write-Host "-> [3/4] PyInstaller sidecars (must run after npm install so stubs are replaced)..." -ForegroundColor Yellow
pwsh -NoLogo -File "$PSScriptRoot\build-sidecar.ps1"
if ($LASTEXITCODE -ne 0) { throw "Sidecar build failed (exit $LASTEXITCODE)" }

$triple = "x86_64-pc-windows-msvc"

# Backend embedded via bundle.resources, check in resources/
$backend = "devices-mcp-backend.exe"
$pBe = Join-Path $PSScriptRoot "resources\$backend"
if (-not (Test-Path $pBe)) { throw "Missing backend resource $pBe" }
$mbBe = [math]::Round((Get-Item $pBe).Length / 1MB, 1)
if ($mbBe -lt 5) { throw "Backend $backend is only ${mbBe} MB — stub detected" }
Write-Host "  OK $backend (${mbBe} MB)" -ForegroundColor Green

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

$version = "1.21.5"
$nsis = Get-ChildItem "$PSScriptRoot\target\release\bundle\nsis\*-setup.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
$setupOut = "$releaseDir\Devices-MCP-$version-x64-setup.exe"
if ($nsis) {
    Copy-Item $nsis.FullName $setupOut -Force
    Write-Host "Installer: $setupOut" -ForegroundColor Cyan
}

$portableDir = "$releaseDir\Devices-MCP-$version-portable"
if (Test-Path $portableDir) { Remove-Item $portableDir -Recurse -Force }
New-Item -ItemType Directory -Path $portableDir -Force | Out-Null
Copy-Item $appExe "$portableDir\Devices-MCP.exe" -Force
Copy-Item "$PSScriptRoot\binaries\devices-mcp-camera-$triple.exe" $portableDir -Force
Copy-Item "$PSScriptRoot\resources\devices-mcp-backend.exe" "$portableDir\devices-mcp-backend-$triple.exe" -Force
$configExample = "$Root\config.example.yaml"
if (Test-Path $configExample) {
    Copy-Item $configExample "$portableDir\config.example.yaml" -Force
}
$readme = @"
Devices MCP desktop (portable)
=============================
1. Copy config.example.yaml to config.yaml and edit (cameras, Hue, Ring, etc.).
2. Place config.yaml in this folder (same folder as Devices-MCP.exe).
3. Double-click Devices-MCP.exe. Dashboard opens at http://127.0.0.1:10717/app/
"@
Set-Content -Path "$portableDir\README.txt" -Value $readme -Encoding utf8
$zipOut = "$releaseDir\Devices-MCP-$version-windows-x64.zip"
if (Test-Path $zipOut) { Remove-Item $zipOut -Force }
Compress-Archive -Path "$portableDir\*" -DestinationPath $zipOut -Force
Write-Host "Portable zip: $zipOut" -ForegroundColor Cyan
Copy-Item "$portableDir\Devices-MCP.exe" "$releaseDir\tauri.exe" -Force

Write-Host "=== Build complete ===" -ForegroundColor Green
