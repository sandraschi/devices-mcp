@echo off
REM Stop devices-mcp fleet ports
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web-sota\stop.ps1"
if errorlevel 1 pause

