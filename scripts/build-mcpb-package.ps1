#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build MCPB package for Devices MCP Server

.DESCRIPTION
    This script builds an MCPB (MCP Bundle) package for distribution.
    It validates the manifest, builds the package, and optionally signs it.

.PARAMETER NoSign
    Skip package signing (for development builds)

.PARAMETER OutputDir
    Custom output directory for the built package (default: dist)

.PARAMETER Help
    Show this help message

.EXAMPLE
    .\scripts\build-mcpb-package.ps1 -NoSign
    Build without signing for development

.EXAMPLE
    .\scripts\build-mcpb-package.ps1 -OutputDir "C:\builds"
    Build with custom output directory
#>

param(
    [switch]$NoSign,
    [string]$OutputDir = "dist",
    [switch]$Help
)

# Color output functions
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "ℹ️  $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }

# Show help
if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

Write-Host ""
Write-Host "📦 Devices MCP - MCPB Package Builder" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

# 1. Check prerequisites
Write-Info "Checking prerequisites..."

# Check MCPB CLI
try {
    $mcpbVersion = mcpb --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "MCPB CLI installed: $mcpbVersion"
    } else {
        throw "MCPB CLI not found"
    }
} catch {
    Write-Error "MCPB CLI not installed!"
    Write-Info "Install with: npm install -g @anthropic-ai/mcpb"
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python installed: $pythonVersion"
    } else {
        throw "Python not found"
    }
} catch {
    Write-Error "Python not installed or not in PATH!"
    exit 1
}

# Check FastMCP version
Write-Info "Checking FastMCP version..."
try {
    $fastmcpVersion = python -c "import fastmcp; print(fastmcp.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "FastMCP installed: v$fastmcpVersion"

        # Verify version is >= 2.12.0
        $versionParts = $fastmcpVersion.Split('.')
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]

        if ($major -lt 2 -or ($major -eq 2 -and $minor -lt 12)) {
            Write-Error "FastMCP version $fastmcpVersion is too old!"
            Write-Warning "MCPB requires FastMCP >= 2.12.0"
            Write-Info "Update with: pip install 'fastmcp>=2.12.0,<3.0.0'"
            exit 1
        }
    } else {
        Write-Warning "FastMCP not installed!"
        Write-Info "Install with: pip install 'fastmcp>=2.12.0,<3.0.0'"
        exit 1
    }
} catch {
    Write-Warning "Could not check FastMCP version"
}

Write-Host ""

# 2. Validate manifest
Write-Info "Validating mcpb/manifest.json..."
if (Test-Path "mcpb/manifest.json") {
    try {
        mcpb validate mcpb/manifest.json
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Manifest validation passed!"
        } else {
            throw "Validation failed"
        }
    } catch {
        Write-Error "Manifest validation failed!"
        Write-Info "Check mcpb/manifest.json for errors"
        exit 1
    }
} else {
    Write-Error "mcpb/manifest.json not found!"
    Write-Info "Create manifest.json in the mcpb/ directory"
    exit 1
}

Write-Host ""

# 3. Create output directory
Write-Info "Preparing output directory: $OutputDir"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Success "Created output directory: $OutputDir"
} else {
    Write-Info "Output directory exists: $OutputDir"

    # Clean old packages
    $oldPackages = Get-ChildItem $OutputDir -Filter "*.mcpb" -ErrorAction SilentlyContinue
    if ($oldPackages) {
        Write-Warning "Removing old packages from $OutputDir"
        Remove-Item "$OutputDir\*.mcpb" -Force
    }
}

Write-Host ""

# 4. Build MCPB package
Write-Info "Building MCPB package..."
try {
    $packageName = "devices-mcp.mcpb"
    $outputPath = Join-Path $OutputDir $packageName

    Write-Info "Running: mcpb pack . $outputPath"
    mcpb pack . $outputPath

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Package built successfully!"

        # Get package size
        if (Test-Path $outputPath) {
            $size = (Get-Item $outputPath).Length
            $sizeMB = [Math]::Round($size / 1MB, 2)
            Write-Success "Package size: $sizeMB MB"
            Write-Success "Package location: $outputPath"
        }
    } else {
        throw "Build failed"
    }
} catch {
    Write-Error "MCPB package build failed!"
    Write-Info "Check the error messages above for details"
    exit 1
}

Write-Host ""

# 5. Optional: Sign package
if (!$NoSign) {
    Write-Info "Package signing requested..."
    Write-Warning "Signing is not yet configured"
    Write-Info "For development, use -NoSign flag"
    Write-Info "For production, configure signing key and remove this warning"
} else {
    Write-Warning "Skipping package signing (development build)"
}

Write-Host ""

# 6. Verify package
Write-Info "Verifying package integrity..."
if (Test-Path $outputPath) {
    try {
        mcpb verify $outputPath
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Package verification passed!"
        } else {
            Write-Warning "Package verification had issues"
        }
    } catch {
        Write-Warning "Could not verify package (this is normal for unsigned packages)"
    }
}

Write-Host ""

# 7. Summary
Write-Host "========================================" -ForegroundColor Green
Write-Success "MCPB Package Build Complete!"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📦 Package: $packageName" -ForegroundColor Cyan
Write-Host "📁 Location: $outputPath" -ForegroundColor Cyan
Write-Host "📊 Size: $sizeMB MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT Steps:" -ForegroundColor Yellow
Write-Host "  1. Install with dev tools: pip install -e .[dev]" -ForegroundColor White
Write-Host "     (includes watchfiles.exe, pytest, ruff, mypy, etc.)" -ForegroundColor Gray
Write-Host "  2. Or install minimal: pip install -e ." -ForegroundColor White
Write-Host "     (then add watchfiles: pip install -r requirements-watchfiles.txt)" -ForegroundColor Gray
Write-Host "  3. Run tests: pytest" -ForegroundColor White
Write-Host "  4. Lint code: ruff check . --fix" -ForegroundColor White
Write-Host "  1. Test installation: Drag $packageName to Claude Desktop" -ForegroundColor White
Write-Host "  2. Configure settings when prompted" -ForegroundColor White
Write-Host "  3. Test all 26+ tools" -ForegroundColor White
Write-Host "  4. For production: Build with signing enabled" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "  - MCPB Guide: docs/mcpb-packaging/MCPB_BUILDING_GUIDE.md" -ForegroundColor White
Write-Host "  - Implementation Summary: docs/mcpb-packaging/MCPB_IMPLEMENTATION_SUMMARY.md" -ForegroundColor White
Write-Host ""
