# Webapp Start - Standardized SOTA (Auto-Repaired V2.6)
# Ports: USB camera helper 10715 | Vite 10716 | FastAPI 10717 (adjacent block per fleet standards)
$WebPort = 10716
$BackendPort = 10717
$CameraPort = 10715
$FrontendDir = Join-Path $PSScriptRoot "web-sota\frontend"

# 1. Zombie kill: clear stack ports before bind (USB camera server 10715 + Vite 10716 + API 10717). taskkill fallback.
$portsToClear = @($CameraPort, $WebPort, $BackendPort)
Write-Host "[1] Zombie kill: clearing ports ($CameraPort USB cam, $WebPort, $BackendPort) ..." -ForegroundColor Yellow
$pids = Get-NetTCPConnection -LocalPort $portsToClear -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 4 } | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($p in $pids) {
    try {
        Stop-Process -Id $p -Force -ErrorAction Stop
        Write-Host "    Terminated PID $p" -ForegroundColor DarkGray
    } catch {
        cmd /c "taskkill /F /PID $p 2>nul"
        if ($LASTEXITCODE -eq 0) { Write-Host "    Killed PID $p (taskkill)" -ForegroundColor DarkGray }
        else { Write-Warning "Failed to terminate PID $p : $_" }
    }
}
Start-Sleep -Seconds 1

Set-Location $PSScriptRoot

$webSotaDir = Join-Path $PSScriptRoot "web-sota"
if (-not (Test-Path (Join-Path $webSotaDir "backend\server.py"))) {
    Write-Host "ERROR: web-sota backend not found at $webSotaDir" -ForegroundColor Red
    exit 1
}

# 2. Windows USB camera helper (must run before dashboard so /api/cameras/.../mjpeg can proxy to 127.0.0.1:$CameraPort)
Write-Host "Starting Windows USB camera server on port $CameraPort ..." -ForegroundColor Cyan
$cameraCmd = "`$env:PYTHONPATH = '$PSScriptRoot;$PSScriptRoot\src'; Set-Location '$PSScriptRoot'; uv run python scripts/windows_camera_server.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cameraCmd -WindowStyle Normal
Start-Sleep -Seconds 2

# 3. FastAPI backend (web-sota: full /api/cameras incl. MJPEG; dual_server alone does not mount those routes)
Write-Host "Starting web-sota API on port $BackendPort ..." -ForegroundColor Cyan
$backendCmd = "Set-Location -LiteralPath '$webSotaDir'; `$env:WINDOWS_CAMERA_SERVER_URL = 'http://127.0.0.1:$CameraPort'; `$env:PYTHONPATH = '$PSScriptRoot;$PSScriptRoot\src'; uv run python -m backend.server --host 127.0.0.1 --port $BackendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

# 4. Vite dev (frontend package lives under web-sota\frontend)
if (-not (Test-Path $FrontendDir)) {
    Write-Host "ERROR: Frontend not found at $FrontendDir" -ForegroundColor Red
    exit 1
}
Set-Location $FrontendDir
if (-not (Test-Path "node_modules")) { npm install }

Write-Host "Starting Vite frontend on port $WebPort (vite proxies /api to port $BackendPort) ..." -ForegroundColor Green
npm run dev -- --port $WebPort --host

