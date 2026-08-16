param([switch]$Headless, [switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 10717
$FrontendPort = 10716
$WebDir = Join-Path $ScriptRoot "web-sota"
$FrontendDir = Join-Path $WebDir "frontend"
$StartLog = "$env:TEMP\devices-mcp-start.log"

function Write-StartLog($msg) {
    Add-Content $StartLog "$(Get-Date -Format 'HH:mm:ss') $msg"
}
Write-StartLog "start.ps1 begin (Headless=$Headless)"

# --- SOTA Headless Standard ---
# Guard: re-spawn once into a hidden window. Uses an env var flag, NOT the
# window title: a hidden pwsh's RawUI.WindowTitle is empty (not 'Hidden'),
# so a title check re-spawns infinitely (fork storm).
if ($Headless -and -not $env:DEVICES_MCP_HEADLESS_REENTERED) {
    $env:DEVICES_MCP_HEADLESS_REENTERED = '1'
    Start-Process pwsh -ArgumentList '-NoProfile', '-File', $PSCommandPath, '-Headless' -WindowStyle Hidden
    exit
}
$WindowStyle = if ($Headless) { 'Hidden' } else { 'Normal' }

# If the NSSM service owns the backend port, skip startup (single-backend rule)
$svc = Get-Service -Name devices-mcp -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq 'Running') {
    Write-Host "devices-mcp service is already running on port $BackendPort -- skipping startup" -ForegroundColor Cyan
    exit
}

# Service banner
$Host.UI.RawUI.WindowTitle = "devices-mcp - backend :$BackendPort / frontend :$FrontendPort"
if (-not $Headless) {
    Write-Host ""
    Write-Host "  devices-mcp" -ForegroundColor Cyan
    Write-Host "  BACKEND   http://127.0.0.1:$BackendPort   (REST /api, /health)" -ForegroundColor Gray
    Write-Host "  FRONTEND  http://127.0.0.1:$FrontendPort  (webapp UI)" -ForegroundColor Gray
    Write-Host ""
}

# Port zombie clearing (LISTENING owners only - a bare ":port" pattern also
# matches client connections to the port and can kill the caller's own processes)
foreach ($port in @($BackendPort, $FrontendPort)) {
    $pids = netstat -ano | Select-String -Pattern ":$port\s.*LISTENING" |
        ForEach-Object { $f = ($_ -split '\s+'); $f[$f.Count - 1] } |
        Sort-Object -Unique
    foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
}

# Start backend (FastAPI web-sota app)
$BackendJob = Start-Job -Name "backend" -ScriptBlock {
    param($Root, $Port)
    Set-Location (Join-Path $Root "web-sota")
    uv run python -m backend.server --host 127.0.0.1 --port $Port 2>&1 |
        Out-File (Join-Path $env:TEMP "devices-mcp-backend.log") -Append
} -ArgumentList $ScriptRoot, $BackendPort

# Readiness poll
$ready = $false
for ($i = 0; $i -lt 240; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep 1
}
if (-not $ready) {
    Write-Host "Backend did not become ready on :$BackendPort" -ForegroundColor Red
    Write-Host "  log: $env:TEMP\devices-mcp-backend.log" -ForegroundColor DarkGray
}

# Start frontend (Vite dev)
if ($env:DEVICES_MCP_VITE_OFF -eq '1') {
    Write-Host "vite launch disabled (DEVICES_MCP_VITE_OFF=1)" -ForegroundColor DarkGray
} elseif (Test-Path (Join-Path $FrontendDir "package.json")) {
    try {
        Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c", "npx vite --port $FrontendPort --host" -WorkingDirectory $FrontendDir -RedirectStandardOutput "$env:TEMP\devices-mcp-vite.log" -RedirectStandardError "$env:TEMP\devices-mcp-vite-err.log"
    } catch {
        Write-Host "Frontend launch failed: $_" -ForegroundColor Red
        Add-Content "$env:TEMP\devices-mcp-backend.log" "frontend launch failed: $_"
    }
    if (-not $Headless -and -not $NoBrowser) {
        Start-Sleep 4
        Start-Process "http://127.0.0.1:$FrontendPort"
    }
} else {
    Write-Host "Frontend dir missing: $FrontendDir" -ForegroundColor DarkGray
}

# Keep-alive: block until backend exits
$heartbeat = 0
while ($true) {
    $heartbeat++
    if ($heartbeat % 30 -eq 1) { Write-StartLog "keep-alive heartbeat $heartbeat (job state: $($BackendJob.State))" }
    if ($BackendJob.State -eq "Completed" -or $BackendJob.State -eq "Failed") {
        Receive-Job $BackendJob
        Write-StartLog "backend job ended ($($BackendJob.State))"
        break
    }
    Start-Sleep 2
}
Write-StartLog "start.ps1 exiting"
