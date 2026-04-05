# GitLab CE Local Setup — Free, Private Git Hosting

## Overview
This guide covers setting up **GitLab Community Edition (CE)** locally for free, using Docker on Windows (PowerShell-friendly). GitLab CE gives you private repositories, issues, and CI/CD on your own machine.

## 1. Requirements
- Windows 10/11 with **WSL2** and **Docker Desktop** installed
- At least:
  - 4–8 GB RAM available for Docker
  - 2+ CPU cores
  - 20–30 GB free disk space for repos and data

## 2. Create Folders for Persistent Data
If you want to use absolute Windows paths (outside this repo), run in PowerShell:

```powershell
if (-not (Test-Path "C:\gitlab")) { New-Item -ItemType Directory -Path "C:\gitlab" }
if (-not (Test-Path "C:\gitlab\config")) { New-Item -ItemType Directory -Path "C:\gitlab\config" }
if (-not (Test-Path "C:\gitlab\logs")) { New-Item -ItemType Directory -Path "C:\gitlab\logs" }
if (-not (Test-Path "C:\gitlab\data")) { New-Item -ItemType Directory -Path "C:\gitlab\data" }
```

Or use the repo-local `deploy\gitlab` folder from the compose file below. In both cases, these hold GitLab configuration, logs, and data so you do not lose everything when the container is recreated.

## 3. Start GitLab CE (Docker)
### Option A: Direct docker run (no compose)
Run in PowerShell (absolute paths example):

```powershell
docker run `
  --hostname localhost `
  --publish 8093:80 `
  --publish 2222:22 `
  --name gitlab-ce `
  --restart always `
  --volume C:\gitlab\config:/etc/gitlab `
  --volume C:\gitlab\logs:/var/log/gitlab `
  --volume C:\gitlab\data:/var/opt/gitlab `
  gitlab/gitlab-ce:latest
```

- Web UI: `http://localhost:8093`
- SSH (optional): `ssh git@localhost -p 2222`

### Initial Root Password
After the container is up (first start can take a few minutes):

```powershell
docker exec -it gitlab-ce `
  type C:\gitlab\config\initial_root_password 2>$null
```

If that file is missing, use:

```powershell
docker exec -it gitlab-ce `
  findstr Password: /etc/gitlab/initial_root_password
```

Login as:
- **Username**: `root`
- **Password**: (from the file/output above)

### Option B: Docker Compose (repo-local)
From the repository root (uses port 8093 on the host):

```powershell
docker compose -f .\deploy\gitlab\docker-compose.yml up -d
```

This uses `deploy\gitlab\config`, `deploy\gitlab\logs`, and `deploy\gitlab\data` for persisted data and maps the GitLab UI to `http://localhost:8093`.

To stop GitLab:

```powershell
docker compose -f .\deploy\gitlab\docker-compose.yml down
```

## 4. Pros, Cons, and Pricing
You can mirror GitHub repos into GitLab for private CI, and optionally mirror critical GitLab repos back to GitHub as an extra backup.

## 7. Backups via Helper Script
From the repository root, you can run:

```powershell
.\scripts\gitlab_backup.ps1
```

Backups are created under `deploy\gitlab\data\backups`. Copy these to another disk or cloud storage according to the 3–2–1 rule.

## 8. Integrating Existing Repos

### Pros
- **Price**: GitLab CE is free and open source.
- **Privacy**: All repos and metadata live on your machine.
- **Integrated CI/CD**: Pipelines, runners, and templates built in.
- **Fine-grained access control**: Groups, protected branches, and permissions.

### Cons / Limitations
- You are responsible for **backups**, **upgrades**, and **security**.
- Resource heavy compared to a bare Git server.
- If your server (PC/NAS) dies and you have no backups, GitLab (and repos) die with it.

## 5. Backup Strategy (3–2–1 Rule)
GitLab stores repositories and metadata in `/var/opt/gitlab`. Use GitLab's backup task plus an external location:

```powershell
docker exec -it gitlab-ce gitlab-rake gitlab:backup:create
```

This creates backups under `/var/opt/gitlab/backups` (mapped into `C:\gitlab\data\backups`). Then:
- Copy the backup file to another disk (external drive or NAS).
- Optionally sync to cloud storage.

3–2–1 rule:
- **3 copies** of your data
- **2 different media** (e.g., internal disk + external drive)
- **1 off-site** copy (cloud or another physical location)

## 6. GitLab vs GitHub (Suggested Usage)
- **GitHub**:
  - Use for **public** repos, open source, and external collaborators.
  - Great for discoverability and community.
- **GitLab CE (local)**:
  - Use for **private** infrastructure repos and home-lab projects.
  - Full control over CI/CD, access, and data locality.

You can mirror GitHub repos into GitLab for private CI, and optionally mirror critical GitLab repos back to GitHub as an extra backup.

## 7. Integrating Existing Repos
Example: migrate `devices-mcp` into GitLab:

1. In GitLab UI, create a **new project** (e.g., group `home-mcp`, project `devices-mcp`).
2. In your local repo (PowerShell):
   ```powershell
   Set-Location -Path "D:\Dev\repos\devices-mcp"
   git remote add gitlab http://localhost:8080/home-mcp/devices-mcp.git
   git push gitlab main --follow-tags
   ```
3. Repeat for other repos (`nest-protect-mcp`, `ring-mcp`, `mcp-central-docs`, etc.).

## 9. Next Steps / Tips
- Schedule backups via Task Scheduler to run the `gitlab:backup:create` command regularly.
- Keep GitLab CE updated by pulling newer `gitlab/gitlab-ce` images occasionally.
