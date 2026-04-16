"""
Onboarding API endpoints for device discovery and configuration.

Provides REST API endpoints for the device onboarding process including
device discovery, configuration, and progress tracking.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from devices_mcp.tools.onboarding.device_discovery_tools import (
    OnboardingState,
    discovery_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class DeviceConfigurationRequest(BaseModel):
    """Request model for device configuration."""

    device_id: str = Field(..., description="ID of the device to configure")
    display_name: str = Field(..., description="User-friendly name for the device")
    location: str = Field(..., description="Physical location of the device")
    settings: dict[str, Any] = Field(default_factory=dict, description="Device-specific settings")


class OnboardingProgressResponse(BaseModel):
    """Response model for onboarding progress."""

    status: str
    current_step: int
    total_devices_discovered: int
    devices_configured: int
    completed_steps: list[str]
    onboarding_complete: bool
    last_updated: str
    device_summary: dict[str, dict[str, int]]
    discovered_devices: list[dict[str, Any]]
    configured_devices: dict[str, dict[str, Any]]
    completion_percentage: float
    next_recommended_steps: list[str]


@router.post("/discover")
async def discover_devices(background_tasks: BackgroundTasks):
    """Start device discovery process."""
    try:
        # Wrap background task in error handler to prevent crashes
        async def safe_discover():
            try:
                await discovery_manager.discover_all_devices()
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e).lower()

                # Categorize and log with actionable context
                if "timeout" in error_msg or "timed out" in error_msg:
                    logger.exception(
                        f"Device discovery timed out: {e}",
                        extra={
                            "error_category": "timeout",
                            "actionable": "Check network connectivity and device availability. Discovery may take longer on slow networks.",
                        },
                    )
                elif "connection" in error_msg or "network" in error_msg:
                    logger.exception(
                        f"Device discovery network error: {e}",
                        extra={
                            "error_category": "network",
                            "actionable": "Check network connectivity, firewall settings, and ensure devices are on the same network.",
                        },
                    )
                elif "auth" in error_msg or "credential" in error_msg:
                    logger.exception(
                        f"Device discovery authentication error: {e}",
                        extra={
                            "error_category": "authentication",
                            "actionable": "Check device credentials in config.yaml. Some devices require authentication for discovery.",
                        },
                    )
                else:
                    logger.exception(
                        f"Background device discovery failed: {error_type}: {e}",
                        extra={
                            "error_category": "unknown",
                            "error_type": error_type,
                            "actionable": f"Unexpected error during discovery. Check logs for details. Error: {e}",
                        },
                    )
                # Don't re-raise - background task failures shouldn't crash server

        # Start discovery in background
        background_tasks.add_task(safe_discover)

        return {
            "status": "success",
            "message": "Device discovery started",
            "estimated_duration": "30-60 seconds",
        }

    except Exception as e:
        logger.exception("Device discovery failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/discover/results")
async def get_discovery_results():
    """Get device discovery results."""
    try:
        # Trigger discovery if not already done
        if not discovery_manager.discovered_devices:
            await discovery_manager.discover_all_devices()

        discovery_results = {
            "tapo_p115": [
                device.dict() for device in discovery_manager.discovered_devices if device.device_type == "tapo_p115"
            ],
            "usb_webcams": [
                device.dict() for device in discovery_manager.discovered_devices if device.device_type == "webcam"
            ],
            "nest_protect": [
                device.dict() for device in discovery_manager.discovered_devices if device.device_type == "nest_protect"
            ],
            "ring_devices": [
                device.dict() for device in discovery_manager.discovered_devices if device.device_type == "ring"
            ],
        }

        device_counts = {device_type: len(devices) for device_type, devices in discovery_results.items()}

        return {
            "status": "success",
            "discovery_results": discovery_results,
            "device_counts": device_counts,
            "total_devices": sum(device_counts.values()),
            "onboarding_progress": discovery_manager.get_onboarding_progress(),
        }

    except Exception as e:
        logger.exception("Failed to get discovery results")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/configure")
async def configure_device(config: DeviceConfigurationRequest):
    """Configure a discovered device."""
    try:
        # Find the device in discovered devices
        device = None
        for discovered_device in discovery_manager.discovered_devices:
            if discovered_device.device_id == config.device_id:
                device = discovered_device
                break

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {config.device_id} not found in discovered devices")

        # Update device configuration
        device.display_name = config.display_name
        device.location = config.location
        device.status = "configured"

        # Save configuration to onboarding state
        discovery_manager.onboarding_state.configured_devices[config.device_id] = {
            "display_name": config.display_name,
            "location": config.location,
            "settings": config.settings,
            "configured_at": datetime.now().isoformat(),
        }

        return {
            "status": "success",
            "message": f"Device {config.display_name} configured successfully",
            "device": device.dict(),
            "configuration": discovery_manager.onboarding_state.configured_devices[config.device_id],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Device configuration failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/progress")
async def get_onboarding_progress():
    """Get current onboarding progress."""
    try:
        progress = discovery_manager.get_onboarding_progress()

        # Get device summary
        device_summary = {}
        for device in discovery_manager.discovered_devices:
            device_type = device.device_type
            if device_type not in device_summary:
                device_summary[device_type] = {"total": 0, "configured": 0}

            device_summary[device_type]["total"] += 1
            if device.status == "configured":
                device_summary[device_type]["configured"] += 1

        # Calculate completion percentage
        total_devices = len(discovery_manager.discovered_devices)
        completion_percentage = 0.0
        if total_devices > 0:
            configured_devices = len(discovery_manager.onboarding_state.configured_devices)
            completion_percentage = (configured_devices / total_devices) * 100

        # Get next recommended steps
        next_steps = []
        unconfigured_devices = [
            device for device in discovery_manager.discovered_devices if device.status == "discovered"
        ]

        if unconfigured_devices:
            next_steps.append(f"Configure {len(unconfigured_devices)} remaining devices")

        auth_required_devices = [
            device
            for device in discovery_manager.discovered_devices
            if device.requires_auth and device.status == "discovered"
        ]

        if auth_required_devices:
            next_steps.append("Set up authentication for protected devices")

        if not discovery_manager.onboarding_state.onboarding_complete and not unconfigured_devices:
            next_steps.append("Complete onboarding and start using devices")

        return OnboardingProgressResponse(
            status="success",
            current_step=progress["current_step"],
            total_devices_discovered=progress["total_devices_discovered"],
            devices_configured=progress["devices_configured"],
            completed_steps=progress["completed_steps"],
            onboarding_complete=progress["onboarding_complete"],
            last_updated=progress["last_updated"],
            device_summary=device_summary,
            discovered_devices=[device.dict() for device in discovery_manager.discovered_devices],
            configured_devices=discovery_manager.onboarding_state.configured_devices,
            completion_percentage=completion_percentage,
            next_recommended_steps=next_steps,
        )

    except Exception as e:
        logger.exception("Failed to get onboarding progress")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/complete")
async def complete_onboarding():
    """Complete the onboarding process."""
    try:
        # Validate that all discovered devices are configured
        unconfigured_devices = [
            device for device in discovery_manager.discovered_devices if device.status == "discovered"
        ]

        if unconfigured_devices:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete onboarding: {len(unconfigured_devices)} devices still need configuration",
                extra={"unconfigured_devices": [device.dict() for device in unconfigured_devices]},
            )

        # Mark onboarding as complete
        discovery_manager.onboarding_state.onboarding_complete = True
        discovery_manager.onboarding_state.completed_steps.append("onboarding_complete")
        discovery_manager.onboarding_state.last_updated = datetime.now().isoformat()

        # Generate summary
        device_summary = {}
        for device in discovery_manager.discovered_devices:
            device_type = device.device_type
            if device_type not in device_summary:
                device_summary[device_type] = 0
            device_summary[device_type] += 1

        return {
            "status": "success",
            "message": "Device onboarding completed successfully!",
            "onboarding_complete": True,
            "total_devices_configured": len(discovery_manager.discovered_devices),
            "device_summary": device_summary,
            "configured_devices": [device.dict() for device in discovery_manager.discovered_devices],
            "next_steps": [
                "Start using your configured devices",
                "Set up automation rules if desired",
                "Configure alert preferences",
                "Access the main dashboard at http://localhost:7777",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Onboarding completion failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/devices")
async def get_discovered_devices():
    """Get all discovered devices."""
    try:
        return {
            "status": "success",
            "devices": [device.dict() for device in discovery_manager.discovered_devices],
            "total_count": len(discovery_manager.discovered_devices),
        }

    except Exception as e:
        logger.exception("Failed to get discovered devices")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/devices/{device_id}")
async def get_device_details(device_id: str):
    """Get details for a specific device."""
    try:
        device = None
        for discovered_device in discovery_manager.discovered_devices:
            if discovered_device.device_id == device_id:
                device = discovered_device
                break

        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Get configuration if available
        configuration = discovery_manager.onboarding_state.configured_devices.get(device_id)

        return {
            "status": "success",
            "device": device.dict(),
            "configuration": configuration,
            "is_configured": device.status == "configured",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get device details")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/reset")
async def reset_onboarding():
    """Reset the onboarding process."""
    try:
        # Reset discovery manager state
        discovery_manager.discovered_devices = []
        discovery_manager.onboarding_state = OnboardingState()

        return {"status": "success", "message": "Onboarding process reset successfully"}

    except Exception as e:
        logger.exception("Failed to reset onboarding")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/recommendations")
async def get_setup_recommendations():
    """Get smart setup recommendations based on discovered devices."""
    try:
        devices = discovery_manager.discovered_devices
        recommendations = []

        # Analyze device combinations and generate recommendations
        has_tapo_plugs = any(device.device_type == "tapo_p115" for device in devices)
        has_nest_protect = any(device.device_type == "nest_protect" for device in devices)
        has_ring_devices = any(device.device_type == "ring" for device in devices)
        has_webcams = any(device.device_type == "webcam" for device in devices)

        if has_tapo_plugs and has_nest_protect:
            recommendations.append(
                {
                    "type": "security_integration",
                    "title": "Emergency Power Shutdown",
                    "description": "Automatically turn off non-essential devices during smoke alarms",
                    "safety_benefit": "Reduces fire risk",
                    "complexity": "low",
                    "estimated_setup_time": "5 minutes",
                }
            )

        if has_tapo_plugs and len([d for d in devices if d.device_type == "tapo_p115"]) > 1:
            recommendations.append(
                {
                    "type": "energy_optimization",
                    "title": "Whole House Energy Management",
                    "description": "Set up coordinated schedules for all smart plugs",
                    "estimated_savings": "$50-100/year",
                    "complexity": "medium",
                    "estimated_setup_time": "15 minutes",
                }
            )

        if has_webcams and has_ring_devices:
            recommendations.append(
                {
                    "type": "security_integration",
                    "title": "Motion Alert Correlation",
                    "description": "Link camera motion detection with Ring doorbell alerts",
                    "security_benefit": "Enhanced security monitoring",
                    "complexity": "low",
                    "estimated_setup_time": "10 minutes",
                }
            )

        return {
            "status": "success",
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
        }

    except Exception as e:
        logger.exception("Failed to get setup recommendations")
        raise HTTPException(status_code=500, detail=str(e)) from e
