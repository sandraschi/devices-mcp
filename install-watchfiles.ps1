# Install Watchfiles Dependencies for Devices MCP WebApp Crashproofing
# Run this script to install the required dependencies for crashproofing

Write-Host "Installing watchfiles crashproofing dependencies..." -ForegroundColor Green
Write-Host "This installs watchfiles.exe and related tools for crashproofing" -ForegroundColor Cyan

# Check if we're in a virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment detected: $env:VIRTUAL_ENV" -ForegroundColor Yellow
} else {
    Write-Host "Warning: No virtual environment detected. Consider activating one first." -ForegroundColor Yellow
    Write-Host "For full development setup, use: pip install -e .[dev]" -ForegroundColor Yellow
}

# Install watchfiles dependencies
Write-Host "Installing watchfiles dependencies..." -ForegroundColor Cyan
pip install -r requirements-watchfiles.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "âœ" Watchfiles dependencies installed successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "To run Devices MCP WebApp with crashproofing:" -ForegroundColor Cyan
    Write-Host "  python watchfiles_runner.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Environment variables you can set:" -ForegroundColor Cyan
    Write-Host "  WATCHFILES_MAX_RESTARTS=10" -ForegroundColor White
    Write-Host "  WATCHFILES_RESTART_DELAY=1.0" -ForegroundColor White
    Write-Host "  WATCHFILES_HEALTH_CHECK_INTERVAL=30" -ForegroundColor White
    Write-Host "  TAPO_WEBAPP_HOST=0.0.0.0" -ForegroundColor White
    Write-Host "  TAPO_WEBAPP_PORT=7777" -ForegroundColor White
    Write-Host "  TAPO_WEBAPP_DEBUG=false" -ForegroundColor White
} else {
    Write-Host "âœ- Failed to install dependencies" -ForegroundColor Red
    exit 1
}
