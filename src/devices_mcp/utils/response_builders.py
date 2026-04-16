"""FastMCP 3.1+ Conversational Response Builders for Devices MCP.

These functions provide structured, conversational responses that enable rich dialogue
between MCP tools and AI assistants, following FastMCP 3.1+ enhanced response patterns.
"""

from typing import Any


def build_success_response(
    operation: str,
    summary: str,
    result: dict[str, Any] | None = None,
    recommendations: list[str] | None = None,
    next_steps: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Build structured success response for MCP clients.

    Args:
        operation: The operation that was performed
        summary: Human-readable summary of the result
        result: Structured result data
        recommendations: Optional suggestions for related actions
        next_steps: Optional guidance on what to do next
        **kwargs: Additional response fields

    Returns:
        Structured response dictionary
    """
    response = {
        "success": True,
        "operation": operation,
        "summary": summary,
    }

    if result is not None:
        response["result"] = result
    if recommendations:
        response["recommendations"] = recommendations
    if next_steps:
        response["next_steps"] = next_steps

    response.update(kwargs)
    return response


def build_error_response(
    error: str,
    error_code: str,
    message: str,
    recovery_options: list[str] | None = None,
    suggestions: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Build structured error response with recovery guidance for MCP clients.

    Args:
        error: Short error description
        error_code: Machine-readable error code
        message: Detailed error message
        recovery_options: Steps to recover from the error
        suggestions: Alternative approaches or preventive measures
        **kwargs: Additional response fields

    Returns:
        Structured error response dictionary
    """
    response = {
        "success": False,
        "error": error,
        "error_code": error_code,
        "message": message,
    }

    if recovery_options:
        response["recovery_options"] = recovery_options
    if suggestions:
        response["suggestions"] = suggestions

    response.update(kwargs)
    return response


def build_hardware_error_response(
    error: str,
    device_type: str,
    device_id: str,
    recovery_options: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Build hardware-specific error response with intelligent recovery recommendations.

    Args:
        error: The hardware error description
        device_type: Type of device (camera, light, etc.)
        device_id: Specific device identifier
        recovery_options: Hardware-specific recovery steps
        **kwargs: Additional response fields

    Returns:
        Structured hardware error response
    """
    base_recovery = [
        f"Check if {device_type} '{device_id}' is powered on and connected to network",
        f"Verify {device_type} '{device_id}' is not blocked by firewall or network restrictions",
        f"Try power cycling {device_type} '{device_id}'",
        f"Check {device_type} '{device_id}' firmware is up to date",
    ]

    if recovery_options:
        base_recovery.extend(recovery_options)

    return build_error_response(
        error=f"{device_type.title()} hardware error",
        error_code=f"HARDWARE_{device_type.upper()}_ERROR",
        message=f"Unable to communicate with {device_type} '{device_id}': {error}",
        recovery_options=base_recovery,
        **kwargs,
    )


def build_network_error_response(
    error: str,
    port: int | None = None,
    service: str | None = None,
    recovery_options: list[str] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Build network-specific error response with intelligent recovery recommendations.

    Args:
        error: The network error description
        port: Port number if applicable
        service: Service name if applicable
        recovery_options: Network-specific recovery steps
        **kwargs: Additional response fields

    Returns:
        Structured network error response
    """
    base_recovery = [
        "Check network connectivity and firewall settings",
        "Verify device is on the same network subnet",
        "Try restarting the MCP server",
    ]

    if port:
        base_recovery.insert(0, f"Check if port {port} is available (might be used by previous server instance)")
        base_recovery.insert(
            1,
            f"Kill any process using port {port}: 'netstat -ano | findstr :{port}' then 'taskkill /PID <pid>'",
        )

    if service:
        base_recovery.insert(0, f"Verify {service} service is running and accessible")

    if recovery_options:
        base_recovery.extend(recovery_options)

    port_info = f" on port {port}" if port else ""
    return build_error_response(
        error="Network connectivity error",
        error_code="NETWORK_ERROR",
        message=f"Network communication failed{port_info}: {error}",
        recovery_options=base_recovery,
        **kwargs,
    )


def build_configuration_error_response(
    error: str, config_field: str, recovery_options: list[str] | None = None, **kwargs
) -> dict[str, Any]:
    """Build configuration-specific error response.

    Args:
        error: The configuration error description
        config_field: Which configuration field is problematic
        recovery_options: Configuration-specific recovery steps
        **kwargs: Additional response fields

    Returns:
        Structured configuration error response
    """
    base_recovery = [
        f"Check {config_field} configuration in config.yaml",
        f"Verify {config_field} format and values are correct",
        "Reload configuration: restart MCP server or call configuration refresh",
        "Check logs for detailed configuration validation errors",
    ]

    if recovery_options:
        base_recovery.extend(recovery_options)

    return build_error_response(
        error="Configuration error",
        error_code="CONFIG_ERROR",
        message=f"Configuration issue with {config_field}: {error}",
        recovery_options=base_recovery,
        **kwargs,
    )
