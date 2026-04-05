# Comprehensive Installation Script for Devices MCP
# Run this to set up the full development environment with all executables

param(
    [switch]$Minimal,
    [switch]$Dev,
    [switch]$WatchfilesOnly,
    [switch]$Help
)

if ($Help) {
    Write-Host "Devices MCP Installation Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\install.ps1                    # Interactive menu"
    Write-Host "  .\install.ps1 -Dev              # Full development setup (recommended)"
    Write-Host "  .\install.ps1 -Minimal         # Basic installation only"
    Write-Host "  .\install.ps1 -WatchfilesOnly  # Just watchfiles crashproofing"
    Write-Host ""
    Write-Host "INSTALLATION OPTIONS:" -ForegroundColor Yellow
    Write-Host "  Minimal:     pip install -e ."
    Write-Host "               - devices-mcp.exe, tapo-llms.exe"
    Write-Host ""
    Write-Host "  Dev:         pip install -e .[dev]"
    Write-Host "               - Everything above PLUS:"
    Write-Host "               - watchfiles.exe (crashproofing)"
    Write-Host "               - pytest.exe, ruff.exe, mypy.exe"
    Write-Host "               - sphinx-build.exe, jupyter.exe"
    Write-Host "               - All development and testing tools"
    Write-Host ""
    Write-Host "  Watchfiles:  pip install -r requirements-watchfiles.txt"
    Write-Host "               - Just watchfiles.exe and dependencies"
    Write-Host ""
    exit 0
}

Write-Host "🔧 Devices MCP Installation" -ForegroundColor Magenta
Write-Host "=================================" -ForegroundColor Magenta

# Check if we're in a virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "✅ Virtual environment detected: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "⚠️  No virtual environment detected!" -ForegroundColor Yellow
    Write-Host "   Recommended: python -m venv venv && .\venv\Scripts\activate" -ForegroundColor Yellow
    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        exit 1
    }
}

# Determine installation type
$installType = "interactive"
if ($Dev) { $installType = "dev" }
if ($Minimal) { $installType = "minimal" }
if ($WatchfilesOnly) { $installType = "watchfiles" }

if ($installType -eq "interactive") {
    Write-Host ""
    Write-Host "Choose installation type:" -ForegroundColor Cyan
    Write-Host "1. Full Development (recommended) - pip install -e .[dev]" -ForegroundColor White
    Write-Host "   Includes: watchfiles.exe, pytest, ruff, mypy, sphinx, jupyter, etc." -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Minimal - pip install -e ." -ForegroundColor White
    Write-Host "   Includes: devices-mcp.exe, tapo-llms.exe only" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Watchfiles Only - pip install -r requirements-watchfiles.txt" -ForegroundColor White
    Write-Host "   Includes: watchfiles.exe for crashproofing" -ForegroundColor Gray
    Write-Host ""

    $choice = Read-Host "Enter choice (1-3)"
    switch ($choice) {
        "1" { $installType = "dev" }
        "2" { $installType = "minimal" }
        "3" { $installType = "watchfiles" }
        default {
            Write-Host "❌ Invalid choice" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "🚀 Starting installation: $installType" -ForegroundColor Green

switch ($installType) {
    "dev" {
        Write-Host "Installing full development environment..." -ForegroundColor Cyan
        Write-Host "This will install ALL dependencies including:" -ForegroundColor Yellow
        Write-Host "  - Core: fastmcp, tapo, opencv, etc." -ForegroundColor White
        Write-Host "  - Dev: watchfiles, pytest, ruff, mypy, sphinx" -ForegroundColor White
        Write-Host "  - Testing: pytest, coverage, hypothesis" -ForegroundColor White
        Write-Host "  - Docs: sphinx, jupyter" -ForegroundColor White
        Write-Host ""

        pip install -e .[dev]

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Full development installation complete!" -ForegroundColor Green
            Write-Host ""
            Write-Host "EXECUTABLES INSTALLED:" -ForegroundColor Cyan
            Write-Host "  Core: devices-mcp.exe, tapo-llms.exe" -ForegroundColor White
            Write-Host "  Dev: watchfiles.exe, pytest.exe, ruff.exe, mypy.exe" -ForegroundColor White
            Write-Host "  Docs: sphinx-build.exe, jupyter.exe" -ForegroundColor White
            Write-Host ""
            Write-Host "NEXT STEPS:" -ForegroundColor Yellow
            Write-Host "  1. Run tests: pytest" -ForegroundColor White
            Write-Host "  2. Check code: ruff check . --fix" -ForegroundColor White
            Write-Host "  3. Start dev: python watchfiles_runner.py" -ForegroundColor White
        }
    }

    "minimal" {
        Write-Host "Installing minimal dependencies..." -ForegroundColor Cyan
        pip install -e .

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Minimal installation complete!" -ForegroundColor Green
            Write-Host ""
            Write-Host "EXECUTABLES INSTALLED:" -ForegroundColor Cyan
            Write-Host "  devices-mcp.exe, tapo-llms.exe" -ForegroundColor White
            Write-Host ""
            Write-Host "For crashproofing, also run: .\install-watchfiles.ps1" -ForegroundColor Yellow
        }
    }

    "watchfiles" {
        Write-Host "Installing watchfiles crashproofing only..." -ForegroundColor Cyan
        pip install -r requirements-watchfiles.txt

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Watchfiles installation complete!" -ForegroundColor Green
            Write-Host ""
            Write-Host "EXECUTABLE INSTALLED:" -ForegroundColor Cyan
            Write-Host "  watchfiles.exe" -ForegroundColor White
            Write-Host ""
            Write-Host "Usage: python watchfiles_runner.py" -ForegroundColor Yellow
        }
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Installation failed!" -ForegroundColor Red
    Write-Host "Check the error messages above and try again." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 Installation complete! Happy coding!" -ForegroundColor Green
