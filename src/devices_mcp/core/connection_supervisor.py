"""
Connection Supervisor - Ensures all devices stay connected and healthy.

Polls all devices at regular intervals, auto-reconnects on failure,
and provides comprehensive health monitoring for demo reliability.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeviceHealth:
    """Health status for a device."""

    device_id: str
    device_type: str  # camera, plug, light, weather, ring
    name: str
    connected: bool
    last_check: datetime
    last_success: datetime | None
    error_count: int
    last_error: str | None
    details: dict[str, Any]
    circuit_breaker_tripped: bool = False  # Circuit breaker to prevent spam
    circuit_breaker_until: datetime | None = None  # When to retry
    alarm_raised: bool = False  # True after ALARM sent for this offline event


class ConnectionSupervisor:
    """
    Supervisor that polls all devices and maintains connections.

    Features:
    - Regular health checks (configurable interval)
    - Auto-reconnect on failure
    - Connection statistics
    - Alert generation for offline devices
    - Weather data collection (every 10 minutes)
    - Graceful degradation (one device failure doesn't crash others)
    """

    def __init__(self, poll_interval: int = 60):
        """
        Initialize supervisor.

        Args:
            poll_interval: Seconds between health checks (default 60)
        """
        self.poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self.device_health: dict[str, DeviceHealth] = {}

        # Weather data collection counter (collect every 10 minutes = 10 polls at 60s interval)
        self._weather_collection_counter = 0
        self._weather_collection_interval = 10  # polls

        # Messaging service integration
        from .messaging_service import MessageCategory, MessageSeverity, get_messaging_service

        self.messaging = get_messaging_service()
        self.MessageSeverity = MessageSeverity
        self.MessageCategory = MessageCategory

    async def start(self):
        """Start the supervisor polling loop."""
        if self._running:
            logger.warning("Supervisor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Connection supervisor started (polling every {self.poll_interval}s)")

    async def stop(self):
        """Stop the supervisor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Connection supervisor stopped")

    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                await self._check_all_devices()
            except Exception:
                logger.exception("Error in supervisor poll loop")

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    async def _check_all_devices(self):
        """Check health of all devices."""
        logger.debug("Supervisor: Checking all devices...")

        # Check devices in parallel for speed
        await asyncio.gather(
            self._check_cameras(),
            self._check_plugs(),
            self._check_hue_bridge(),
            self._check_hue_homeaware(),
            self._check_netatmo(),
            self._check_ring(),
            self._check_shelly(),
            self._check_home_assistant(),
            return_exceptions=True,  # Don't let one failure crash others
        )

    async def _check_cameras(self):
        """Check all cameras."""
        try:
            from ..core.server import TapoCameraServer

            # Add timeout to prevent blocking
            try:
                server = await asyncio.wait_for(TapoCameraServer.get_instance(), timeout=5.0)
                cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=5.0)
            except TimeoutError:
                logger.warning("Camera manager access timed out - skipping camera checks this cycle")
                return

            for cam in cameras:
                device_id = f"camera_{cam['name']}"
                status = cam.get("status", {})
                connected = status.get("connected", False) if isinstance(status, dict) else False
                cam_type = cam.get("type", "unknown")

                # Check if USB camera is in use by another application
                in_use = status.get("in_use_by_another_app", False) if isinstance(status, dict) else False
                in_use_error = status.get("in_use_error") or status.get("warning") if isinstance(status, dict) else None

                # Determine error message
                error_msg = None
                if in_use:
                    error_msg = in_use_error or "Camera in use by another application (e.g., Microsoft Teams, Zoom)"
                elif not connected:
                    error_msg = "Camera offline"

                self._update_health(
                    device_id=device_id,
                    device_type="camera",
                    name=cam["name"],
                    connected=connected and not in_use,  # Mark as not connected if in use
                    error=error_msg,
                    details={
                        "model": status.get("model", "Unknown") if isinstance(status, dict) else "Unknown",
                        "type": cam_type,
                        "streaming": status.get("streaming", False) if isinstance(status, dict) else False,
                        "in_use_by_another_app": in_use,
                        "device_id": status.get("device_id") if isinstance(status, dict) else None,
                    },
                )

                # Log warning and send alert if camera is in use
                if in_use:
                    device_id_display = status.get("device_id", "?") if isinstance(status, dict) else "?"
                    warning_msg = f"Camera {cam['name']} (USB device {device_id_display}) is in use by another application. Close Microsoft Teams, Zoom, or other video apps."
                    logger.warning(warning_msg)

                    # Send alert message
                    try:
                        from .messaging_service import (
                            MessageCategory,
                            MessageSeverity,
                            get_messaging_service,
                        )

                        messaging = get_messaging_service()
                        messaging.add_message(
                            severity=MessageSeverity.WARNING,
                            category=MessageCategory.DEVICE_CONNECTION,
                            source=device_id,
                            title=f"Camera {cam['name']} Locked by Another Application",
                            description=in_use_error or warning_msg,
                            details={
                                "device_type": "camera",
                                "device_id": device_id,
                                "camera_name": cam["name"],
                                "usb_device_id": status.get("device_id") if isinstance(status, dict) else None,
                                "in_use_by_another_app": True,
                            },
                        )
                    except Exception as e:
                        logger.debug(f"Messaging service unavailable: {e}")

                # Auto-reconnect if offline (but not if in use - that requires user action)
                if not connected and not in_use and cam_type in ["onvif", "tapo"]:
                    logger.warning(f"Camera {cam['name']} offline, attempting reconnect...")
                    try:
                        # Try to reconnect camera
                        pass  # Camera manager handles reconnection
                    except Exception:
                        logger.exception("Failed to reconnect")

        except Exception:
            logger.exception("Error checking cameras")

    async def _check_plugs(self):
        """Check Tapo P115 smart plugs."""
        try:
            # Check if tapo library available
            try:
                import tapo
            except ImportError:
                logger.warning("tapo library not installed - cannot check P115 plugs")
                self._update_health(
                    device_id="plugs_system",
                    device_type="plug",
                    name="Tapo P115 System",
                    connected=False,
                    error="tapo library not installed",
                    details={"library_missing": True},
                )
                return

            from ..config import get_config

            config = get_config()
            plugs_config = config.get("energy", {}).get("tapo_p115", {}).get("devices", [])

            for plug_cfg in plugs_config:
                device_id = plug_cfg.get("device_id", "unknown")
                name = plug_cfg.get("name", device_id)
                host = plug_cfg.get("host")

                # Check circuit breaker - skip if tripped
                existing_health = self.device_health.get(f"plug_{device_id}")
                if (
                    existing_health
                    and existing_health.circuit_breaker_tripped
                    and existing_health.circuit_breaker_until
                    and datetime.now() < existing_health.circuit_breaker_until
                ):
                    # Skip this check, but still report as offline
                    self._update_health(
                        device_id=f"plug_{device_id}",
                        device_type="plug",
                        name=name,
                        connected=False,
                        error=f"Circuit breaker active until {existing_health.circuit_breaker_until}",
                        details={"host": host, "circuit_breaker": True},
                    )
                    continue

                # Try to query plug
                try:
                    account = config.get("energy", {}).get("tapo_p115", {}).get("account", {})
                    account_email = account.get("email") or account.get("username")
                    account_password = account.get("password")

                    if not account_email or not account_password:
                        raise ValueError("Missing Tapo account credentials")

                    # Quick connection test with timeout to prevent hangs
                    try:
                        device = await asyncio.wait_for(
                            tapo.ApiClient(account_email, account_password).p115(host),
                            timeout=5.0,
                        )
                        info = await asyncio.wait_for(device.get_device_info(), timeout=3.0)
                        energy = await asyncio.wait_for(device.get_energy_usage(), timeout=3.0)
                    except TimeoutError:
                        raise ConnectionError(f"Timeout connecting to plug {name} at {host}") from None
                    except Exception as e:
                        raise ConnectionError(f"Failed to connect to plug {name}: {e}") from e

                    current_power = 0.0
                    voltage = 220.0
                    current_a = 0.0
                    try:
                        from ..ingest.tapo_p115 import parse_tapo_power_reading

                        power_data = await asyncio.wait_for(device.get_current_power(), timeout=3.0)
                        current_power, voltage, current_a = parse_tapo_power_reading(power_data)
                    except Exception:
                        pass

                    power_state = bool(getattr(info, "device_on", False))
                    today_kwh = float(getattr(energy, "today_energy", 0) or 0) / 1000.0
                    month_kwh = float(getattr(energy, "month_energy", 0) or 0) / 1000.0

                    try:
                        from ..db import TimeSeriesDB

                        TimeSeriesDB().store_energy_data(
                            device_id=device_id,
                            timestamp=datetime.now(tz=UTC),
                            power_w=current_power,
                            voltage_v=voltage,
                            current_a=current_a,
                            daily_energy_kwh=today_kwh,
                            monthly_energy_kwh=month_kwh,
                            power_state=power_state,
                        )
                    except Exception as db_exc:
                        logger.debug("Time series store for plug %s: %s", device_id, db_exc)

                    self._update_health(
                        device_id=f"plug_{device_id}",
                        device_type="plug",
                        name=name,
                        connected=True,
                        error=None,
                        details={
                            "power": current_power,
                            "today_energy": energy.today_energy if energy else 0,
                            "month_energy": energy.month_energy if energy else 0,
                            "host": host,
                            "model": info.model if info else "P115",
                        },
                    )
                except Exception as e:
                    # Increment error count and check for circuit breaker
                    error_count = 1
                    circuit_breaker_tripped = False
                    circuit_breaker_until = None

                    if existing_health:
                        error_count = existing_health.error_count + 1
                        # Trip circuit breaker after 5 consecutive failures
                        if error_count >= 5:
                            circuit_breaker_tripped = True
                            # Back off for 15 minutes
                            circuit_breaker_until = datetime.now() + timedelta(minutes=15)
                            logger.warning(f"Plug {name} circuit breaker tripped - backing off for 15 minutes")

                    self._update_health(
                        device_id=f"plug_{device_id}",
                        device_type="plug",
                        name=name,
                        connected=False,
                        error=str(e),
                        details={"host": host, "error_count": error_count},
                        circuit_breaker_tripped=circuit_breaker_tripped,
                        circuit_breaker_until=circuit_breaker_until,
                    )

                    # Log all plug status changes for debugging
                    if circuit_breaker_tripped:
                        logger.warning(f"Plug {name} circuit breaker active - skipping check")
                    else:
                        logger.warning(f"Plug {name} offline: {e}")

        except Exception:
            logger.exception("Error checking plugs")

    async def _check_hue_bridge(self):
        """Check Philips Hue Bridge."""
        try:
            # Check if phue available
            import importlib.util

            from ..tools.lighting.hue_tools import hue_manager

            if importlib.util.find_spec("phue") is None:
                self._update_health(
                    device_id="hue_bridge",
                    device_type="light",
                    name="Philips Hue Bridge",
                    connected=False,
                    error="phue library not installed",
                    details={"library_missing": True},
                )
                return

            # Check connection with timeout
            if not hue_manager._initialized:
                try:
                    await asyncio.wait_for(hue_manager.initialize(), timeout=10.0)
                except TimeoutError:
                    self._update_health(
                        device_id="hue_bridge",
                        device_type="light",
                        name="Philips Hue Bridge",
                        connected=False,
                        error="Initialization timeout",
                        details={"timeout": True},
                    )
                    return

            connected = hue_manager._initialized and hue_manager._bridge is not None

            self._update_health(
                device_id="hue_bridge",
                device_type="light",
                name="Philips Hue Bridge",
                connected=connected,
                error=hue_manager._connection_error if not connected else None,
                details={
                    "bridge_ip": hue_manager._bridge_ip,
                    "lights_count": len(hue_manager.lights),
                    "groups_count": len(hue_manager.groups),
                    "scenes_count": len(hue_manager.scenes),
                },
            )

        except Exception:
            logger.exception("Error checking Hue Bridge")

    async def _check_hue_homeaware(self):
        """Check Philips Hue MotionAware (CLIP v2 motion areas on Bridge Pro)."""
        try:
            from importlib.util import find_spec

            from ..tools.lighting.hue_tools import hue_manager

            if find_spec("phue") is None:
                return

            if not hue_manager._clip_v2_available:
                logger.debug("Hue CLIP v2 / MotionAware not available — skipping")
                return

            if not hue_manager._initialized:
                try:
                    await asyncio.wait_for(hue_manager.initialize(), timeout=10.0)
                except TimeoutError:
                    return

            motion_events = await hue_manager.monitor_homeaware_motion()

            for event in motion_events:
                area_id = event.get("area_id", "")
                name = event.get("name") or area_id
                kind = event.get("area_kind", "motion_area")
                device_id = f"hue_motionaware_{kind}_{area_id}"

                self.messaging.alert(
                    category=self.MessageCategory.SECURITY,
                    source=device_id,
                    title=f"MotionAware: {name}",
                    description=(f"Motion reported for {kind} area '{name}' (Hue API v2, id {area_id})."),
                    device_type="motionaware_area",
                    device_name=name,
                    severity="medium",
                )

                logger.warning(
                    "MotionAware motion: %s (%s) area_id=%s",
                    name,
                    kind,
                    area_id,
                )

            ma_ok = hue_manager._clip_v2_available
            self._update_health(
                device_id="hue_motionaware_system",
                device_type="motion_detection",
                name="Hue MotionAware",
                connected=ma_ok,
                error=None if ma_ok else (hue_manager._clip_v2_error or "CLIP v2 unavailable"),
                details={
                    "clip_v2": ma_ok,
                    "motion_edges_this_tick": len(motion_events),
                },
            )

        except Exception:
            logger.exception("Error checking Hue MotionAware motion")

    async def _check_netatmo(self):
        """Check Netatmo weather station."""
        try:
            # Check if pyatmo available
            import importlib.util

            if importlib.util.find_spec("pyatmo") is None:
                self._update_health(
                    device_id="netatmo_weather",
                    device_type="weather",
                    name="Netatmo Weather Station",
                    connected=False,
                    error="pyatmo library not installed",
                    details={"library_missing": True},
                )
                return

            from ..integrations.netatmo_client import NetatmoService

            service = None
            try:
                # Use singleton pattern to share instance with web API
                service = await asyncio.wait_for(NetatmoService.get_instance(), timeout=5.0)

                connected = service._use_real_api and service._account is not None

                if connected:
                    try:
                        # Add timeout to prevent DNS hangs
                        stations = await asyncio.wait_for(service.list_stations(), timeout=5.0)
                        station_count = len(stations)
                        module_count = sum(len(s.get("modules", [])) for s in stations)

                        self._update_health(
                            device_id="netatmo_weather",
                            device_type="weather",
                            name="Netatmo Weather Station",
                            connected=True,
                            error=None,
                            details={"stations": station_count, "modules": module_count},
                        )

                        # Collect weather data every 10 minutes (when counter reaches interval)
                        self._weather_collection_counter += 1
                        if self._weather_collection_counter >= self._weather_collection_interval:
                            self._weather_collection_counter = 0  # Reset counter
                            await self._collect_weather_data(service, stations)
                    except TimeoutError:
                        error_msg = "Connection timeout (DNS/network issue)"
                        error_type = "TimeoutError"
                    except Exception as e:
                        error_msg = str(e)
                        error_type = type(e).__name__

                        # Handle DNS/network errors with specific messages
                        if "getaddrinfo failed" in error_msg or "ClientConnectorDNSError" in error_type:
                            error_msg = "DNS resolution failed (network issue)"
                        elif "Cannot connect to host" in error_msg:
                            error_msg = "Cannot connect to api.netatmo.com (network/firewall issue)"
                        elif "timeout" in error_msg.lower():
                            error_msg = "Connection timeout to Netatmo API"
                        elif "SSL" in error_type or "certificate" in error_msg.lower():
                            error_msg = "SSL/TLS error connecting to Netatmo API"

                        logger.warning(f"Netatmo API call failed: {error_type}: {error_msg}")
                        self._update_health(
                            device_id="netatmo_weather",
                            device_type="weather",
                            name="Netatmo Weather Station",
                            connected=False,
                            error=error_msg,
                            details={"error_type": error_type, "network_error": True},
                        )
                else:
                    self._update_health(
                        device_id="netatmo_weather",
                        device_type="weather",
                        name="Netatmo Weather Station",
                        connected=False,
                        error="Not initialized or no account",
                        details={},
                    )
            finally:
                # Always close service if it was created
                if service:
                    try:
                        await service.close()
                    except Exception as e:
                        logger.debug(f"Error closing service: {e}")

        except Exception as e:
            # Catch all exceptions including network errors
            logger.exception("Netatmo health check failed:")
            self._update_health(
                device_id="netatmo_weather",
                device_type="weather",
                name="Netatmo Weather Station",
                connected=False,
                error=str(e),
                details={"unexpected_error": True},
            )

    async def _collect_weather_data(self, service, stations):
        """Collect and store weather data from all stations every 10 minutes."""
        try:
            logger.debug("Weather data collection: Starting for all stations")

            for station in stations:
                station_id = station.get("_id", station.get("station_id", station.get("id")))
                if not station_id:
                    logger.warning(f"Station missing ID: {station}")
                    continue

                # Netatmo “station systems” are typically one master (NAMain) plus slave indoor modules.
                # `current_data(station_id, "all")` collects indoor+outdoor+extra indoor modules and stores
                # them correctly in our DB. (The previous per-module loop passed module_id where a
                # module_type selector was expected.)
                try:
                    data, _timestamp = await asyncio.wait_for(service.current_data(station_id, "all"), timeout=10.0)
                    if data:
                        extra_count = (
                            len(data.get("extra_indoor", [])) if isinstance(data.get("extra_indoor"), list) else 0
                        )
                        logger.debug(
                            "Weather data collected: %s (indoor+outdoor+%s extra indoor modules)",
                            station_id,
                            extra_count,
                        )
                except Exception as e:
                    logger.warning(f"Failed to collect full Netatmo data for {station_id}: {e}")

            logger.info("Weather data collection completed for all stations")

        except Exception as e:
            logger.exception("Error during weather data collection")
            # Catch all exceptions including network errors
            error_msg = str(e)
            error_type = type(e).__name__

            # Provide specific error messages
            if "getaddrinfo failed" in error_msg or "ClientConnectorDNSError" in error_type:
                error_msg = "DNS resolution failed (Python/aiohttp resolver issue - may be IPv6/IPv4 conflict)"
            elif "Cannot connect to host" in error_msg:
                error_msg = "Cannot connect to api.netatmo.com (firewall/proxy blocking or IPv6 issue)"
            elif "timeout" in error_msg.lower():
                error_msg = "Connection timeout to Netatmo API"
            elif "SSL" in error_type or "certificate" in error_msg.lower():
                error_msg = "SSL/TLS error connecting to Netatmo API"

            logger.warning(f"Error checking Netatmo: {error_type}: {error_msg}")
            self._update_health(
                device_id="netatmo_weather",
                device_type="weather",
                name="Netatmo Weather Station",
                connected=False,
                error=error_msg,
                details={"error_type": error_type, "raw_error": str(e)},
            )

    async def _check_ring(self):
        """Check Ring doorbell."""
        try:
            from ..integrations.ring_client import get_ring_client

            client = get_ring_client("default")
            if client and client.is_initialized:
                try:
                    summary = await asyncio.wait_for(client.get_summary(), timeout=10.0)
                    doorbell_count = summary.get("doorbell_count", 0)

                    self._update_health(
                        device_id="ring_doorbell",
                        device_type="ring",
                        name="Ring Doorbell",
                        connected=True,
                        error=None,
                        details={
                            "doorbells": doorbell_count,
                            "alarm_capable": summary.get("alarm_capable", False),
                        },
                    )
                except Exception as e:
                    self._update_health(
                        device_id="ring_doorbell",
                        device_type="ring",
                        name="Ring Doorbell",
                        connected=False,
                        error=f"API call failed: {e}",
                        details={},
                    )
            else:
                self._update_health(
                    device_id="ring_doorbell",
                    device_type="ring",
                    name="Ring Doorbell",
                    connected=False,
                    error="Not initialized - run 2FA setup",
                    details={"needs_setup": True},
                )

        except Exception:
            logger.exception("Error checking Ring")

    async def _check_shelly(self):
        """Check Shelly temperature sensors."""
        try:
            from ..config import get_config

            # No Shelly hardware configured - skip entirely (otherwise a phantom
            # "Shelly Temperature offline" device appears in every health report).
            shelly_cfg = get_config().get("shelly") or {}
            if not shelly_cfg.get("enabled", False):
                return

            from ..integrations.shelly_client import get_shelly_client

            client = get_shelly_client()
            if client and client.is_initialized:
                try:
                    summary = await asyncio.wait_for(client.get_summary(), timeout=10.0)
                    self._update_health(
                        device_id="shelly_sensors",
                        device_type="shelly",
                        name="Shelly Temperature",
                        connected=True,
                        error=None,
                        details={
                            "sensors": summary.get("sensor_count", 0),
                            "alerts": summary.get("alert_count", 0),
                        },
                    )
                except Exception as e:
                    self._update_health(
                        device_id="shelly_sensors",
                        device_type="shelly",
                        name="Shelly Temperature",
                        connected=False,
                        error=f"API call failed: {e}",
                        details={},
                    )
            else:
                self._update_health(
                    device_id="shelly_sensors",
                    device_type="shelly",
                    name="Shelly Temperature",
                    connected=False,
                    error="Not initialized",
                    details={"needs_setup": True},
                )
        except Exception:
            logger.exception("Error checking Shelly")

    async def _check_home_assistant(self):
        """Check Home Assistant / Nest Protect."""
        try:
            from ..integrations.homeassistant_client import get_homeassistant_client

            client = get_homeassistant_client()
            if client and client.is_initialized:
                try:
                    summary = await asyncio.wait_for(client.get_nest_summary(), timeout=10.0)
                    connected = summary.get("initialized", False)
                    self._update_health(
                        device_id="nest_protect",
                        device_type="nest",
                        name="Nest Protect (HA)",
                        connected=connected,
                        error=None if connected else summary.get("error"),
                        details={
                            "devices": summary.get("total_devices", 0),
                            "all_ok": summary.get("all_ok"),
                        },
                    )
                except Exception as e:
                    self._update_health(
                        device_id="nest_protect",
                        device_type="nest",
                        name="Nest Protect (HA)",
                        connected=False,
                        error=f"API call failed: {e}",
                        details={},
                    )
            else:
                self._update_health(
                    device_id="nest_protect",
                    device_type="nest",
                    name="Nest Protect (HA)",
                    connected=False,
                    error="Home Assistant not connected",
                    details={"needs_setup": True},
                )
        except Exception:
            logger.exception("Error checking Home Assistant")

    def _update_health(
        self,
        device_id: str,
        device_type: str,
        name: str,
        connected: bool,
        error: str | None,
        details: dict[str, Any],
        circuit_breaker_tripped: bool = False,
        circuit_breaker_until: datetime | None = None,
    ):
        """Update health status for a device and generate alerts."""
        now = datetime.now()

        if device_id in self.device_health:
            health = self.device_health[device_id]
            previous_state = health.connected

            health.connected = connected
            health.last_check = now
            health.circuit_breaker_tripped = circuit_breaker_tripped
            health.circuit_breaker_until = circuit_breaker_until

            if connected:
                # Device came back online
                if not previous_state:
                    # Clear stale unacknowledged DEVICE_CONNECTION messages for
                    # this device - without this the offline WARNING/ALARM stays
                    # in the feed forever and every priority aggregation
                    # re-emits the outage (plug reconnected yesterday but the
                    # hub still reported it offline for days).
                    try:
                        for msg in self.messaging.get_messages(acknowledged=False):
                            if msg.category == self.MessageCategory.DEVICE_CONNECTION and (
                                msg.source == device_id or msg.details.get("device_name") == name
                            ):
                                self.messaging.acknowledge_message(msg.id)
                    except Exception:
                        logger.warning("Failed to acknowledge stale messages for %s", name, exc_info=True)

                    self.messaging.info(
                        category=self.MessageCategory.DEVICE_CONNECTION,
                        source=device_id,
                        title=f"{name} Reconnected",
                        description=f"{device_type.upper()} device reconnected successfully",
                        device_type=device_type,
                        device_name=name,
                    )
                    logger.info(f"Device {name} reconnected")

                health.last_success = now
                health.error_count = 0
                health.last_error = None
                health.alarm_raised = False
            else:
                # Device went offline
                if previous_state:
                    # First failure - WARNING
                    self.messaging.warning(
                        category=self.MessageCategory.DEVICE_CONNECTION,
                        source=device_id,
                        title=f"{name} Offline",
                        description=f"{device_type.upper()} device connection lost: {error}",
                        device_type=device_type,
                        device_name=name,
                        error=error,
                    )
                    logger.warning(f"Device {name} went offline: {error}")

                health.error_count += 1
                health.last_error = error

                # Escalate to ALARM after 3 consecutive failures (once only).
                # Devices that were never successfully connected (not yet
                # onboarded) must NOT alarm - there is nothing to be offline
                # from; last_success is None for them.
                if health.error_count == 3 and not health.alarm_raised and health.last_success is not None:
                    self.messaging.alarm(
                        category=self.MessageCategory.DEVICE_CONNECTION,
                        source=device_id,
                        title=f"{name} CRITICAL",
                        description=f"{device_type.upper()} device offline for 3 checks ({3 * self.poll_interval}s). Check device and network.",
                        device_type=device_type,
                        device_name=name,
                        error_count=3,
                        duration_seconds=3 * self.poll_interval,
                    )
                    logger.error(f"Device {name} CRITICAL - offline for {3 * self.poll_interval}s")

                    health.alarm_raised = True

            health.details = details
        else:
            # New device discovered
            self.device_health[device_id] = DeviceHealth(
                device_id=device_id,
                device_type=device_type,
                name=name,
                connected=connected,
                last_check=now,
                last_success=now if connected else None,
                error_count=0 if connected else 1,
                last_error=None if connected else error,
                details=details,
                circuit_breaker_tripped=circuit_breaker_tripped,
                circuit_breaker_until=circuit_breaker_until,
            )

            # Generate discovery message
            if connected:
                self.messaging.info(
                    category=self.MessageCategory.DEVICE_STATUS,
                    source=device_id,
                    title=f"{name} Discovered",
                    description=f"New {device_type.upper()} device detected and connected",
                    device_type=device_type,
                    device_name=name,
                )

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall system health summary."""
        total_devices = len(self.device_health)
        online_devices = sum(1 for h in self.device_health.values() if h.connected)
        offline_devices = total_devices - online_devices

        # Group by type
        by_type = {}
        for health in self.device_health.values():
            device_type = health.device_type
            if device_type not in by_type:
                by_type[device_type] = {"online": 0, "offline": 0}

            if health.connected:
                by_type[device_type]["online"] += 1
            else:
                by_type[device_type]["offline"] += 1

        return {
            "total_devices": total_devices,
            "online": online_devices,
            "offline": offline_devices,
            "health_percentage": round((online_devices / total_devices * 100) if total_devices > 0 else 0, 1),
            "by_type": by_type,
            "devices": [
                {
                    "device_id": h.device_id,
                    "type": h.device_type,
                    "name": h.name,
                    "connected": h.connected,
                    "last_check": h.last_check.isoformat(),
                    "last_success": h.last_success.isoformat() if h.last_success else None,
                    "error_count": h.error_count,
                    "last_error": h.last_error,
                    "details": h.details,
                }
                for h in self.device_health.values()
            ],
        }

    def get_offline_devices(self) -> list[DeviceHealth]:
        """Get list of offline devices."""
        return [h for h in self.device_health.values() if not h.connected]

    def get_device_status(self) -> list[dict[str, Any]]:
        """Get device status as list of dicts for API/metrics export."""
        return [
            {
                "device_id": h.device_id,
                "type": h.device_type,
                "name": h.name,
                "connected": h.connected,
                "last_check": int(h.last_check.timestamp()) if h.last_check else 0,
                "last_success": int(h.last_success.timestamp()) if h.last_success else 0,
                "error_count": h.error_count,
                "last_error": h.last_error,
                "details": h.details,
            }
            for h in self.device_health.values()
        ]


# Global supervisor instance
_supervisor: ConnectionSupervisor | None = None


def get_supervisor() -> ConnectionSupervisor:
    """Get or create global supervisor instance."""
    global _supervisor
    if _supervisor is None:
        _supervisor = ConnectionSupervisor(poll_interval=60)
    return _supervisor
