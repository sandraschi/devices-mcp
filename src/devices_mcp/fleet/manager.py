import json
import logging
from datetime import UTC, datetime
from typing import Any

from devices_mcp.db.timeseries import TimeSeriesDB

logger = logging.getLogger(__name__)


class FleetManager:
    """Manages node registration, heartbeats, and status tracking for the fleet."""

    def __init__(self, db: TimeSeriesDB | None = None):
        """Initialize the Fleet Manager."""
        self.db = db or TimeSeriesDB()

    async def record_heartbeat(
        self,
        node_id: str,
        status: str = "online",
        ip_address: str | None = None,
        drift_score: float = 0.0,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a heartbeat from a node."""
        timestamp = int(datetime.now(UTC).timestamp())
        details_json = json.dumps(details) if details else None

        try:
            import sqlite3

            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO fleet_status
                    (node_id, last_heartbeat, status, ip_address, drift_score, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (node_id, timestamp, status, ip_address, drift_score, details_json),
                )
                conn.commit()

            logger.info(f"Recorded heartbeat for node {node_id}: {status}")
            return {"success": True, "node_id": node_id, "status": status, "timestamp": timestamp}
        except Exception as e:
            logger.error(f"Failed to record heartbeat for {node_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_fleet_status(self) -> list[dict[str, Any]]:
        """Get the current status of all known nodes."""
        try:
            import sqlite3

            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM fleet_status ORDER BY last_heartbeat DESC")
                rows = cursor.fetchall()

            nodes = []
            for row in rows:
                node = dict(row)
                if node["details"]:
                    try:
                        node["details"] = json.loads(node["details"])
                    except json.JSONDecodeError:
                        pass
                nodes.append(node)

            return nodes
        except Exception as e:
            logger.error(f"Failed to fetch fleet status: {e}")
            return []

    async def get_node_status(self, node_id: str) -> dict[str, Any] | None:
        """Get the status of a specific node."""
        try:
            import sqlite3

            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM fleet_status WHERE node_id = ?", (node_id,))
                row = cursor.fetchone()

            if row:
                node = dict(row)
                if node["details"]:
                    try:
                        node["details"] = json.loads(node["details"])
                    except json.JSONDecodeError:
                        pass
                return node
            return None
        except Exception as e:
            logger.error(f"Failed to fetch node status for {node_id}: {e}")
            return None
