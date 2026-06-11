@echo off
REM Hard restart devices-mcp
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web-sota\stop.ps1"
if errorlevel 1 (
    echo stop failed
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web-sota\start.ps1"
pause

