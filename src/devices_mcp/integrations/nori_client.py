"""HTTP client for norirobotics-mcp (Nori A3 gateway on port 11970)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)
DEFAULT_NORI_MCP_URL = "http://127.0.0.1:11970"


def nori_mcp_url() -> str:
    return os.environ.get("NORI_MCP_URL", DEFAULT_NORI_MCP_URL).rstrip("/")


def mcp_call_succeeded(result: dict[str, Any]) -> bool:
    """True when a norirobotics-mcp REST response indicates success."""
    if result.get("success") is True:
        return True
    if result.get("status") == "success":
        return True
    if result.get("status") == "online":
        return True
    return False


class NoriMcpClient:
    """Proxy to norirobotics-mcp's REST API for the Nori A3 (WebRTC/Supabase, mock-first)."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0):
        self.base_url = (base_url or nori_mcp_url()).rstrip("/")
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method == "GET":
                    response = await client.get(url, params=params)
                else:
                    response = await client.post(url, params=params, json=json_body)
                response.raise_for_status()
                if not response.content:
                    return {"success": True}
                data = response.json()
                return data if isinstance(data, dict) else {"success": True, "data": data}
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                payload = exc.response.json()
                detail = payload.get("detail", detail)
            except Exception:
                pass
            return {
                "success": False,
                "message": str(detail),
                "error": str(detail),
                "status_code": exc.response.status_code,
            }
        except httpx.RequestError as exc:
            return {
                "success": False,
                "message": f"norirobotics-mcp unreachable at {self.base_url}: {exc}",
                "error": f"norirobotics-mcp unreachable at {self.base_url}: {exc}",
            }
        except Exception as exc:
            logger.exception("Nori MCP request failed: %s %s", method, path)
            return {"success": False, "message": str(exc), "error": str(exc)}

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/api/health")

    async def hero(self) -> dict[str, Any]:
        return await self._request("GET", "/api/hero")

    async def session_status(self) -> dict[str, Any]:
        return await self._request("GET", "/api/session")

    async def session_connect(self, *, force_mock: bool = False) -> dict[str, Any]:
        return await self._request("POST", "/api/session/connect", params={"force_mock": force_mock})

    async def session_disconnect(self) -> dict[str, Any]:
        return await self._request("POST", "/api/session/disconnect")

    async def estop(self) -> dict[str, Any]:
        return await self._request("POST", "/api/control/estop")

    async def episode_start(self, task: str | None = None) -> dict[str, Any]:
        return await self._request("POST", "/api/recording/episode_start", json_body={"task": task})

    async def episode_stop(self) -> dict[str, Any]:
        return await self._request("POST", "/api/recording/episode_stop")

    def connection_summary(self, session: dict[str, Any]) -> dict[str, Any]:
        """Normalize session payload for the devices-mcp dashboard."""
        return {
            "mcp_reachable": mcp_call_succeeded(session),
            "connected": bool(session.get("connected")),
            "mock": session.get("mock"),
            "hint": None
            if session.get("connected")
            else "Call session_connect (defaults to nori_sdk's own mock session pre-hardware)",
        }

    def session_is_live(self, session: dict[str, Any]) -> bool:
        return bool(session.get("connected"))


_nori_client: NoriMcpClient | None = None


def get_nori_client() -> NoriMcpClient:
    global _nori_client
    if _nori_client is None:
        _nori_client = NoriMcpClient()
    return _nori_client
