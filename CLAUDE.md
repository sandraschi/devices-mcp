# devices-mcp -- Claude Code Guide

## Overview
FastMCP 3.4+ server for universal IoT and surveillance dashboard: cameras (Tapo, Ring, USB), Nest Protect, Hue lights, Netatmo weather, and more.

## Entry Points
- `uv run python -m devices_mcp.server_v2` -- MCP stdio server
- `web-sota\start.ps1` -- Full webapp (FastAPI :10717 + Vite :10716)

## Standards
- FastMCP 3.4+ portmanteau tool pattern -- tools use `operation` enum param
- Responses: structured dicts with `success`, `message`, domain-specific fields
- Dual transport: stdio (Claude Desktop) + HTTP
- See mcp-central-docs for fleet-wide coding standards

## Ports
- Backend: 10717
- Frontend: 10716
- USB camera helper: 10715
