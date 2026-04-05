@echo off
TITLE Devices MCP Dashboard Launcher
COLOR 0D
SETLOCAL EnableDelayedExpansion

:: -------------------------------------------------------------------
:: Devices MCP Dashboard - SOTA Launcher (v1.20.0)
:: -------------------------------------------------------------------

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

set "PS1_PATH=%BASE_DIR%start.ps1"
if not exist "%PS1_PATH%" (
    echo [ERROR] start.ps1 not found: %PS1_PATH%
    pause
    exit /b 1
)

:: Check for uv
where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] uv not found in PATH.
    pause
    exit /b 1
)

echo [LAUNCH] USB camera helper 10715, API 10717, Vite 10716 ...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Dashboard failed to start or exited with error.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [DONE] Dashboard exited.
echo.
pause
