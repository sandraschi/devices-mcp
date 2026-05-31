"""HTTP client for yahboom-mcp (ROS 2 Yahboom robot car gateway)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_YAHBOOM_MCP_URL = "http://127.0.0.1:10892"


def yahboom_mcp_url() -> str:
    return os.environ.get("YAHBOOM_MCP_URL", DEFAULT_YAHBOOM_MCP_URL).rstrip("/")


def mcp_call_succeeded(result: dict[str, Any]) -> bool:
    """True when a yahboom-mcp REST response indicates success."""
    if result.get("success") is True:
        return True
    if result.get("status") == "success":
        return True
    if result.get("status") == "online":
        return True
    return False


class YahboomMcpClient:
    """Proxy to yahboom-mcp REST API on port 10892 (dual/http mode)."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0):
        self.base_url = (base_url or yahboom_mcp_url()).rstrip("/")
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
            return {"success": False, "error": str(detail), "status_code": exc.response.status_code}
        except httpx.RequestError as exc:
            return {"success": False, "error": f"yahboom-mcp unreachable at {self.base_url}: {exc}"}
        except Exception as exc:
            logger.exception("Yahboom MCP request failed: %s %s", method, path)
            return {"success": False, "error": str(exc)}

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/health")

    async def telemetry(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/telemetry")

    async def reconnect(self) -> dict[str, Any]:
        return await self._request("POST", "/api/v1/reconnect")

    async def move(self, linear: float = 0.0, angular: float = 0.0, linear_y: float = 0.0) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/control/move",
            params={"linear": linear, "angular": angular, "linear_y": linear_y},
        )

    async def stop_all(self) -> dict[str, Any]:
        return await self._request("POST", "/api/v1/stop_all")

    async def missions_stop(self) -> dict[str, Any]:
        return await self._request("POST", "/api/v1/missions/stop")

    async def lightstrip(
        self,
        *,
        operation: str = "set",
        r: int = 0,
        g: int = 0,
        b: int = 0,
        pattern: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"operation": operation, "r": r, "g": g, "b": b}
        if pattern:
            body["pattern"] = pattern
        return await self._request("POST", "/api/v1/control/lightstrip", json_body=body)

    def connection_summary(self, health: dict[str, Any]) -> dict[str, Any]:
        """Normalize health payload for the devices-mcp dashboard."""
        robot_conn = health.get("robot_connection") or {}
        mcp_online = health.get("status") == "online"
        ros_connected = robot_conn.get("ros") == "connected"
        return {
            "mcp_reachable": mcp_call_succeeded(health) or bool(health.get("system")),
            "mcp_online": mcp_online,
            "ros_connected": ros_connected,
            "cmd_vel_ready": bool(robot_conn.get("cmd_vel_ready")),
            "robot_ip": robot_conn.get("ip"),
            "video": robot_conn.get("video"),
            "ssh": robot_conn.get("ssh"),
            "hint": robot_conn.get("hint"),
            "driver_stack": robot_conn.get("driver_stack"),
        }

    def telemetry_is_live(self, telemetry: dict[str, Any]) -> bool:
        return telemetry.get("source") == "live" or telemetry.get("status") == "live"


_yahboom_client: YahboomMcpClient | None = None


def get_yahboom_client() -> YahboomMcpClient:
    global _yahboom_client
    if _yahboom_client is None:
        _yahboom_client = YahboomMcpClient()
    return _yahboom_client
