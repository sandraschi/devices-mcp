"""
Automation Management Portmanteau Tool
Consolidates all automation-related operations into a single tool with action-based interface.
Currently supports smart scheduling, conditional rules, and predictive maintenance.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

logger = logging.getLogger(__name__)
AUTOMATION_ACTIONS = {
    "create_rule": "Create new automation rule with conditions and actions",
    "list_rules": "List all automation rules",
    "execute_rule": "Execute a specific automation rule",
    "delete_rule": "Delete an automation rule",
    "create_schedule": "Create scheduled automation task",
    "list_schedules": "List all automation schedules",
    "execute_schedule": "Execute a scheduled automation task",
    "delete_schedule": "Delete an automation schedule",
    "get_history": "Get automation execution history",
    "analyze_patterns": "Analyze patterns for smart automation",
}


def register_automation_management_tool(mcp: FastMCP) -> None:
    """Register the automation management portmanteau tool."""

    @mcp.tool()
    async def automation_management(
        action: Literal[
            "create_rule",
            "list_rules",
            "execute_rule",
            "delete_rule",
            "create_schedule",
            "list_schedules",
            "execute_schedule",
            "delete_schedule",
            "get_history",
            "analyze_patterns",
        ],
        rule_id: str | None = None,
        schedule_id: str | None = None,
        rule_name: str | None = None,
        conditions: dict[str, Any] | None = None,
        actions: list[dict[str, Any]] | None = None,
        cron_expression: str | None = None,
        schedule_name: str | None = None,
        priority: int = 1,
        enabled: bool = True,
        time_range: str = "24h",
    ) -> dict[str, Any]:
        """
        Comprehensive automation management portmanteau tool for smart scheduling and rules.
        PORTMANTEAU PATTERN RATIONALE:
        Consolidates automation operations into a single interface to reduce tool explosion
        while maintaining full functionality. Supports conditional rules, scheduled tasks,
        pattern analysis, and predictive automation.
        Args:
            action (Literal, required): The automation operation to perform. Must be one of:
                - "create_rule": Create automation rule (requires: rule_name, conditions, actions)
                - "list_rules": List all automation rules
                - "execute_rule": Execute rule (requires: rule_id)
                - "delete_rule": Delete rule (requires: rule_id)
                - "create_schedule": Create scheduled task (requires: schedule_name, cron_expression, actions)
                - "list_schedules": List all schedules
                - "execute_schedule": Execute schedule (requires: schedule_id)
                - "delete_schedule": Delete schedule (requires: schedule_id)
                - "get_history": Get execution history (optional: time_range)
                - "analyze_patterns": Analyze patterns for smart automation
            rule_id (str | None): Rule ID for rule operations
            schedule_id (str | None): Schedule ID for schedule operations
            rule_name (str | None): Name for new rule
            conditions (dict | None): Rule conditions (e.g., {"time": "sunset", "motion": true})
            actions (list[dict] | None): Actions to execute (e.g., [{"type": "light", "action": "on"}])
            cron_expression (str | None): Cron expression for schedules (e.g., "0 9 * * *")
            schedule_name (str | None): Name for new schedule
            priority (int): Rule priority (1-10, default: 1)
            enabled (bool): Whether rule/schedule is enabled (default: True)
            time_range (str): Time range for history (default: "24h")
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (rules, schedules, history, etc.)
                - error (str | None): Error message if success is False
        Examples:
            # Create automation rule
            result = await automation_management(
                action="create_rule",
                rule_name="Evening Lights",
                conditions={"time": "sunset", "motion": True},
                actions=[{"type": "light", "group": "living_room", "action": "on"}]
            )
            # List all rules
            result = await automation_management(action="list_rules")
            # Execute specific rule
            result = await automation_management(action="execute_rule", rule_id="rule_001")
            # Create scheduled task
            result = await automation_management(
                action="create_schedule",
                schedule_name="Morning Routine",
                cron_expression="0 7 * * *",
                actions=[{"type": "light", "group": "bedroom", "action": "on"}]
            )
            # Get automation history
            result = await automation_management(action="get_history", time_range="7d")
            # Analyze patterns
            result = await automation_management(action="analyze_patterns")
        """
        try:
            if action not in AUTOMATION_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(AUTOMATION_ACTIONS.keys())}",
                }
            logger.info(f"Executing automation management action: {action}")
            # Import the smart automation tool
            from ...tools.automation.smart_automation import SmartAutomationTool

            automation_tool = SmartAutomationTool()
            # Map actions to tool parameters
            if action == "create_rule":
                if not rule_name or not conditions or not actions:
                    return {
                        "success": False,
                        "message": "rule_name, conditions, and actions are required for create_rule",
                        "error": "rule_name, conditions, and actions are required for create_rule",
                    }
                result = await automation_tool.execute(
                    action="create_rule",
                    name=rule_name,
                    conditions=conditions,
                    actions=actions,
                    priority=priority,
                    enabled=enabled,
                )
            elif action == "list_rules":
                result = await automation_tool.execute(action="list_rules")
            elif action == "execute_rule":
                if not rule_id:
                    return {
                        "success": False,
                        "message": "rule_id is required for execute_rule",
                        "error": "rule_id is required for execute_rule",
                    }
                result = await automation_tool.execute(action="execute_rule", rule_id=rule_id)
            elif action == "delete_rule":
                if not rule_id:
                    return {
                        "success": False,
                        "message": "rule_id is required for delete_rule",
                        "error": "rule_id is required for delete_rule",
                    }
                result = await automation_tool.execute(action="delete_rule", rule_id=rule_id)
            elif action == "create_schedule":
                if not schedule_name or not cron_expression or not actions:
                    return {
                        "success": False,
                        "message": "schedule_name, cron_expression, and actions are required for create_schedule",
                        "error": "schedule_name, cron_expression, and actions are required for create_schedule",
                    }
                result = await automation_tool.execute(
                    action="create_schedule",
                    name=schedule_name,
                    cron_expression=cron_expression,
                    actions=actions,
                    enabled=enabled,
                )
            elif action == "list_schedules":
                result = await automation_tool.execute(action="list_schedules")
            elif action == "execute_schedule":
                if not schedule_id:
                    return {
                        "success": False,
                        "message": "schedule_id is required for execute_schedule",
                        "error": "schedule_id is required for execute_schedule",
                    }
                result = await automation_tool.execute(action="execute_schedule", schedule_id=schedule_id)
            elif action == "delete_schedule":
                if not schedule_id:
                    return {
                        "success": False,
                        "message": "schedule_id is required for delete_schedule",
                        "error": "schedule_id is required for delete_schedule",
                    }
                result = await automation_tool.execute(action="delete_schedule", schedule_id=schedule_id)
            elif action == "get_history":
                result = await automation_tool.execute(action="get_history", time_range=time_range)
            elif action == "analyze_patterns":
                result = await automation_tool.execute(action="analyze_patterns")
            else:
                return {
                    "success": False,
                    "message": f"Action '{action}' not implemented",
                    "error": f"Action '{action}' not implemented",
                }
            return {
                "success": result.get("success", True),
                "message": result.get("message", "Action completed"),
                "next_steps": result.get("next_steps", []),
                "action": action,
                "data": result,
                "error": result.get("error"),
            }
        except Exception as e:
            logger.exception("Error in automation management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute automation action '{action}': {e!s}",
            }
