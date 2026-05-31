import logging

from fastapi import APIRouter, HTTPException, Response

from devices_mcp.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics", summary="Prometheus metrics endpoint")
async def get_prometheus_metrics() -> Response:
    """
    Expose Prometheus-formatted metrics for Grafana.
    Includes P115 energy metrics for alerting.
    """
    try:
        from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

        config = get_config()

        metrics_lines = []

        # Collect P115 power metrics
        devices = await tapo_plug_manager.get_all_devices()
        for device in devices:
            device_id = device.device_id
            host = tapo_plug_manager.get_device_host(device_id) or "unknown"
            name = device.name or device_id
            location = getattr(device, "location", "unknown")

            power_watts = 0.0
            try:
                account = config.get("energy", {}).get("tapo_p115", {}).get("account", {})
                account_email = account.get("email") or account.get("username")
                account_password = account.get("password")

                if account_email and account_password and host != "unknown":
                    import tapo

                    client = await tapo.ApiClient(account_email, account_password).p115(host)
                    current_power_result = await client.get_current_power()
                    power_watts = (
                        current_power_result.current_power if hasattr(current_power_result, "current_power") else 0.0
                    )
            except Exception:
                power_watts = getattr(device, "current_power", 0.0)

            labels = f'device_id="{device_id}",host="{host}",name="{name}",location="{location}"'
            metrics_lines.append(f"tapo_p115_power_watts{{{labels}}} {power_watts}")
            metrics_lines.append(f"tapo_p115_voltage_volts{{{labels}}} {getattr(device, 'voltage', 0.0)}")
            metrics_lines.append(f"tapo_p115_current_amps{{{labels}}} {getattr(device, 'current', 0.0)}")
            metrics_lines.append(f"tapo_p115_daily_energy_kwh{{{labels}}} {device.daily_energy}")
            metrics_lines.append(f"tapo_p115_monthly_energy_kwh{{{labels}}} {device.monthly_energy}")
            metrics_lines.append(f"tapo_p115_power_state{{{labels}}} {1 if device.power_state else 0}")

        # Device health metrics
        try:
            from devices_mcp.core.connection_supervisor import get_supervisor

            supervisor = get_supervisor()
            if supervisor:
                for device in supervisor.get_device_status():
                    d_id = device.get("device_id", "unknown")
                    d_type = device.get("type", "unknown")
                    d_name = device.get("name", d_id)
                    conn = 1 if device.get("connected", False) else 0
                    metrics_lines.append(
                        f'device_health_status{{device_id="{d_id}",type="{d_type}",name="{d_name}"}} {conn}'
                    )
        except Exception:
            pass

        metrics_text = "\n".join(metrics_lines) + "\n"
        return Response(content=metrics_text, media_type="text/plain; version=0.0.4")
    except Exception as e:
        logger.exception("Error generating Prometheus metrics")
        return Response(content=f"# Error: {e}\n", media_type="text/plain", status_code=500)


@router.get("/api/energy/status")
async def get_energy_status():
    """Get all smart plugs status using MCP energy tools."""
    try:
        from devices_mcp.tools.energy.energy_management_tool import EnergyManagementTool

        tool = EnergyManagementTool()
        result = await tool.execute(operation="status")
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail="Failed to retrieve energy data")
        return result
    except Exception as e:
        logger.exception(f"Error in get_energy_status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/energy/consumption")
async def get_energy_consumption(time_range: str = "24h"):
    """Get energy consumption data using MCP energy tools."""
    try:
        from devices_mcp.tools.energy.energy_management_tool import EnergyManagementTool

        tool = EnergyManagementTool()
        result = await tool.execute(operation="consumption", time_range=time_range)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail="Failed to retrieve consumption data")
        return result
    except Exception as e:
        logger.exception(f"Error in get_energy_consumption: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/energy/control")
async def control_energy_device(device_id: str, action: str):
    """Control smart plug using MCP energy tools."""
    try:
        from devices_mcp.tools.energy.energy_management_tool import EnergyManagementTool

        if action not in ["on", "off", "toggle"]:
            raise HTTPException(status_code=400, detail="Invalid action")
        tool = EnergyManagementTool()
        result = await tool.execute(operation="control", device_id=device_id, action=action)
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.exception(f"Error controlling energy device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
