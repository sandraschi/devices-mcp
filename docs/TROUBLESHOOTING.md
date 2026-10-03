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

## Ollama: "llama-server binary not found" (generate 500s, reinstalls don't help)

**Symptoms:** `GET /api/tags` and `POST /api/show` work, but every
`POST /api/generate` returns 500 with
`error starting llama-server: llama-server binary not found (checked: ...)`.
Chat in the dashboard fails on the Ollama provider while LM Studio works.
Reinstalling Ollama changes nothing.

**Root cause (seen 2026-10-03):** the `ollama-serve` NSSM service plus the
Ollama tray app run 24/7 **from inside the install directory**
(`%LOCALAPPDATA%\Programs\Ollama`). Every reinstall tries to replace files
that are locked by those running processes, so it aborts partway — leaving
`lib\` (the whole runner directory) empty and `is-*.tmp` leftovers behind.
Repeating the same locked install cannot fix it. (Also note: current Ollama
ships `llama-server.exe` as a ~22 KB stub that loads
`libllama-server-impl.dll` + CUDA/cuDNN backends — a small exe is normal,
a missing `lib\` is not.)

**Fix — stop everything first, then reinstall:**

```powershell
sc.exe stop ollama-serve
Get-Process "ollama app" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
# verify nothing holds the dir, then run the installer (models on OLLAMA_MODELS are untouched)
Start-Process "C:\Users\sandr\Downloads\OllamaSetup(3).exe" -ArgumentList "/SILENT" -Wait
# verify runners landed:
Get-ChildItem "$env:LOCALAPPDATA\Programs\Ollama\lib\ollama\llama-server.exe"
sc.exe start ollama-serve
```

**Verify:** generate directly, then through the backend:

```powershell
curl.exe -s --max-time 120 -X POST http://127.0.0.1:11434/api/generate `
  -H "Content-Type: application/json" `
  -d '{"model":"llama3.2:3b","prompt":"hi","stream":false}'
curl.exe -s --max-time 120 -X POST http://127.0.0.1:10717/api/llm/chat `
  -H "Content-Type: application/json" `
  -d '{"messages":[{"role":"user","content":"hi"}],"provider":"ollama","model":"llama3.2:3b","stream":false}'
```

Both must return success. Models live under `OLLAMA_MODELS` (`N:\AI\ollama\models`
here) and are never touched by a reinstall — no re-download needed.

## Get help

[GitHub Issues](https://github.com/sandraschi/devices-mcp/issues) — include build version (Releases tag), config redacted, and whether NSSM is used.
