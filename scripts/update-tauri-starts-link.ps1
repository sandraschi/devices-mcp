param(
    [string]$LinkName = "devices-mcp-setup.lnk",
    [string]$StartsDir = "D:\Dev\Tauri starts",
    [string]$InstallExe = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

if (-not $InstallExe) {
    $nsisDir = Join-Path $RepoRoot "native\target\release\bundle\nsis"
    $installer = Get-ChildItem -Path $nsisDir -Filter "*-setup.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $installer) { throw "No NSIS installer found in $nsisDir" }
    $InstallExe = $installer.FullName
}

if (-not (Test-Path $InstallExe)) { throw "Installer not found: $InstallExe" }

New-Item -ItemType Directory -Force -Path $StartsDir | Out-Null
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut((Join-Path $StartsDir $LinkName))
$s.TargetPath = $InstallExe
$s.Description = "Devices MCP NSIS installer ($(Get-Item $InstallExe).VersionInfo.FileVersion)"
$s.Save()
Write-Host "Updated: $StartsDir\$LinkName -> $InstallExe"
