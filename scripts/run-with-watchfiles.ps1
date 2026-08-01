# Run Devices MCP WebApp with Watchfiles Crashproofing
# This script starts the Devices MCP WebApp with automatic crash recovery

param(
    [int]$MaxRestarts = 10,
    [float]$RestartDelay = 1.0,
    [int]$HealthCheckInterval = 30,
    [string]$Host = "0.0.0.0",
    [int]$Port = 7777,
    [switch]$Debug,
    [switch]$Test
)

Write-Host "STARTING Devices MCP WebApp with Watchfiles Crashproofing" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan

# Set environment variables
$env:TAPO_WEBAPP_HOST = $Host
$env:TAPO_WEBAPP_PORT = $Port
$env:TAPO_WEBAPP_DEBUG = $Debug.ToString().ToLower()
$env:WATCHFILES_MAX_RESTARTS = $MaxRestarts.ToString()
$env:WATCHFILES_RESTART_DELAY = $RestartDelay.ToString()
$env:WATCHFILES_HEALTH_CHECK_INTERVAL = $HealthCheckInterval.ToString()

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Host: $Host" -ForegroundColor White
Write-Host "  Port: $Port" -ForegroundColor White
Write-Host "  Debug: $($Debug.ToString().ToLower())" -ForegroundColor White
Write-Host "  Max Restarts: $MaxRestarts" -ForegroundColor White
Write-Host "  Restart Delay: ${RestartDelay}s" -ForegroundColor White
Write-Host "  Health Check Interval: ${HealthCheckInterval}s" -ForegroundColor White
Write-Host ""

if ($Test) {
    Write-Host "ðŸ§ª Running in test mode..." -ForegroundColor Yellow
    python test_watchfiles_runner.py
} else {
    Write-Host "ðŸ"„ Starting crashproof runner..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop gracefully" -ForegroundColor Cyan
    Write-Host ""

    try {
        python watchfiles_runner.py
    } catch {
        Write-Host "âœ- Failed to start watchfiles runner: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "ðŸ'‹ Devices MCP WebApp watchfiles runner stopped" -ForegroundColor Green
