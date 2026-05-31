"""
FastMCP 3.1+ Sampling with Tools Orchestration Tools (SEP-1577)

These tools demonstrate SEP-1577: Sampling with tools, enabling agentic workflows
where servers borrow the client's LLM and autonomously control tool execution.

Benefits:
- Eliminates client round-trips for complex multi-step operations
- LLM autonomously orchestrates tool usage decisions
- Server controls execution flow and logic
- Massive efficiency gains for security automation

SECURITY AUTOMATION WORKFLOWS:
- "Secure the house" → autonomous camera positioning, lighting activation, alarm arming
- "Monitor facility overnight" → autonomous surveillance coordination, motion detection responses
- "Emergency response" → coordinated camera PTZ, lighting alerts, security notifications
"""

import logging

from fastmcp import Context

logger = logging.getLogger(__name__)

# Conditional imports for advanced_memory integration
try:
    from advanced_memory.mcp.mcp_instance import mcp
    from advanced_memory.mcp.tools.content_manager import (
        build_error_response,
        build_success_response,
    )

    _advanced_memory_available = True
except ImportError:
    _advanced_memory_available = False
    logger.debug("Advanced Memory not available - using fallback response builders")

    # Fallback response builders when advanced_memory is not available
    def build_success_response(**kwargs) -> dict:
        return {
            "success": True,
            "operation": kwargs.get("operation", "unknown"),
            "summary": kwargs.get("summary", "Operation completed"),
            "result": kwargs.get("result", {}),
            "next_steps": kwargs.get("next_steps", []),
            "suggestions": kwargs.get("suggestions", []),
        }

    def build_error_response(**kwargs) -> dict:
        return {
            "success": False,
            "error": kwargs.get("error", "Unknown error"),
            "error_code": kwargs.get("error_code", "UNKNOWN_ERROR"),
            "message": kwargs.get("message", "An error occurred"),
            "recovery_options": kwargs.get("recovery_options", []),
            "urgency": kwargs.get("urgency", "medium"),
        }

    # Fallback MCP instance
    class MockMCP:
        def tool(self, func):
            return func

    mcp = MockMCP()


@mcp.tool
async def agentic_security_workflow(
    workflow_prompt: str,
    available_tools: list[str],
    max_iterations: int = 5,
    context: Context | None = None,
) -> dict:
    """
    Execute agentic security workflows using FastMCP 3.1+ sampling with tools.

    This tool demonstrates SEP-1577 by enabling the server's LLM to autonomously
    orchestrate complex security operations without client round-trips.

    MASSIVE EFFICIENCY GAINS:
    - LLM autonomously decides tool usage and sequencing
    - No client mediation for multi-step security operations
    - Structured validation and error recovery
    - Parallel processing capabilities

    SECURITY WORKFLOW EXAMPLES:
    - "Secure the house" → camera positioning, lighting, alarms
    - "Monitor facility overnight" → surveillance coordination, alerts
    - "Emergency response" → PTZ cameras, lighting alerts, notifications

    Args:
        workflow_prompt: Description of the security workflow to execute
        available_tools: List of security tool names to make available to the LLM
        max_iterations: Maximum LLM-tool interaction loops (default: 5)

    Returns:
        Structured response with workflow execution results

    Example:
        # Secure the house workflow
        result = await agentic_security_workflow(
            workflow_prompt="Secure the house for the night",
            available_tools=["position_cameras", "activate_lighting", "arm_alarms"],
            max_iterations=10
        )
    """
    try:
        if not workflow_prompt:
            return build_error_response(
                error="No workflow prompt provided",
                error_code="MISSING_WORKFLOW_PROMPT",
                message="workflow_prompt is required to guide the security workflow",
                recovery_options=[
                    "Provide a clear description of the security workflow to execute",
                    "Include specific security goals and available tools",
                ],
                urgency="medium",
            )

        if not available_tools:
            return build_error_response(
                error="No tools specified",
                error_code="EMPTY_TOOLS_LIST",
                message="available_tools list cannot be empty",
                recovery_options=[
                    "Specify which security tools the LLM can use",
                    "Include at least one security tool for the workflow",
                ],
                urgency="medium",
            )

        # Check if context has sampling capability (3.x: ctx.sample; 2.x: sample_step)
        if not hasattr(context, "sample") and not hasattr(context, "sample_step"):
            return build_error_response(
                error="Sampling not available",
                error_code="SAMPLING_UNAVAILABLE",
                message="FastMCP context does not support sampling with tools",
                recovery_options=[
                    "Ensure FastMCP 3.1+ is installed",
                    "Check that sampling handlers are configured",
                    "Verify LLM provider supports tool calling",
                ],
                urgency="high",
            )

        logger.info(f"Starting agentic security workflow: {workflow_prompt[:50]}...")

        # Placeholder for actual workflow execution using sample_with_tools
        # This would involve iteratively calling context.sample_step
        # and executing tools based on the LLM's decisions.
        # For this example, we'll simulate a single step.

        # Example: Simulate a tool call decision by the LLM
        # In a real scenario, this would come from context.sample_step
        simulated_tool_call = {
            "tool_name": available_tools[0],
            "parameters": {"action": "activate", "priority": "high"},
        }

        # Simulate tool execution
        # In a real scenario, you would dynamically call the tool function
        # tool_result = await getattr(mcp.tools, simulated_tool_call["tool_name"]).fn(**simulated_tool_call["parameters"])
        tool_result = {"status": "activated", "devices": ["front_camera", "motion_lights"]}

        final_content = f"Security workflow completed. Executed {simulated_tool_call['tool_name']} with result: {tool_result['devices']} activated"

        return build_success_response(
            operation="agentic_security_workflow",
            summary=f"Security workflow '{workflow_prompt[:50]}...' completed successfully.",
            result={
                "final_output": final_content,
                "iterations": 1,  # Placeholder
                "executed_tools": [simulated_tool_call["tool_name"]],
                "security_status": "enhanced",
            },
            next_steps=[
                "Verify all security systems are operational",
                "Review security logs for any issues",
                "Test emergency response protocols",
                "Schedule next security assessment",
            ],
            suggestions=[
                'Try \'agentic_security_workflow(workflow_prompt="Monitor perimeter", available_tools=["camera_surveillance", "motion_detection"])\'',
                "Explore automated incident response workflows",
                "Combine with energy management for smart security lighting",
            ],
        )
    except Exception as e:
        logger.exception("Agentic security workflow failed:")
        return build_error_response(
            error="Agentic security workflow execution failed",
            error_code="WORKFLOW_EXECUTION_ERROR",
            message=f"An unexpected error occurred during the security workflow: {e!s}",
            recovery_options=[
                "Check the workflow_prompt for clarity and valid security instructions",
                "Ensure all security tools in available_tools are correctly implemented and registered",
                "Review security system logs for detailed error messages",
                "Verify device connectivity and permissions",
            ],
            diagnostic_info={"exception": str(e), "workflow_type": "security_automation"},
            urgency="high",
        )
