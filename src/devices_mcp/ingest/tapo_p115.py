"""
Real ingestion adapter for TP-Link Tapo P115 smart plugs.

Uses the 'tapo' Python library (not python-kasa) for Tapo P115 plugs.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from ..config import get_config
from ..db import TimeSeriesDB

if TYPE_CHECKING:
    from tapo import ApiClient
else:
    try:
        from tapo import ApiClient
    except ImportError:  # pragma: no cover - tapo is optional
        ApiClient = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


def parse_tapo_power_reading(power_data: Any) -> tuple[float, float, float]:
    """Parse tapo plug ``get_current_power()`` response into watts, volts, amps."""
    current_power = 0.0
    voltage = 220.0
    current = 0.0
    if power_data is None:
        return current_power, voltage, current

    for attr in ("current_power", "power", "power_mw", "power_w"):
        val = getattr(power_data, attr, None)
        if val is not None:
            current_power = float(val)
            if attr == "power_mw":
                current_power = current_power / 1000.0
            break

    for attr in ("voltage", "voltage_v", "voltage_mv"):
        val = getattr(power_data, attr, None)
        if val is not None:
            voltage = float(val)
            if attr == "voltage_mv":
                voltage = voltage / 1000.0
            break

    for attr in ("current", "current_a", "current_ma"):
        val = getattr(power_data, attr, None)
        if val is not None:
            current = float(val)
            if attr == "current_ma":
                current = current / 1000.0
            break

    if current == 0.0 and current_power > 0 and voltage > 0:
        current = current_power / voltage

    return current_power, voltage, current


class IngestionUnavailableError(RuntimeError):
    """Raised when a real ingestion adapter cannot be used."""


class TapoP115IngestionService:
    """
    Communicates with Tapo P115 plugs via the 'tapo' Python library.

    The service looks for configuration in the main `config.yaml` under
    `energy.tapo_p115`. If no configuration is present it falls back to
    environment variables:

    - `TAPO_ACCOUNT_EMAIL`
    - `TAPO_ACCOUNT_PASSWORD`
    - `TAPO_P115_HOSTS` (comma separated list)
    """

    def __init__(self, config: dict | None = None):
        if config is not None:
            self._config = config
            logger.info("Tapo P115 ingestion using provided config")
        else:
            try:
                self._config = get_config().get("energy", {}).get("tapo_p115", {})
                logger.info("Tapo P115 ingestion config loaded successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to load config for Tapo P115 ingestion: {e}, using defaults"
                )
                self._config = {}
        self._account = self._config.get("account", {})
        self._devices_cfg = self._config.get("devices", [])
        self._discovery_cfg = self._config.get("discovery", {})
        # Delay DB initialization until needed
        self._db = None

        self._hosts: list[str] = [
            device.get("host") for device in self._devices_cfg if device.get("host")
        ]

        logger.info(f"Tapo P115 configured devices: {len(self._devices_cfg)}")
        logger.info(f"Tapo P115 configured hosts: {self._hosts}")
        logger.info(f"Tapo P115 account: {self._account.get('email', 'no email')}")

        env_hosts = os.getenv("TAPO_P115_HOSTS")
        if env_hosts:
            self._hosts.extend(host.strip() for host in env_hosts.split(",") if host.strip())

        self._hosts = list(dict.fromkeys(self._hosts))  # deduplicate while preserving order
        logger.info(f"Tapo P115 final hosts: {self._hosts}")

        self._email = (
            self._account.get("email")
            or self._account.get("username")
            or os.getenv("TAPO_ACCOUNT_EMAIL")
            or os.getenv("TAPO_ACCOUNT_USERNAME")
        )
        self._password = self._account.get("password") or os.getenv("TAPO_ACCOUNT_PASSWORD")

        # LAN broadcast discovery (tapo.ApiClient.discover_devices) when no static hosts:
        # default enabled if nothing to query; override with energy.tapo_p115.discovery.enabled
        # or TAPO_P115_DISCOVERY_ENABLED=0|1.
        env_disc = os.getenv("TAPO_P115_DISCOVERY_ENABLED", "").strip().lower()
        if env_disc in ("0", "false", "no", "off"):
            self._discovery_enabled = False
        elif env_disc in ("1", "true", "yes", "on"):
            self._discovery_enabled = True
        elif self._discovery_cfg.get("enabled") is not None:
            self._discovery_enabled = bool(self._discovery_cfg.get("enabled"))
        else:
            self._discovery_enabled = not bool(self._hosts)

        self._discovery_timeout = int(self._discovery_cfg.get("timeout", 10))
        self._metadata_by_host = {device.get("host"): device for device in self._devices_cfg if device.get("host")}

        # Cache for ApiClient instance
        self._client: ApiClient | None = None
        self._client_lock = asyncio.Lock()

        if ApiClient is None:
            raise IngestionUnavailableError(
                "tapo library is not installed; install it to enable real Tapo P115 ingestion: pip install tapo"
            )

        if not self._email or not self._password:
            raise IngestionUnavailableError(
                "Tapo account credentials not configured. Provide email/password in config.yaml under "
                "`energy.tapo_p115.account` or set TAPO_ACCOUNT_EMAIL and TAPO_ACCOUNT_PASSWORD."
            )

        if not self._hosts and not self._discovery_enabled:
            raise IngestionUnavailableError(
                "No Tapo P115 hosts configured. Provide hosts in config.yaml under "
                "`energy.tapo_p115.devices`, set TAPO_P115_HOSTS, or enable LAN discovery "
                "(default when no hosts: `energy.tapo_p115.discovery.enabled` or unset; "
                "set TAPO_P115_BROADCAST for subnet broadcast, e.g. 192.168.1.255)."
            )

    def _get_db(self):
        """Get database instance lazily."""
        if self._db is None:
            self._db = TimeSeriesDB()
        return self._db

    async def _get_client(self) -> ApiClient:
        """Get or create ApiClient instance."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    if not self._email or not self._password:
                        raise IngestionUnavailableError("Tapo credentials not configured")
                    self._client = ApiClient(self._email, self._password)
        return self._client

    async def _discover_energy_plug_hosts_via_lan(self) -> list[str]:
        """Use tapo broadcast discovery to find P110/P115-class plugs on the LAN."""
        try:
            from tapo import DiscoveryResult
        except ImportError:
            return []

        broadcast = (
            os.getenv("TAPO_P115_BROADCAST")
            or self._discovery_cfg.get("broadcast")
            or "255.255.255.255"
        )
        timeout_s = min(60, max(1, self._discovery_timeout))
        hosts: list[str] = []
        client = await self._get_client()
        logger.info(
            "Tapo LAN discovery: broadcast=%s timeout_s=%s (set TAPO_P115_BROADCAST for subnet, e.g. 192.168.1.255)",
            broadcast,
            timeout_s,
        )
        try:
            discovery = await client.discover_devices(broadcast, timeout_s=timeout_s)
            async for maybe in discovery:
                try:
                    result = maybe.get()
                except Exception:
                    continue
                if isinstance(result, DiscoveryResult.PlugEnergyMonitoring):
                    ip = getattr(result.device_info, "ip", None)
                    if ip:
                        hosts.append(str(ip))
        except Exception:
            logger.exception("Tapo LAN broadcast discovery failed")
        return list(dict.fromkeys(hosts))

    async def discover_devices(self) -> list[dict[str, object]]:
        """
        Discover and fetch real-time statistics for configured Tapo P115 plugs.
        """
        logger.info(f"Starting Tapo P115 discovery for hosts: {self._hosts}")
        discovered_host_data: list[dict[str, object]] = []
        hosts = list(self._hosts)

        if not hosts and self._discovery_enabled:
            found = await self._discover_energy_plug_hosts_via_lan()
            if found:
                hosts = found
                logger.info("Tapo P115 discovery will use LAN-found hosts: %s", hosts)
            else:
                logger.warning(
                    "LAN discovery found no plugs; set TAPO_P115_HOSTS or energy.tapo_p115.devices[].host"
                )

        if not hosts:
            logger.warning("No P115 hosts available for discovery")
            return []

        logger.info(f"Querying {len(hosts)} hosts: {hosts}")

        results = await asyncio.gather(
            *(self._fetch_device_snapshot(host) for host in hosts),
            return_exceptions=True,
        )

        logger.info(f"Discovery completed, processing {len(results)} results")
        for i, result in enumerate(results):
            host = hosts[i]
            if isinstance(result, Exception):
                logger.warning(f"Host {host} failed: {result}")
                # Create device entry from config even if connection failed
                device_cfg = self._metadata_by_host.get(host, {})
                device_id = device_cfg.get("device_id") or f"tapo_p115_{host.replace('.', '_')}"
                device_entry = {
                    "device_id": device_id,
                    "name": device_cfg.get("name", f"P115 {host}"),
                    "location": device_cfg.get("location", "Unknown"),
                    "type": "tapo_p115",
                    "device_model": "P115",
                    "power_state": False,
                    "current_power": 0.0,
                    "voltage": 0.0,
                    "current": 0.0,
                    "daily_energy": 0.0,
                    "monthly_energy": 0.0,
                    "daily_cost": 0.0,
                    "monthly_cost": 0.0,
                    "last_seen": None,
                    "error": str(result),
                }
                logger.info(f"Adding failed device {device_id} ({device_entry['name']}) to results")
                discovered_host_data.append(device_entry)
            elif result and isinstance(result, dict):
                logger.info(f"Host {host} succeeded: {result.get('name')}")
                discovered_host_data.append(result)
            else:
                logger.warning(f"Host {host} returned unexpected result: {type(result)}")
                # Still create device entry from config
                device_cfg = self._metadata_by_host.get(host, {})
                device_id = device_cfg.get("device_id") or f"tapo_p115_{host.replace('.', '_')}"
                device_entry = {
                    "device_id": device_id,
                    "name": device_cfg.get("name", f"P115 {host}"),
                    "location": device_cfg.get("location", "Unknown"),
                    "type": "tapo_p115",
                    "device_model": "P115",
                    "power_state": False,
                    "current_power": 0.0,
                    "voltage": 0.0,
                    "current": 0.0,
                    "daily_energy": 0.0,
                    "monthly_energy": 0.0,
                    "daily_cost": 0.0,
                    "monthly_cost": 0.0,
                    "last_seen": None,
                    "error": "Unknown error",
                }
                discovered_host_data.append(device_entry)

        logger.info(f"Discovery returning {len(discovered_host_data)} devices")
        return discovered_host_data

    async def _fetch_device_snapshot(self, host: str) -> dict[str, object] | None:
        """
        Collect realtime metrics for a single plug using tapo library.
        """
        try:
            client = await asyncio.wait_for(self._get_client(), timeout=5.0)
            plug = await asyncio.wait_for(client.p115(host), timeout=5.0)

            # Get device info
            device_info = await asyncio.wait_for(plug.get_device_info(), timeout=3.0)
            device_name = getattr(
                device_info, "nickname", getattr(device_info, "name", f"P115 {host}")
            )
            model = getattr(device_info, "model", "P115")
            device_id_attr = getattr(device_info, "device_id", None)

            # Get power state
            try:
                # Use device_info.device_on instead of is_on() method
                device_info_for_state = await asyncio.wait_for(plug.get_device_info(), timeout=3.0)
                power_state = bool(getattr(device_info_for_state, "device_on", False))
            except Exception:
                power_state = False

            # Get real-time current power (watts)
            current_power = 0.0
            voltage = 220.0  # Default to 220V for European mains (user specified)
            current = 0.0
            try:
                power_data = await asyncio.wait_for(plug.get_current_power(), timeout=3.0)
                current_power, voltage, current = parse_tapo_power_reading(power_data)
            except Exception as e:
                logger.debug(f"Real-time power not available for {host}: {e}")
                # Keep defaults (0W, 220V, 0A)

            # Get energy usage (daily/monthly totals)
            today_energy = 0.0
            month_energy = 0.0
            try:
                energy = await asyncio.wait_for(plug.get_energy_usage(), timeout=3.0)
                # Energy values are in Wh (watt-hours), convert to kWh
                today_energy = float(getattr(energy, "today_energy", 0)) / 1000.0
                month_energy = float(getattr(energy, "month_energy", 0)) / 1000.0

                logger.debug(
                    f"Energy data for {host}: power={current_power}W, voltage={voltage}V, current={current}A, today={today_energy}kWh"
                )
            except Exception as e:
                logger.warning(f"Energy usage not available for {host}: {e}")

            metadata = self._metadata_by_host.get(host, {})
            device_id = metadata.get("device_id") or device_id_attr
            if not device_id:
                device_id = f"tapo_p115_{host.replace('.', '_')}"

            snapshot_data = {
                "host": host,
                "device_id": device_id,
                "name": metadata.get("name") or device_name,
                "location": metadata.get("location", "Unknown"),
                "device_model": model,
                "power_state": power_state,
                "current_power": current_power,
                "voltage": voltage,
                "current": current,
                "daily_energy": today_energy,
                "monthly_energy": month_energy,
                "last_seen": datetime.now(tz=timezone.utc).isoformat(),
            }

            # Store data point in database
            try:
                timestamp = datetime.now(tz=timezone.utc)
                self._get_db().store_energy_data(
                    device_id=device_id,
                    timestamp=timestamp,
                    power_w=current_power,
                    voltage_v=voltage,
                    current_a=current,
                    daily_energy_kwh=today_energy,
                    monthly_energy_kwh=month_energy,
                    power_state=power_state,
                )
            except Exception as db_exc:
                logger.warning(f"Failed to store energy data in database: {db_exc}")

            return snapshot_data
        except Exception as exc:
            logger.warning(f"Unable to query Tapo P115 at {host}: {exc}")
            return None

    async def control_device(self, host: str, *, turn_on: bool | None = None) -> None:
        """
        Toggle plug state using tapo library.
        """
        client = await self._get_client()
        plug = await client.p115(host)

        if turn_on is True:
            await plug.on()
        elif turn_on is False:
            await plug.off()

    async def fetch_usage_series(self, host: str, *, hours: int = 24) -> list[dict[str, object]]:
        """
        Build a lightweight time series using real readings. Tapo P115 only
        exposes day-level counters, so we provide the latest realtime snapshot
        and a synthetic series derived from daily totals.
        """
        snapshot = await self._fetch_device_snapshot(host)
        if not snapshot:
            return []

        now = datetime.now(tz=timezone.utc)
        hourly_energy = float(snapshot["daily_energy"])
        # Spread the daily energy across the elapsed hours.
        elapsed_hours = max(1, now.hour or 1)
        per_hour = hourly_energy / elapsed_hours if hourly_energy else 0.0

        series: list[dict[str, object]] = []
        for i in range(min(hours, elapsed_hours)):
            ts = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
            series.append(
                {
                    "timestamp": ts.isoformat(),
                    "energy_kwh": per_hour,
                    "power_w": snapshot["current_power"],
                }
            )

        return list(reversed(series))
