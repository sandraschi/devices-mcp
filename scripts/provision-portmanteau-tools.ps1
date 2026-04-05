# Devices MCP Portmanteau Tools Provision Script
# Verifies and sets up all portmanteau tools for the devices-mcp server

param(
    [switch]$Force,
    [switch]$Verbose,
    [switch]$SkipDependencies
)

# Configuration
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot  # scripts -> project root
$SRC_DIR = Join-Path $PROJECT_ROOT "src"
$PORTMANTEAU_DIR = Join-Path $SRC_DIR "devices_mcp/tools/portmanteau"

# Tool categories and their files
$PORTMANTEAU_TOOLS = @{
    # Core tools (always required)
    "tapo_control" = "tapo_control.py"
    "camera_management" = "camera_management.py"
    "ptz_management" = "ptz_management.py"
    "media_management" = "media_management.py"
    "energy_management" = "energy_management.py"
    "lighting_management" = "lighting_management.py"
    "kitchen_management" = "kitchen_management.py"
    "security_management" = "security_management.py"
    "system_management" = "system_management.py"
    "weather_management" = "weather_management.py"
    "configuration_management" = "configuration_management.py"

    # Extended tools (v1.5.0+)
    "ring_management" = "ring_management.py"
    "audio_management" = "audio_management.py"
    "motion_management" = "motion_management.py"
    "home_assistant_management" = "home_assistant_management.py"

    # Advanced tools (v1.6.0+)
    "robotics_management" = "robotics_management.py"
    "ai_analysis" = "ai_analysis.py"
    "automation_management" = "automation_management.py"
    "analytics_management" = "analytics_management.py"
    "grafana_management" = "grafana_management.py"

    # Latest additions
    "alerts_management" = "alerts_management.py"
    "appliance_monitor_management" = "appliance_monitor_management.py"
    "messages_management" = "messages_management.py"
    "medical_management" = "medical_management.py"
    "shelly_management" = "shelly_management.py"
    "thermal_management" = "thermal_management.py"
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    if ($Verbose) {
        Add-Content -Path "$PROJECT_ROOT\provision-tools.log" -Value $logMessage
    }
}

function Test-ToolFile {
    param([string]$ToolName, [string]$FileName)

    $filePath = Join-Path $PORTMANTEAU_DIR $FileName

    if (-not (Test-Path $filePath)) {
        Write-Log "MISSING: $ToolName tool file - $FileName" "ERROR"
        return $false
    }

    # Check if file contains registration function
    $content = Get-Content $filePath -Raw
    $registrationPattern = "def register_${ToolName}_tool"
    if ($content -notmatch $registrationPattern) {
        Write-Log "INVALID: $ToolName tool missing registration function" "ERROR"
        return $false
    }

    # Check if tool is imported in __init__.py
    $initFile = Join-Path $PORTMANTEAU_DIR "__init__.py"
    if (Test-Path $initFile) {
        $initContent = Get-Content $initFile -Raw
        $importPattern = "from \.${ToolName} import register_${ToolName}_tool"
        if ($initContent -notmatch $importPattern) {
            Write-Log "NOT REGISTERED: $ToolName tool not imported in __init__.py" "WARN"
        }
    }

    Write-Log "OK: $ToolName tool verified - $FileName" "INFO"
    return $true
}

function Test-PortmanteauRegistration {
    $initFile = Join-Path $PORTMANTEAU_DIR "__init__.py"

    if (-not (Test-Path $initFile)) {
        Write-Log "CRITICAL: Portmanteau __init__.py file missing" "ERROR"
        return $false
    }

    $content = Get-Content $initFile -Raw

    # Check if register_all_portmanteau_tools function exists
    if ($content -notmatch "def register_all_portmanteau_tools") {
        Write-Log "CRITICAL: register_all_portmanteau_tools function missing" "ERROR"
        return $false
    }

    # Check if all tools are imported
    $missingImports = @()
    foreach ($tool in $PORTMANTEAU_TOOLS.Keys) {
        $importPattern = "from \.${tool} import register_${tool}_tool"
        if ($content -notmatch $importPattern) {
            $missingImports += $tool
        }
    }

    if ($missingImports.Count -gt 0) {
        Write-Log "MISSING IMPORTS: $($missingImports -join ', ')" "ERROR"
        return $false
    }

    # Check if all tools are registered in the function
    $missingRegistrations = @()
    foreach ($tool in $PORTMANTEAU_TOOLS.Keys) {
        $registerPattern = "register_${tool}_tool\(mcp\)"
        if ($content -notmatch $registerPattern) {
            $missingRegistrations += $tool
        }
    }

    if ($missingRegistrations.Count -gt 0) {
        Write-Log "MISSING REGISTRATIONS: $($missingRegistrations -join ', ')" "ERROR"
        return $false
    }

    Write-Log "OK: All portmanteau tools properly registered" "INFO"
    return $true
}

function Test-ToolRegistration {
    $registerFile = Join-Path $SRC_DIR "devices_mcp/tools/register_tools.py"

    if (-not (Test-Path $registerFile)) {
        Write-Log "CRITICAL: Tool registration file missing" "ERROR"
        return $false
    }

    $content = Get-Content $registerFile -Raw

    # Check if portmanteau registration is called
    if ($content -notmatch "register_all_portmanteau_tools\(mcp\)") {
        Write-Log "CRITICAL: Portmanteau tools not registered in main registration" "ERROR"
        return $false
    }

    Write-Log "OK: Portmanteau tools registered in main tool system" "INFO"
    return $true
}

function Test-ServerIntegration {
    $serverFile = Join-Path $SRC_DIR "devices_mcp/core/server.py"

    if (-not (Test-Path $serverFile)) {
        Write-Log "CRITICAL: Server file missing" "ERROR"
        return $false
    }

    $content = Get-Content $serverFile -Raw

    # Check if tool registration is called
    if ($content -notmatch "register_all_tools\(self\.mcp") {
        Write-Log "CRITICAL: Tools not registered in server initialization" "ERROR"
        return $false
    }

    Write-Log "OK: Portmanteau tools integrated into server startup" "INFO"
    return $true
}

function Test-PythonSyntax {
    param([string]$FilePath)

    try {
        $null = python -m py_compile $FilePath 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $true
        } else {
            Write-Log "SYNTAX ERROR: $FilePath" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "SYNTAX CHECK FAILED: $FilePath - $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Repair-ToolImports {
    $initFile = Join-Path $PORTMANTEAU_DIR "__init__.py"

    if (-not (Test-Path $initFile)) {
        Write-Log "Cannot repair: __init__.py missing" "ERROR"
        return $false
    }

    $content = Get-Content $initFile -Raw

    # Add missing imports
    $importSection = ""
    foreach ($tool in $PORTMANTEAU_TOOLS.Keys) {
        $importPattern = "from \.${tool} import register_${tool}_tool"
        if ($content -notmatch $importPattern) {
            $importSection += "from .${tool} import register_${tool}_tool`n"
            Write-Log "Adding missing import: $tool" "INFO"
        }
    }

    if ($importSection) {
        # Find the import section and add missing imports
        $lines = Get-Content $initFile
        $importEndIndex = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match "^from \.") {
                $importEndIndex = $i
            } elseif ($importEndIndex -ge 0 -and $lines[$i].Trim() -eq "") {
                # Insert after the last import
                $lines = $lines[0..$importEndIndex] + $importSection.TrimEnd("`n").Split("`n") + $lines[($importEndIndex+1)..($lines.Count-1)]
                break
            }
        }

        $lines | Set-Content $initFile
        Write-Log "Repaired missing imports in __init__.py" "INFO"
    }

    # Add missing registrations in the function
    $registerSection = ""
    foreach ($tool in $PORTMANTEAU_TOOLS.Keys) {
        $registerPattern = "register_${tool}_tool\(mcp\)"
        if ($content -notmatch $registerPattern) {
            $registerSection += "    register_${tool}_tool(mcp)`n"
            Write-Log "Adding missing registration: $tool" "INFO"
        }
    }

    if ($registerSection) {
        # Find the registration function and add missing registrations
        $lines = Get-Content $initFile
        $inFunction = $false
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match "def register_all_portmanteau_tools") {
                $inFunction = $true
            } elseif ($inFunction -and $lines[$i] -match "^    logger\.info") {
                # Insert before the logger.info line
                $lines = $lines[0..($i-1)] + $registerSection.TrimEnd("`n").Split("`n") + $lines[$i..($lines.Count-1)]
                break
            }
        }

        $lines | Set-Content $initFile
        Write-Log "Repaired missing registrations in __init__.py" "INFO"
    }

    return $true
}

# Main execution
Write-Log "=== Devices MCP PORTMANTEAU TOOLS PROVISION ===" "INFO"
Write-Log "Project root: $PROJECT_ROOT" "INFO"
Write-Log "Portmanteau directory: $PORTMANTEAU_DIR" "INFO"
Write-Log "Force mode: $($Force.ToString().ToUpper())" "INFO"
Write-Log "Verbose logging: $($Verbose.ToString().ToUpper())" "INFO"
Write-Log "" "INFO"

$allGood = $true
$toolsChecked = 0
$toolsValid = 0

# Check Python availability
if (-not $SkipDependencies) {
    try {
        $pythonVersion = python --version 2>$null
        Write-Log "Python available: $pythonVersion" "INFO"
    } catch {
        Write-Log "Python not found - install Python 3.8+ to continue" "ERROR"
        exit 1
    }
}

# Verify portmanteau directory exists
if (-not (Test-Path $PORTMANTEAU_DIR)) {
    Write-Log "CRITICAL: Portmanteau tools directory missing: $PORTMANTEAU_DIR" "ERROR"
    exit 1
}

Write-Log "Checking $($PORTMANTEAU_TOOLS.Count) portmanteau tools..." "INFO"
Write-Log "" "INFO"

# Check each tool file
foreach ($tool in $PORTMANTEAU_TOOLS.GetEnumerator()) {
    $toolsChecked++
    if (Test-ToolFile -ToolName $tool.Key -FileName $tool.Value) {
        $toolsValid++

        # Test Python syntax
        $filePath = Join-Path $PORTMANTEAU_DIR $tool.Value
        if (-not (Test-PythonSyntax -FilePath $filePath)) {
            $allGood = $false
        }
    } else {
        $allGood = $false
    }
}

Write-Log "" "INFO"
Write-Log "Tool files checked: $toolsChecked, Valid: $toolsValid" "INFO"

# Test portmanteau registration system
Write-Log "" "INFO"
Write-Log "Testing portmanteau registration system..." "INFO"

$registrationOk = Test-PortmanteauRegistration
if (-not $registrationOk) {
    $allGood = $false
}

# Test main tool registration
$mainRegistrationOk = Test-ToolRegistration
if (-not $mainRegistrationOk) {
    $allGood = $false
}

# Test server integration
$serverIntegrationOk = Test-ServerIntegration
if (-not $serverIntegrationOk) {
    $allGood = $false
}

Write-Log "" "INFO"

# Attempt repairs if needed and force is enabled
if (-not $allGood -and $Force) {
    Write-Log "Force mode enabled - attempting repairs..." "WARN"

    if (Repair-ToolImports) {
        Write-Log "Repairs completed - re-running verification..." "INFO"
        Write-Log "" "INFO"

        # Re-run checks
        $allGood = $true
        $toolsValid = 0

        foreach ($tool in $PORTMANTEAU_TOOLS.GetEnumerator()) {
            if (Test-ToolFile -ToolName $tool.Key -FileName $tool.Value) {
                $toolsValid++
            } else {
                $allGood = $false
            }
        }

        $registrationOk = Test-PortmanteauRegistration
        $mainRegistrationOk = Test-ToolRegistration
        $serverIntegrationOk = Test-ServerIntegration

        $allGood = $allGood -and $registrationOk -and $mainRegistrationOk -and $serverIntegrationOk
    }
}

# Final status
Write-Log "" "INFO"
Write-Log "=== PROVISION RESULTS ===" "INFO"

if ($allGood) {
    Write-Log "✅ ALL PORTMANTEAU TOOLS PROPERLY PROVISIONED" "SUCCESS"
    Write-Log "Ready for deployment: $($PORTMANTEAU_TOOLS.Count) tools available" "INFO"
    exit 0
} else {
    Write-Log "❌ PROVISION ISSUES DETECTED" "ERROR"
    Write-Log "Issues found - check logs above for details" "ERROR"
    Write-Log "Run with -Force to attempt automatic repairs" "INFO"
    Write-Log "Run with -Verbose for detailed logging" "INFO"
    exit 1
}
