# MyHomeControl — Dockerization Guide (PowerShell-safe)

## Overview
Containerized deployment for the expanded home surveillance/control stack formerly focused on Tapo cameras. This repo now ships an app image and a compose file named after the stack: MyHomeControl.

## Why Dockerize
- Reproducible deploys across environments
- Simple integration with Prometheus/Grafana
- Single-command bring-up for app and monitoring

## App (MyHomeControl) — Build & Run

```powershell
# From repo root
docker build -t myhomecontrol-app .

# Create network (shared with monitoring) once
docker network create myhomecontrol

# Run via compose
docker compose -f .\deploy\myhomecontrol\docker-compose.yml up -d
```

App will be available at: `http://localhost:7777`

## Configuration & Volumes
- `config.yaml` is bind-mounted read-only into the container
- Volumes persist logs, snapshots, recordings, cache

## Monitoring Integration
- The monitoring compose is updated to also join the `myhomecontrol` network
- Prometheus can scrape `http://myhomecontrol-app:7777/metrics` if desired
- Alternatively, the existing config continues to use `host.docker.internal`

## USB Webcam Caveat
- Linux: map `/dev/video0` in compose under `devices` to access a webcam
- Windows/macOS Docker Desktop: host webcam passthrough is limited; prefer network cameras (Tapo/Ring/Nest)

## Stop/Remove
```powershell
docker compose -f .\deploy\myhomecontrol\docker-compose.yml down
```
