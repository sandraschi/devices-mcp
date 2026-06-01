# Troubleshooting

## Splash: "Dashboard did not start in time" but browser works

**Cause:** Splash page runs on Tauri `asset.localhost` and calls `fetch('/api/health')`. Older builds blocked CORS; or backend was already up via **NSSM** while desktop tried to spawn a second server.

**Fix (v1.21.5+):** Update installer; splash allows Tauri origins and reuses port 10717 if busy.

**Workaround now:** Open http://127.0.0.1:10717/app/ in Edge/Chrome, or click **Open dashboard anyway** (newer splash).

## White screen in Tauri window

1. Confirm backend: http://127.0.0.1:10717/api/health
2. Only one listener on 10717 (stop duplicate NSSM/sidecar).
3. Allow **Devices MCP** through Windows Firewall (private LAN).
4. Check `%USERPROFILE%\.config\devices-mcp\config.yaml` exists.

## Logs page: `D:\Dev\repos\devices-mcp\tapo_mcp.log (not found)`

Relative log paths resolve to the **dev repo** when config says `tapo_mcp.log`.

**Fix:**

```yaml
logging:
  file: "C:/Users/YOU/.local/share/devices-mcp/devices-mcp.log"
```

Create the folder; restart backend.

## Port already in use

```powershell
netstat -ano | findstr :10717
```

Stop the other process (NSSM service, stray `devices-mcp-backend.exe`, or dev `uvicorn`).

## Desktop vs NSSM

| Setup | Recommendation |
|-------|----------------|
| NSSM runs backend 24/7 | Use browser dashboard; optional Tauri as viewer only |
| No service | Use Tauri installer only |
| Both started | Keep one backend; v1.21.5+ reuses existing |

## Camera sidecar

USB cams need OpenCV; Tapo needs credentials in config. Camera helper listens on **10715** when spawned.

## Slow cold start

Full sidecars are ~123 MB each; first launch unpacks PyInstaller temp — **1–3 minutes** is normal on HDD/slow AV scan.

## Get help

[GitHub Issues](https://github.com/sandraschi/devices-mcp/issues) — include build version (Releases tag), config redacted, and whether NSSM is used.
