import logging
from typing import Any

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field

from devices_mcp.fleet.manager import FleetManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


class HeartbeatRequest(BaseModel):
    """Request model for node heartbeat."""

    node_id: str = Field(..., description="Unique identifier for the node")
    status: str = Field("online", description="Current status of the node (online, offline, degraded)")
    drift_score: float = Field(0.0, description="Calculated Ontological Drift score")
    details: dict[str, Any] | None = Field(None, description="Additional telemetery/metadata")


@router.post("/heartbeat")
async def record_heartbeat(
    request: HeartbeatRequest, req: Request, x_forwarded_for: str | None = Header(None, alias="X-Forwarded-For")
) -> dict[str, Any]:
    """
    Record a heartbeat from a fleet node.
    Captures IP address and telemetry.
    """
    # Resolve IP address
    ip = x_forwarded_for or req.client.host if req.client else "unknown"

    manager = FleetManager()
    result = await manager.record_heartbeat(
        node_id=request.node_id,
        status=request.status,
        ip_address=ip,
        drift_score=request.drift_score,
        details=request.details,
    )

    if result.get("success"):
        return {"status": "success", "message": f"Heartbeat recorded for {request.node_id}"}
    else:
        return {"status": "error", "message": result.get("error")}


@router.get("/status")
async def get_fleet_status() -> list[dict[str, Any]]:
    """Get the current status of all nodes in the fleet."""
    manager = FleetManager()
    return await manager.get_fleet_status()


@router.get("/node/{node_id}")
async def get_node_status(node_id: str) -> dict[str, Any]:
    """Get detailed status for a specific node."""
    manager = FleetManager()
    node = await manager.get_node_status(node_id)
    if node:
        return node
    return {"error": "Node not found"}
