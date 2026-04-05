param (
    [string]$ComposeFilePath = ".\deploy\gitlab\docker-compose.yml"
)

if (-not (Test-Path $ComposeFilePath)) {
    Write-Host "Compose file not found at $ComposeFilePath"
    exit 1
}

Write-Host "Running GitLab backup via docker compose..."

docker compose -f $ComposeFilePath exec gitlab-ce gitlab-rake gitlab:backup:create

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backup command failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

$backupDir = Join-Path -Path (Split-Path $ComposeFilePath) -ChildPath "data\backups"
Write-Host "Backup completed. Files should be in: $backupDir"
