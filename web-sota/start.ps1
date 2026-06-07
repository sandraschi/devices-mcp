param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser,
    [switch]$Automated
)

$CameraPort = 10715
$WebPort = 10716
$BackendPort = 10717
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ScriptDir "frontend"

$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly
Stop-FleetPortSquatters -Ports @($WebPort, $BackendPort, $CameraPort) -Label "devices-mcp"

if (-not (Assert-FleetPortsAvailable -Ports @($WebPort, $BackendPort, $CameraPort) -Label "devices-mcp")) { exit 1 }

# 2. Setup
Set-Location -LiteralPath $ScriptDir
if (Test-Path (Join-Path $FrontendDir "package.json")) {
    Set-Location -LiteralPath $FrontendDir
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
        npm install
    }
    Set-Location -LiteralPath $ScriptDir
}

# 3. Command definitions
$cameraCmd = "`$env:PYTHONPATH = '$ProjectRoot;$ProjectRoot\src'; Set-Location '$ProjectRoot'; uv run python scripts/windows_camera_server.py"
$backendCmd = "`$env:WINDOWS_CAMERA_SERVER_URL = 'http://127.0.0.1:$CameraPort'; `$env:PYTHONPATH = '$ProjectRoot;$ProjectRoot\src'; Set-Location -LiteralPath '$ScriptDir'; uv run python -m backend.server --host 127.0.0.1 --port $BackendPort"

if ($Automated) {
    # 3a. Start camera helper in background (hidden)
    Write-Host "Starting USB camera server on port $CameraPort ..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cameraCmd -WindowStyle Hidden

    # 3b. Start backend in background (hidden)
    Write-Host "Starting Python backend on port $BackendPort ..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Hidden

    # Wait for backend to be ready
    $backendUrl = "http://127.0.0.1:$BackendPort/"
    $waited = 0
    $maxWait = 60
    while ($waited -lt $maxWait) {
        try {
            $null = Invoke-WebRequest -Uri $backendUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            break
        } catch {
            Start-Sleep -Seconds 1
            $waited++
        }
    }
    if ($waited -ge $maxWait) {
        Write-Host "Backend did not become ready in ${maxWait}s." -ForegroundColor Red
        exit 1
    }
    Write-Host "Backend ready." -ForegroundColor Green

    # 4a. Start frontend in background (hidden)
    Write-Host "Starting Vite frontend on port $WebPort ..." -ForegroundColor Cyan
    Start-Process -FilePath "npm" -ArgumentList "run", "dev", "--", "--port", $WebPort, "--host" -WorkingDirectory $FrontendDir -WindowStyle Hidden
    
    $frontendUrl = "http://127.0.0.1:$WebPort/"
    $waited = 0
    while ($waited -lt 30) {
        try {
            $null = Invoke-WebRequest -Uri $frontendUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            break
        } catch {
            Start-Sleep -Seconds 1
            $waited++
        }
    }
    
    # 5. Open browser and exit
    Start-Process $frontendUrl
    Write-Host "Browser opened at $frontendUrl" -ForegroundColor Green
    exit 0
}

# Interactive mode
Write-Host "Starting USB camera server on port $CameraPort ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cameraCmd -WindowStyle Normal

Write-Host "Starting Python backend on port $BackendPort ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Normal

# Wait for backend
$backendUrl = "http://127.0.0.1:$BackendPort/"
$waited = 0
$maxBackendWait = 30
while ($waited -lt $maxBackendWait) {
    try { $null = Invoke-WebRequest -Uri $backendUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; break } catch { Start-Sleep -Seconds 1; $waited++ }
}
if ($waited -ge $maxBackendWait) {
    Write-Host "ERROR: Backend on $BackendPort did not become ready in ${maxBackendWait}s. Check the backend window for errors." -ForegroundColor Red
    Write-Host "Press any key to continue anyway..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Launch browser polling task
$frontendUrl = "http://127.0.0.1:$WebPort/"
$pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen

if (-not $FleetStart.RunFrontend) { return }

Write-Host "Starting Vite frontend on port $WebPort ..." -ForegroundColor Green
Set-Location -LiteralPath $FrontendDir
if (-not $FleetStart.RunFrontend) { return }
npm run dev -- --port $WebPort --host



