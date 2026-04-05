@echo off
TITLE Devices MCP Stack Launcher
COLOR 0B
SETLOCAL EnableDelayedExpansion

:: -------------------------------------------------------------------
:: Devices MCP - SOTA Launcher (v1.19.0)
:: -------------------------------------------------------------------

echo.
echo  ###############################################################
echo  #                                                             #
echo  #         🎥 DEVICES MCP - GLOBAL ORCHESTRATION 🎥            #
echo  #                                                             #
echo  ###############################################################
echo.

:: Get directory of this script
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH. Please install Python 3.8+.
    pause
    exit /b 1
)

:: Launch the PowerShell orchestration script
echo [LAUNCH] Starting PowerShell Orchestration...
echo [INFO] Ports: USB Cam helper (10715), Vite (10716), API (10717)
echo.

powershell -ExecutionPolicy Bypass -File ".\start.ps1"

echo.
echo [DONE] Orchestration sequence triggered.
echo.
pause
