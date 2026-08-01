#!/usr/bin/env pwsh
<#
.SYNOPSIS
  List or toggle GitHub Actions enabled flag per repository (personal account).

.DESCRIPTION
  SAFE BY DEFAULT: dry-run unless -Confirm is passed.
  Saves scripts/github-actions-state.json for -Enable rollback.

.PARAMETER Owner
  GitHub user or org (default: authenticated user)

.PARAMETER Confirm
  Required to change remote settings

.PARAMETER Enable
  Re-enable repos that were enabled=true in the state file at disable time

.EXAMPLE
  pwsh -File scripts/disable-github-actions.ps1
  pwsh -File scripts/disable-github-actions.ps1 -Confirm
  pwsh -File scripts/disable-github-actions.ps1 -Enable -Confirm
#>
param(
    [string]$Owner = "",
    [switch]$Confirm,
    [switch]$Enable
)

$ErrorActionPreference = "Stop"
$StatePath = Join-Path $PSScriptRoot "github-actions-state.json"

if (-not $Owner) {
    $Owner = gh api user -q .login
}

function Get-RepoList {
    $repos = gh api "users/$Owner/repos?per_page=100&affiliation=owner" --paginate -q '.[].name'
    return @($repos)
}

function Get-ActionsEnabled {
    param([string]$RepoName)
    try {
        $p = gh api "repos/$Owner/$RepoName/actions/permissions" 2>$null | ConvertFrom-Json
        return [bool]$p.enabled
    } catch {
        return $null
    }
}

function Set-ActionsEnabled {
    param([string]$RepoName, [bool]$Enabled)
    $json = (@{ enabled = $Enabled } | ConvertTo-Json -Compress)
    $tmp = New-TemporaryFile
    try {
        Set-Content -Path $tmp.FullName -Value $json -Encoding utf8NoBOM
        gh api --method PUT "repos/$Owner/$RepoName/actions/permissions" --input $tmp.FullName 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "exit $LASTEXITCODE"
        }
    } finally {
        Remove-Item $tmp.FullName -Force -ErrorAction SilentlyContinue
    }
}

if ($Enable) {
    if (-not (Test-Path $StatePath)) {
        Write-Error "Missing state file: $StatePath (run disable with -Confirm first)"
    }
    $state = Get-Content $StatePath -Raw | ConvertFrom-Json
    $targets = @($state.repos | Where-Object { $_.previously_enabled -eq $true })
    Write-Host "Re-enable Actions on $($targets.Count) repos" -ForegroundColor Cyan
    foreach ($r in $targets) {
        if (-not $Confirm) {
            Write-Host "  [dry-run] enable $($r.name)"
            continue
        }
        Write-Host "  enable $($r.name)" -NoNewline
        try {
            Set-ActionsEnabled -RepoName $r.name -Enabled $true
            Write-Host " OK" -ForegroundColor Green
        } catch {
            Write-Host " FAILED: $_" -ForegroundColor Red
        }
    }
    if (-not $Confirm) {
        Write-Host "Dry run. Add -Confirm to apply." -ForegroundColor Yellow
    }
    exit 0
}

$repos = Get-RepoList
Write-Host "Owner: $Owner - repos: $($repos.Count)" -ForegroundColor Cyan

$rows = @()
foreach ($name in $repos) {
    $enabled = Get-ActionsEnabled -RepoName $name
    $rows += [pscustomobject]@{ name = $name; actions_enabled = $enabled }
}

$toDisable = @($rows | Where-Object { $_.actions_enabled -eq $true })
Write-Host "Actions currently enabled: $($toDisable.Count)" -ForegroundColor Yellow

foreach ($r in $toDisable) {
    if ($Confirm) {
        Write-Host "  disable $($r.name)" -NoNewline
        try {
            Set-ActionsEnabled -RepoName $r.name -Enabled $false
            Write-Host " OK" -ForegroundColor Green
        } catch {
            Write-Host " FAILED" -ForegroundColor Red
            Write-Host "    $_" -ForegroundColor DarkRed
        }
    } else {
        Write-Host "  [dry-run] disable $($r.name)"
    }
}

$state = @{
    owner = $Owner
    disabled_at = (Get-Date).ToUniversalTime().ToString("o")
    repos = @($rows | ForEach-Object {
        @{ name = $_.name; previously_enabled = ($_.actions_enabled -eq $true) }
    })
}
if ($Confirm) {
    $state | ConvertTo-Json -Depth 5 | Set-Content $StatePath -Encoding utf8
    Write-Host "State saved: $StatePath" -ForegroundColor Cyan
}

if (-not $Confirm) {
    Write-Host ""
    Write-Host "Dry run only. To disable Actions on $($toDisable.Count) repos:" -ForegroundColor Yellow
    Write-Host "  pwsh -File scripts/disable-github-actions.ps1 -Confirm" -ForegroundColor White
}
