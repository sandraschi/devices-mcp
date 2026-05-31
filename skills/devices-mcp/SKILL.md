---
name: devices-mcp-home
description: >-
  Live inventory of the user's smart home on this devices-mcp installation —
  cameras, Hue lights, Tapo P115 plugs, Netatmo weather, Ring, Nest Protect,
  Shelly sensors, and robots. Use when the user asks what devices they have,
  what's online, or wants a status summary before controlling hardware.
---

# Devices MCP — Home Inventory Skill

You have access to a **live device snapshot** injected as the system message in Chat.
Treat it as ground truth for "what do I have?" questions unless the user says it is stale.

## Answer patterns

- **"What cameras do we have?"** — List every camera from the snapshot: name/id, type (Tapo ONVIF, USB webcam, Ring), and online/offline if shown.
- **"What's offline?"** — Report devices marked offline or integrations not connected.
- **"Summarize my home"** — Cameras, lighting, energy plugs, weather, security, sensors, robots in one short overview.

## Control vs inventory

This skill covers **inventory and status**. To turn lights on, move robots, or arm Ring, tell the user which dashboard page or MCP tool applies (`lighting_management`, `camera_management`, etc.) unless tool-calling is enabled in their client.

## If snapshot is missing

Say the webapp may still be starting and suggest opening **Chat** after restart, or checking **MCP Capabilities** and **Dashboard**.
