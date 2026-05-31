#!/usr/bin/env pwsh
# Placeholder sidecars so `cargo check` / `tauri dev` compile before full PyInstaller build.
$ErrorActionPreference = "Stop"
$dst = Join-Path $PSScriptRoot "binaries"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
$triple = "x86_64-pc-windows-msvc"
$camera = Join-Path $dst "devices-mcp-camera-$triple.exe"
$backend = Join-Path $dst "devices-mcp-backend-$triple.exe"
$stub = Join-Path $dst "_stub-host.exe"
if (-not (Test-Path $stub)) {
    Copy-Item $env:ComSpec $stub -Force
}
Copy-Item $stub $camera -Force
Copy-Item $stub $backend -Force
Write-Host "Stub sidecars: $camera" -ForegroundColor Gray
Write-Host "Stub sidecars: $backend" -ForegroundColor Gray
Write-Host "Replace with .\build-sidecar.ps1 before release." -ForegroundColor Yellow
