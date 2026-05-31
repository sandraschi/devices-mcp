"""
Home Assistant Management Portmanteau Tool

Consolidates Home Assistant integration operations into a single tool with action-based interface.
Used primarily for Nest Protect integration via HA bridge.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

HA_ACTIONS = {
    "status": "Get Home Assistant connection status",
    "entities": "List Home Assistant entities",
    "nest_protect": "Get Nest Protect devices via Home Assistant",
    "call_service": "Call a Home Assistant service",
    "get_state": "Get state of a specific entity",
}


def register_home_assistant_management_tool(mcp: FastMCP) -> None:
    """Register the Home Assistant management portmanteau tool."""

    @mcp.tool()
    async def home_assistant_management(
        action: Literal["status", "entities", "nest_protect", "call_service", "get_state"],
        entity_id: str | None = None,
        domain: str | None = None,
        service: str | None = None,
        service_data: dict | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive Home Assistant integration management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Consolidates Home Assistant operations into a single interface.
        Home Assistant serves as a bridge for devices like Nest Protect that
        require Google Cloud OAuth setup.

        Args:
            action (Literal, required): The operation to perform. Must be one of:
                - "status": Get HA connection status (no params required)
                - "entities": List HA entities (optional: domain to filter)
                - "nest_protect": Get Nest Protect devices via HA (no params required)
                - "call_service": Call HA service (requires: domain, service)
                - "get_state": Get entity state (requires: entity_id)

            entity_id (str | None): Home Assistant entity ID. Required for: get_state.
                Example: "sensor.nest_protect_smoke_status"

            domain (str | None): Entity domain for filtering or service calls.
                Examples: "sensor", "binary_sensor", "switch", "light"
                Required for: call_service. Optional for: entities.

            service (str | None): Service to call. Required for: call_service.
                Example: "turn_on", "turn_off"

            service_data (dict | None): Additional data for service call.
                Optional for: call_service. Example: {"brightness": 255}

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Whether operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False

        Examples:
            # Get HA status
            result = await home_assistant_management(action="status")

            # List all entities
            result = await home_assistant_management(action="entities")

            # List sensor entities only
            result = await home_assistant_management(action="entities", domain="sensor")

            # Get Nest Protect devices
            result = await home_assistant_management(action="nest_protect")

            # Get specific entity state
            result = await home_assistant_management(action="get_state", entity_id="sensor.nest_smoke")

            # Call a service
            result = await home_assistant_management(
                action="call_service",
                domain="light",
                service="turn_on",
                service_data={"entity_id": "light.living_room", "brightness": 128}
            )
        """
        try:
            if action not in HA_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(HA_ACTIONS.keys())}",
                    "available_actions": HA_ACTIONS,
                }

            logger.info(f"Executing Home Assistant management action: {action}")

            # Get HA configuration
            import httpx

            from devices_mcp.config import get_config

            config = get_config() or {}

            # Get HA settings from config
            ha_config = config.get("security", {}).get("integrations", {}).get("homeassistant", {})
            ha_url = ha_config.get("url", "http://localhost:8123")
            ha_token = ha_config.get("access_token")

            if not ha_token:
                return {
                    "success": False,
                    "action": action,
                    "error": "Home Assistant access token not configured. "
                    "Add security.integrations.homeassistant.access_token to config.yaml",
                }

            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                if action == "status":
                    try:
                        response = await client.get(f"{ha_url}/api/", headers=headers)
                        if response.status_code == 200:
                            return {
                                "success": True,
                                "action": action,
                                "data": {
                                    "connected": True,
                                    "url": ha_url,
                                    "api_response": response.json(),
                                },
                            }
                        return {
                            "success": False,
                            "action": action,
                            "error": f"HA returned status {response.status_code}",
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "action": action,
                            "error": f"Cannot connect to Home Assistant: {e}",
                            "data": {"url": ha_url},
                        }

                if action == "entities":
                    try:
                        response = await client.get(f"{ha_url}/api/states", headers=headers)
                        if response.status_code == 200:
                            entities = response.json()
                            # Filter by domain if provided
                            if domain:
                                entities = [e for e in entities if e.get("entity_id", "").startswith(f"{domain}.")]
                            return {
                                "success": True,
                                "action": action,
                                "data": {
                                    "entities": [
                                        {
                                            "entity_id": e.get("entity_id"),
                                            "state": e.get("state"),
                                            "friendly_name": e.get("attributes", {}).get("friendly_name"),
                                        }
                                        for e in entities[:50]  # Limit to 50
                                    ],
                                    "count": len(entities),
                                    "domain_filter": domain,
                                },
                            }
                        return {
                            "success": False,
                            "action": action,
                            "error": f"Failed to get entities: {response.status_code}",
                        }
                    except Exception as e:
                        return {"success": False, "action": action, "error": str(e)}

                if action == "nest_protect":
                    try:
                        response = await client.get(f"{ha_url}/api/states", headers=headers)
                        if response.status_code == 200:
                            entities = response.json()
                            # Find Nest Protect entities
                            nest_entities = [
                                e
                                for e in entities
                                if "nest" in e.get("entity_id", "").lower()
                                or "protect" in e.get("entity_id", "").lower()
                                or "smoke" in e.get("entity_id", "").lower()
                                or "co_alarm" in e.get("entity_id", "").lower()
                            ]
                            if nest_entities:
                                return {
                                    "success": True,
                                    "action": action,
                                    "data": {
                                        "devices": [
                                            {
                                                "entity_id": e.get("entity_id"),
                                                "state": e.get("state"),
                                                "friendly_name": e.get("attributes", {}).get("friendly_name"),
                                                "attributes": e.get("attributes", {}),
                                            }
                                            for e in nest_entities
                                        ],
                                        "count": len(nest_entities),
                                    },
                                }
                            return {
                                "success": True,
                                "action": action,
                                "data": {
                                    "devices": [],
                                    "count": 0,
                                    "note": "No Nest Protect entities found. "
                                    "Ensure Nest integration is set up in Home Assistant.",
                                },
                            }
                        return {
                            "success": False,
                            "action": action,
                            "error": f"Failed to get entities: {response.status_code}",
                        }
                    except Exception as e:
                        return {"success": False, "action": action, "error": str(e)}

                if action == "get_state":
                    if not entity_id:
                        return {
                            "success": False,
                            "action": action,
                            "error": "entity_id is required for get_state action",
                        }
                    try:
                        response = await client.get(f"{ha_url}/api/states/{entity_id}", headers=headers)
                        if response.status_code == 200:
                            entity = response.json()
                            return {
                                "success": True,
                                "action": action,
                                "data": {
                                    "entity_id": entity.get("entity_id"),
                                    "state": entity.get("state"),
                                    "attributes": entity.get("attributes", {}),
                                    "last_changed": entity.get("last_changed"),
                                    "last_updated": entity.get("last_updated"),
                                },
                            }
                        return {
                            "success": False,
                            "action": action,
                            "error": f"Entity not found or error: {response.status_code}",
                        }
                    except Exception as e:
                        return {"success": False, "action": action, "error": str(e)}

                if action == "call_service":
                    if not domain or not service:
                        return {
                            "success": False,
                            "action": action,
                            "error": "domain and service are required for call_service action",
                        }
                    try:
                        response = await client.post(
                            f"{ha_url}/api/services/{domain}/{service}",
                            headers=headers,
                            json=service_data or {},
                        )
                        if response.status_code in [200, 201]:
                            return {
                                "success": True,
                                "action": action,
                                "data": {
                                    "domain": domain,
                                    "service": service,
                                    "result": response.json() if response.text else "Service called successfully",
                                },
                            }
                        return {
                            "success": False,
                            "action": action,
                            "error": f"Service call failed: {response.status_code}",
                        }
                    except Exception as e:
                        return {"success": False, "action": action, "error": str(e)}

            return {"success": False, "error": f"Action '{action}' not implemented"}

        except Exception as e:
            logger.exception(f"Error in Home Assistant management action '{action}'")
            return {"success": False, "action": action, "error": str(e)}
