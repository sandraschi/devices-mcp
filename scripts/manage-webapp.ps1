#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Webapp Process Manager for Devices MCP

.DESCRIPTION
    This script manages the Devices MCP webapp process, ensuring only one instance runs at a time.

.PARAMETER Action
    Action to perform: start, stop, restart, status

.PARAMETER Port
    Port to use for the webapp (default: 7777)

.EXAMPLE
    .\manage-webapp.ps1 -Action start
    .\manage-webapp.ps1 -Action stop
    .\manage-webapp.ps1 -Action restart
    .\manage-webapp.ps1 -Action status
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action,

    [int]$Port = 7777
)

$ErrorActionPreference = "Stop"
$ScriptName = "Devices MCP Webapp"
$ProcessName = "python"
$ModuleName = "devices_mcp.web.server"

function Get-WebappProcesses {
    return Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*$ModuleName*" -or $_.CommandLine -like "*devices_mcp*"
    }
}

function Stop-Webapp {
    Write-Host "🛑 Stopping $ScriptName..." -ForegroundColor Yellow

    $processes = Get-WebappProcesses
    if ($processes) {
        foreach ($process in $processes) {
            Write-Host "  Stopping process $($process.Id)..." -ForegroundColor Gray
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }

        # Wait a bit and check again
        Start-Sleep -Seconds 2
        $remaining = Get-WebappProcesses
        if ($remaining) {
            Write-Host "⚠️ Some processes still running, force killing..." -ForegroundColor Red
            $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
        }

        Write-Host "✅ $ScriptName stopped" -ForegroundColor Green
    } else {
        Write-Host "ℹ️ No $ScriptName processes found" -ForegroundColor Gray
    }
}

function Start-Webapp {
    Write-Host "🚀 Starting $ScriptName on port $Port..." -ForegroundColor Cyan

    # Check if already running
    $existing = Get-WebappProcesses
    if ($existing) {
        Write-Host "⚠️ $ScriptName is already running (PID: $($existing.Id))" -ForegroundColor Yellow
        return
    }

    # Check if port is in use
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "❌ Port $Port is already in use by process $($portInUse.OwningProcess)" -ForegroundColor Red
        return
    }

    # Start the webapp in background
    $venvPython = Join-Path $PSScriptRoot "..\venv\Scripts\python.exe"
    $startCommand = "$venvPython -m $ModuleName --host 0.0.0.0 --port $Port"

    Write-Host "  Command: $startCommand" -ForegroundColor Gray

    try {
        # Start as background process
        $process = Start-Process -FilePath $venvPython -ArgumentList "-m $ModuleName --host 0.0.0.0 --port $Port" -NoNewWindow -PassThru

        Start-Sleep -Seconds 3

        # Check if process is still running
        $process.Refresh()
        if (!$process.HasExited) {
            Write-Host "✅ $ScriptName started successfully (PID: $($process.Id))" -ForegroundColor Green
            Write-Host "🌐 Webapp available at: http://localhost:$Port" -ForegroundColor Cyan
        } else {
            Write-Host "❌ $ScriptName process exited prematurely" -ForegroundColor Red
            Write-Host "  Exit code: $($process.ExitCode)" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Error starting $ScriptName`: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Get-WebappStatus {
    Write-Host "📊 $ScriptName Status" -ForegroundColor Cyan
    Write-Host "=" * 40

    $processes = Get-WebappProcesses
    if ($processes) {
        Write-Host "✅ Status: RUNNING" -ForegroundColor Green
        foreach ($process in $processes) {
            Write-Host "  PID: $($process.Id)" -ForegroundColor White
            Write-Host "  Started: $($process.StartTime)" -ForegroundColor White
            Write-Host "  Memory: $([math]::Round($process.WorkingSet / 1MB, 1)) MB" -ForegroundColor White
        }

        # Check if webapp is responding
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$Port/api/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "  Health: HEALTHY" -ForegroundColor Green
            } else {
                Write-Host "  Health: RESPONDING (status $($response.StatusCode))" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Health: NOT RESPONDING" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ Status: STOPPED" -ForegroundColor Red
    }
}

function Restart-Webapp {
    Write-Host "🔄 Restarting $ScriptName..." -ForegroundColor Cyan
    Stop-Webapp
    Start-Sleep -Seconds 2
    Start-Webapp
}

# Main execution
switch ($Action) {
    "start" { Start-Webapp }
    "stop" { Stop-Webapp }
    "restart" { Restart-Webapp }
    "status" { Get-WebappStatus }
    default {
        Write-Host "❌ Invalid action: $Action" -ForegroundColor Red
        Write-Host "Valid actions: start, stop, restart, status" -ForegroundColor Yellow
        exit 1
    }
}
