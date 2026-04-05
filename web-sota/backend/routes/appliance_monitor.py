"""Appliance health monitoring API for detecting device failures via energy patterns."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from devices_mcp.core.server import DevicesMCPServer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/appliance-monitor", tags=["appliance-monitor"])


class ApplianceConfig(BaseModel):
    """Configuration for appliance monitoring."""

    device_id: str
    appliance_type: str  # fridge, freezer, washer, dryer, etc.
    expected_power_range: Dict[str, float]  # {"min": 50, "max": 200} watts
    monitoring_period: int = 3600  # seconds to monitor
    alert_threshold: int = 1800  # seconds without expected power before alert
    enabled: bool = True


class ApplianceStatus(BaseModel):
    """Current status of appliance monitoring."""

    device_id: str
    appliance_type: str
    status: str  # healthy, warning, critical, offline
    current_power: float
    last_active: Optional[datetime]
    monitoring_since: datetime
    alerts_triggered: int
    last_alert: Optional[datetime]


class CreateApplianceMonitorRequest(BaseModel):
    """Request to create appliance monitoring."""

    device_id: str
    appliance_type: str
    expected_power_range: Dict[str, float]
    monitoring_period: Optional[int] = 3600
    alert_threshold: Optional[int] = 1800


class ApplianceAlert(BaseModel):
    """Appliance alert information."""

    device_id: str
    appliance_type: str
    alert_type: str  # no_power, low_power, high_power, offline
    message: str
    triggered_at: datetime
    current_power: float
    expected_range: Dict[str, float]


# In-memory storage for appliance monitoring
_appliance_configs = {}
_appliance_status = {}
_appliance_alerts = []


def get_appliance_configs() -> Dict[str, ApplianceConfig]:
    """Get all appliance configurations."""
    return _appliance_configs.copy()


def get_appliance_status() -> Dict[str, ApplianceStatus]:
    """Get all appliance statuses."""
    return _appliance_status.copy()


def get_appliance_alerts(limit: int = 50) -> List[ApplianceAlert]:
    """Get recent appliance alerts."""
    return _appliance_alerts[-limit:] if _appliance_alerts else []


async def check_appliance_health(device_id: str) -> None:
    """Check health of a specific appliance."""
    if device_id not in _appliance_configs:
        return

    config = _appliance_configs[device_id]

    try:
        # Get current power reading from Tapo plug
        server = await DevicesMCPServer.get_instance()
        energy_client = getattr(server, "energy_client", None)

        if not energy_client:
            logger.warning("No energy client available for appliance monitoring")
            return

        # Get current power
        current_power = await energy_client.get_current_power(device_id)

        now = datetime.now()

        # Initialize status if not exists
        if device_id not in _appliance_status:
            _appliance_status[device_id] = ApplianceStatus(
                device_id=device_id,
                appliance_type=config.appliance_type,
                status="monitoring",
                current_power=current_power,
                last_active=now
                if current_power >= config.expected_power_range.get("min", 0)
                else None,
                monitoring_since=now,
                alerts_triggered=0,
                last_alert=None,
            )

        status = _appliance_status[device_id]
        status.current_power = current_power

        # Check if power is in expected range
        min_power = config.expected_power_range.get("min", 0)
        max_power = config.expected_power_range.get("max", float("inf"))

        is_power_normal = min_power <= current_power <= max_power

        if is_power_normal:
            # Appliance is active
            status.last_active = now
            status.status = "healthy"
        # Check how long it's been since last activity
        elif status.last_active:
            time_since_active = (now - status.last_active).total_seconds()
            if time_since_active > config.alert_threshold:
                # Trigger alert
                alert = ApplianceAlert(
                    device_id=device_id,
                    appliance_type=config.appliance_type,
                    alert_type="no_power" if current_power < min_power else "abnormal_power",
                    message=f"{config.appliance_type.title()} not drawing expected power for {int(time_since_active / 60)} minutes. Current: {current_power}W",
                    triggered_at=now,
                    current_power=current_power,
                    expected_range=config.expected_power_range,
                )

                _appliance_alerts.append(alert)
                status.alerts_triggered += 1
                status.last_alert = now
                status.status = "critical"

                logger.warning(f"Appliance alert: {alert.message}")

                # Send notification (would integrate with alerts system)
                await send_appliance_alert(alert)
            elif time_since_active > (config.alert_threshold / 2):
                status.status = "warning"
            else:
                status.status = "monitoring"

    except Exception as e:
        logger.exception(f"Failed to check appliance health for {device_id}: {e}")
        if device_id in _appliance_status:
            _appliance_status[device_id].status = "error"


async def send_appliance_alert(alert: ApplianceAlert) -> None:
    """Send appliance alert notification."""
    try:
        # This would integrate with your alerts system
        # For now, just log it
        logger.error(f"APPLIANCE ALERT: {alert.message}")

        # Could integrate with:
        # - Email notifications
        # - SMS alerts
        # - Push notifications
        # - Integration with alerts-mcp

    except Exception as e:
        logger.exception(f"Failed to send appliance alert: {e}")


async def monitor_appliances_background() -> None:
    """Background task to monitor all appliances."""
    while True:
        try:
            for device_id in _appliance_configs:
                if _appliance_configs[device_id].enabled:
                    await check_appliance_health(device_id)

            # Check every 5 minutes
            await asyncio.sleep(300)

        except Exception as e:
            logger.exception(f"Error in appliance monitoring background task: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


@router.post("/create")
async def create_appliance_monitor(request: CreateApplianceMonitorRequest):
    """Create monitoring for an appliance."""
    try:
        config = ApplianceConfig(
            device_id=request.device_id,
            appliance_type=request.appliance_type,
            expected_power_range=request.expected_power_range,
            monitoring_period=request.monitoring_period or 3600,
            alert_threshold=request.alert_threshold or 1800,
            enabled=True,
        )

        _appliance_configs[request.device_id] = config

        # Initialize status
        _appliance_status[request.device_id] = ApplianceStatus(
            device_id=request.device_id,
            appliance_type=config.appliance_type,
            status="initializing",
            current_power=0.0,
            last_active=None,
            monitoring_since=datetime.now(),
            alerts_triggered=0,
            last_alert=None,
        )

        logger.info(f"Created appliance monitor for {request.device_id} ({request.appliance_type})")

        return {
            "success": True,
            "message": f"Appliance monitor created for {request.appliance_type}",
            "config": config.dict(),
        }

    except Exception as e:
        logger.exception("Failed to create appliance monitor")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_all_appliance_status():
    """Get status of all monitored appliances."""
    try:
        status_dict = {}
        for device_id, status in _appliance_status.items():
            status_dict[device_id] = status.dict()

        return {"success": True, "appliances": status_dict}

    except Exception as e:
        logger.exception("Failed to get appliance status")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{device_id}")
async def get_appliance_status(device_id: str):
    """Get status of specific appliance."""
    try:
        if device_id not in _appliance_status:
            raise HTTPException(status_code=404, detail=f"Appliance {device_id} not found")

        return {"success": True, "status": _appliance_status[device_id].dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get appliance status for {device_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_recent_alerts(limit: int = 20):
    """Get recent appliance alerts."""
    try:
        alerts = get_appliance_alerts(limit)
        alert_dicts = [alert.dict() for alert in alerts]

        return {"success": True, "alerts": alert_dicts, "total": len(_appliance_alerts)}

    except Exception as e:
        logger.exception("Failed to get appliance alerts")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts")
async def clear_alerts():
    """Clear all appliance alerts."""
    try:
        _appliance_alerts.clear()
        logger.info("Cleared all appliance alerts")

        return {"success": True, "message": "All alerts cleared"}

    except Exception as e:
        logger.exception("Failed to clear appliance alerts")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/{device_id}")
async def manual_health_check(device_id: str):
    """Manually trigger health check for appliance."""
    try:
        if device_id not in _appliance_configs:
            raise HTTPException(status_code=404, detail=f"Appliance {device_id} not configured")

        await check_appliance_health(device_id)

        return {
            "success": True,
            "message": f"Health check completed for {device_id}",
            "status": _appliance_status.get(device_id, {}).dict()
            if device_id in _appliance_status
            else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to manually check appliance health for {device_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_appliance_presets():
    """Get preset configurations for common appliances."""
    presets = {
        "fridge": {
            "appliance_type": "fridge",
            "expected_power_range": {"min": 50, "max": 200},
            "monitoring_period": 3600,
            "alert_threshold": 7200,  # 2 hours - fridges cycle power
            "description": "Refrigerator power monitoring",
        },
        "freezer": {
            "appliance_type": "freezer",
            "expected_power_range": {"min": 30, "max": 150},
            "monitoring_period": 3600,
            "alert_threshold": 10800,  # 3 hours - freezers cycle less frequently
            "description": "Freezer power monitoring",
        },
        "washer": {
            "appliance_type": "washer",
            "expected_power_range": {"min": 100, "max": 2000},
            "monitoring_period": 1800,
            "alert_threshold": 3600,  # 1 hour - washers have distinct cycles
            "description": "Washing machine power monitoring",
        },
        "dryer": {
            "appliance_type": "dryer",
            "expected_power_range": {"min": 500, "max": 5000},
            "monitoring_period": 1800,
            "alert_threshold": 7200,  # 2 hours - dryers run longer cycles
            "description": "Clothes dryer power monitoring",
        },
        "dishwasher": {
            "appliance_type": "dishwasher",
            "expected_power_range": {"min": 100, "max": 1800},
            "monitoring_period": 1800,
            "alert_threshold": 3600,  # 1 hour - dishwashers have timed cycles
            "description": "Dishwasher power monitoring",
        },
        "water_heater": {
            "appliance_type": "water_heater",
            "expected_power_range": {"min": 1000, "max": 6000},
            "monitoring_period": 3600,
            "alert_threshold": 21600,  # 6 hours - water heaters cycle infrequently
            "description": "Water heater power monitoring",
        },
        "ac_unit": {
            "appliance_type": "ac_unit",
            "expected_power_range": {"min": 500, "max": 5000},
            "monitoring_period": 1800,
            "alert_threshold": 3600,  # 1 hour - AC cycles frequently
            "description": "Air conditioner power monitoring",
        },
    }

    return {
        "success": True,
        "presets": presets,
        "usage": "Use preset values as starting point, adjust based on your specific appliance",
    }


@router.post("/start-background-monitoring")
async def start_background_monitoring(background_tasks: BackgroundTasks):
    """Start background appliance monitoring."""
    try:
        # Only start if not already running
        # In a real implementation, you'd track if it's already running

        background_tasks.add_task(monitor_appliances_background)

        logger.info("Started background appliance monitoring")

        return {
            "success": True,
            "message": "Background appliance monitoring started",
            "monitored_appliances": list(_appliance_configs.keys()),
        }

    except Exception as e:
        logger.exception("Failed to start background monitoring")
        raise HTTPException(status_code=500, detail=str(e))
