# Start Devices MCP Dashboard (legacy: devices_mcp.web on port 7777)
# For SOTA Vite + FastAPI + USB camera helper on 10715-10717, use .\start.ps1 from repo root.

Write-Host "`n" -NoNewline
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Home Security MCP Dashboard - Starting..." -ForegroundColor White
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Set UTF-8 encoding for console
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Activate venv
& .\venv\Scripts\Activate.ps1

# Validate dependencies BEFORE starting
Write-Host "CHECK: Validating dependencies..." -ForegroundColor Cyan
python validate_dependencies.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: DEPENDENCY CHECK FAILED!" -ForegroundColor Red
    Write-Host "   Server cannot start with missing critical dependencies." -ForegroundColor Yellow
    Write-Host "   Install missing packages shown above and try again.`n" -ForegroundColor White
    exit 1
}

Write-Host "`nSUCCESS: Dependencies validated!" -ForegroundColor Green
Write-Host ""

# Check for port conflicts
$port = 7777
Write-Host "CHECK: Checking port 7777 availability..." -ForegroundColor Cyan
# Add timeout to port check (max 1 second)
$portCheckJob = Start-Job -ScriptBlock {
    Get-NetTCPConnection -LocalPort 7777 -ErrorAction SilentlyContinue
}
$portInUse = $null
if (Wait-Job -Job $portCheckJob -Timeout 1) {
    $portInUse = Receive-Job -Job $portCheckJob
    Remove-Job -Job $portCheckJob
} else {
    Remove-Job -Job $portCheckJob -Force
    Write-Host "WARNING: Port check timed out, assuming port is available" -ForegroundColor Yellow
}

if ($portInUse) {
    $processId = $portInUse.OwningProcess
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    $processName = if ($process) { $process.ProcessName } else { "Unknown" }
    $processPath = if ($process) { $process.Path } else { "N/A" }

    Write-Host "`nERROR: PORT CONFLICT DETECTED!" -ForegroundColor Red
    Write-Host "   Port 7777 is already in use by:" -ForegroundColor Yellow
    Write-Host "   • Process: $processName (PID: $processId)" -ForegroundColor White
    Write-Host "   • Path: $processPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "SOLUTION: Solutions:" -ForegroundColor Cyan
    Write-Host "   1. Stop the conflicting process:" -ForegroundColor White
    Write-Host "      Stop-Process -Id $processId -Force" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   2. Stop Docker container (if using Docker):" -ForegroundColor White
    Write-Host "      docker ps | findstr tapo" -ForegroundColor Gray
    Write-Host "      docker stop <container-id>" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   3. Use a different port:" -ForegroundColor White
    Write-Host "      python -m devices_mcp.web --host 0.0.0.0 --port 7778" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "SUCCESS: Port 7777 is available!" -ForegroundColor Green
Write-Host ""

# Start dashboard
Write-Host "START: Starting dashboard on http://localhost:7777..." -ForegroundColor Yellow
Write-Host "   Connection supervisor will monitor all devices" -ForegroundColor Gray
Write-Host "   Health dashboard: http://localhost:7777/health-dashboard" -ForegroundColor Gray
Write-Host "   Alerts dashboard: http://localhost:7777/alerts`n" -ForegroundColor Gray

python -m devices_mcp.web --host 0.0.0.0 --port 7777
