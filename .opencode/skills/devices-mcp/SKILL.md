---
name: devices-mcp
description: Home-IoT session starter for devices-mcp - device health recall and safe close-of-work
---

## Session Context (devices-mcp)

Beta home-IoT stack: Tapo/Ring/Nest/Hue/Netatmo/Shelly devices via 27 portmanteau
MCP tools, web dashboard on :10717, Tauri desktop installer.

**Before starting work, check what is online:**
1. Snapshot device health: sensor_health (status, connectivity, battery)
2. Backend alive? GET http://127.0.0.1:10717/api/health (one backend only - NSSM or Tauri, never both)

**At end of work, leave the home sane:**
- Confirm changed devices via camera_management / lighting_management status calls
- Never commit config.yaml or *.cache (LAN creds); update docs/ONBOARDING.md when setup changes
