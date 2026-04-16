"""
Devices MCP Prompt Registry
SOTA v14.1.0-compliant prompt definitions for smart home orchestration.
"""

from fastmcp.prompts import Message


def device_status() -> Message:
    """Ask for a full device status summary across cameras, lighting, energy, Ring, and alarms."""
    return Message(
        "Summarize the status of all my smart home devices: cameras, lights, energy plugs, Ring doorbell, and alarms. List what is on/off and any issues."
    )


def list_cameras() -> Message:
    """Ask to list all cameras and their connection status."""
    return Message("List all configured cameras and their current connection status.")


def security_audit() -> Message:
    """Analyze all active security systems and report any vulnerabilities or offline sensors."""
    return Message(
        "Perform a comprehensive security audit of my smart home. Check camera connectivity, Ring status, Nest Protect alarms, and provide a threat summary."
    )


def register_prompts(mcp) -> None:
    """Register all SOTA prompts with the FastMCP instance."""
    mcp.add_prompt(device_status)
    mcp.add_prompt(list_cameras)
    mcp.add_prompt(security_audit)
