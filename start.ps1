Param([switch]$Headless)

# --- SOTA Headless Standard ---
if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch 'Hidden')) {
    Start-Process pwsh -ArgumentList '-NoProfile', '-File', $PSCommandPath, '-Headless' -WindowStyle Hidden
    exit
}
$WindowStyle = if ($Headless) { 'Hidden' } else { 'Normal' }
# ------------------------------

$env:FASTMCP_LOG_LEVEL = 'WARNING'
# schip-mcp-devices Start - Standards-Compliant SOTA
Write-Host 'Starting schip-mcp-devices...' -ForegroundColor Cyan

# Start Windows Camera Server (optional, port 10715)
$CamServerJob = Start-Job -Name "WinCamServer" -ScriptBlock {
    Set-Location $using:PWD
    uv run scripts/windows_camera_server.py 2>&1 | Out-File "$env:TEMP\devices-mcp-cam-server.log" -Append
}
Write-Host "  Camera server started (job id: $($CamServerJob.Id))" -ForegroundColor DarkGray

# Brief pause for camera server to initialize (auto-discover + HTTP server start)
Start-Sleep -Seconds 3

try {
    uv run -m schip_mcp_devices
} finally {
    Write-Host "Stopping camera server..." -ForegroundColor DarkGray
    Stop-Job -Name "WinCamServer" -ErrorAction SilentlyContinue
    Remove-Job -Name "WinCamServer" -ErrorAction SilentlyContinue
}