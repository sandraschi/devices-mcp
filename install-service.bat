@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as Administrator
    pause
    exit /b 1
)

set NSSM="C:\Program Files\Jellyfin\Server\nssm.exe"
set DIR=%~dp0

%NSSM% stop devices-mcp 2>nul
%NSSM% remove devices-mcp confirm 2>nul

%NSSM% install devices-mcp "%DIR%run-devices-backend.bat"
%NSSM% set devices-mcp AppDirectory "%DIR%web-sota"
%NSSM% set devices-mcp AppStdout "%DIR%logs\service-stdout.log"
%NSSM% set devices-mcp AppStderr "%DIR%logs\service-stderr.log"
%NSSM% set devices-mcp Start SERVICE_AUTO_START
%NSSM% set devices-mcp AppRotateFiles 1
%NSSM% set devices-mcp AppRotateSeconds 86400
%NSSM% set devices-mcp AppRotateBytes 10485760

%NSSM% start devices-mcp
echo devices-mcp service installed and started
