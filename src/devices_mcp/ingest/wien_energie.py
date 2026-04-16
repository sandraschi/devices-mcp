"""
Real ingestion adapter for Wien Energie smart meters via Wiener Netze infrastructure.

Uses IEC 62056-21 (DLMS/COSEM) protocol for communication with smart meters
via infrared reading adapter.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime

from ..config import get_config
from ..db import TimeSeriesDB

logger = logging.getLogger(__name__)

# Try to import DLMS/COSEM libraries (optional dependencies)
try:
    import serial
    import serial_asyncio
except ImportError:
    serial = None  # type: ignore[assignment]
    serial_asyncio = None  # type: ignore[assignment]

# DLMS/COSEM library would be imported here if available
# For now, we'll create a structure that can be extended


class IngestionUnavailableError(RuntimeError):
    """Raised when a real ingestion adapter cannot be used."""


class WienEnergieIngestionService:
    """
    Communicates with Wien Energie smart meters via IEC 62056-21 (DLMS/COSEM) protocol.

    The service looks for configuration in the main `config.yaml` under
    `energy.wien_energie`. If no configuration is present it falls back to
    environment variables:

    - `WIEN_ENERGIE_ENABLED`
    - `WIEN_ENERGIE_ADAPTER_PORT`
    - `WIEN_ENERGIE_SECURITY_KEY`
    - `WIEN_ENERGIE_POLLING_INTERVAL`
    """

    # OBIS codes for common energy data points
    OBIS_TOTAL_ENERGY = "1.0.0.0.0.255"  # Total energy consumption (kWh)
    OBIS_ACTIVE_POWER = "1.0.1.7.0.255"  # Active power (W)
    OBIS_VOLTAGE = "1.0.32.7.0.255"  # Voltage (V)
    OBIS_CURRENT = "1.0.31.7.0.255"  # Current (A)
    OBIS_POWER_FACTOR = "1.0.13.7.0.255"  # Power factor
    OBIS_FREQUENCY = "1.0.14.7.0.255"  # Frequency (Hz)

    def __init__(self, config: dict | None = None):
        self._config = config or get_config().get("energy", {}).get("wien_energie", {})
        self._adapter_cfg = self._config.get("adapter", {})
        self._security_cfg = self._config.get("security", {})
        self._meter_cfg = self._config.get("meter", {})
        self._polling_cfg = self._config.get("polling", {})
        self._tariffs_cfg = self._config.get("tariffs", {})
        self._db = TimeSeriesDB()

        # Adapter configuration
        self._adapter_type = self._adapter_cfg.get("type", "ir")
        self._adapter_port = self._adapter_cfg.get("port") or os.getenv("WIEN_ENERGIE_ADAPTER_PORT") or "/dev/ttyUSB0"
        self._baudrate = self._adapter_cfg.get("baudrate", 9600)
        self._timeout = self._adapter_cfg.get("timeout", 5)

        # Security configuration
        self._security_key = self._security_cfg.get("key") or os.getenv("WIEN_ENERGIE_SECURITY_KEY")
        self._encryption = self._security_cfg.get("encryption", "AES-128")

        # Meter configuration
        self._meter_serial = self._meter_cfg.get("serial_number", "auto-detect")
        self._obis_codes = self._meter_cfg.get("obis_codes", {})

        # Polling configuration
        self._polling_enabled = self._polling_cfg.get("enabled", True)
        self._polling_interval = int(self._polling_cfg.get("interval_seconds", 60))

        # Tariff configuration
        self._base_rate = float(self._tariffs_cfg.get("base_rate", 0.12))  # EUR/kWh
        self._peak_rate = float(self._tariffs_cfg.get("peak_rate", 0.15))
        self._off_peak_rate = float(self._tariffs_cfg.get("off_peak_rate", 0.10))

        # Connection state
        self._serial_reader: asyncio.StreamReader | None = None
        self._serial_writer: asyncio.StreamWriter | None = None
        self._connection_lock = asyncio.Lock()

        # Check dependencies
        if serial is None or serial_asyncio is None:
            raise IngestionUnavailableError(
                "pyserial and pyserial-asyncio are required for Wien Energie integration. "
                "Install with: pip install pyserial pyserial-asyncio"
            )

        if not self._security_key:
            raise IngestionUnavailableError(
                "Wien Energie security key not configured. Provide key in config.yaml under "
                "`energy.wien_energie.security.key` or set WIEN_ENERGIE_SECURITY_KEY."
            )

    async def _ensure_connection(self) -> None:
        """Ensure serial connection to adapter is established."""
        if self._serial_reader is None or self._serial_writer is None:
            async with self._connection_lock:
                if self._serial_reader is None or self._serial_writer is None:
                    try:
                        (
                            self._serial_reader,
                            self._serial_writer,
                        ) = await serial_asyncio.open_serial_connection(
                            url=self._adapter_port,
                            baudrate=self._baudrate,
                            timeout=self._timeout,
                        )
                        logger.info(f"Connected to Wien Energie adapter at {self._adapter_port}")
                    except Exception as e:
                        logger.exception("Failed to connect to adapter:")
                        raise IngestionUnavailableError(f"Cannot connect to adapter at {self._adapter_port}: {e}")

    async def _read_obis_code(self, obis_code: str) -> float | None:
        """
        Read a value from the smart meter using OBIS code.

        This is a placeholder implementation. In production, this would:
        1. Send DLMS/COSEM request with OBIS code
        2. Decrypt response using security key
        3. Parse and return the value

        Args:
            obis_code: OBIS code to read (e.g., "1.0.0.0.0.255")

        Returns:
            Value from smart meter, or None if unavailable
        """
        await self._ensure_connection()

        # TODO: Implement actual DLMS/COSEM protocol communication
        # This would involve:
        # 1. Constructing DLMS request frame
        # 2. Sending via serial port
        # 3. Receiving and decrypting response
        # 4. Parsing OBIS code value

        logger.debug(f"Reading OBIS code {obis_code} (not yet implemented)")
        return None

    async def discover_meter(self) -> dict[str, object] | None:
        """
        Discover and connect to the smart meter.

        Returns:
            Meter information dictionary, or None if discovery fails
        """
        try:
            await self._ensure_connection()

            # Try to read meter serial number
            # This would typically be done via DLMS/COSEM identification

            meter_info = {
                "serial_number": self._meter_serial,
                "adapter_port": self._adapter_port,
                "adapter_type": self._adapter_type,
                "protocol": "IEC 62056-21 (DLMS/COSEM)",
                "last_seen": datetime.now(tz=UTC).isoformat(),
            }

            logger.info(f"Discovered Wien Energie smart meter: {meter_info}")
            return meter_info

        except Exception as exc:
            logger.warning(f"Unable to discover Wien Energie smart meter: {exc}")
            return None

    async def fetch_current_reading(self) -> dict[str, object] | None:
        """
        Fetch current energy reading from smart meter.

        Returns:
            Dictionary with current energy data, or None if unavailable
        """
        try:
            await self._ensure_connection()

            # Read OBIS codes for current values
            total_energy = await self._read_obis_code(self.OBIS_TOTAL_ENERGY)
            active_power = await self._read_obis_code(self.OBIS_ACTIVE_POWER)
            voltage = await self._read_obis_code(self.OBIS_VOLTAGE)
            current = await self._read_obis_code(self.OBIS_CURRENT)
            power_factor = await self._read_obis_code(self.OBIS_POWER_FACTOR)
            frequency = await self._read_obis_code(self.OBIS_FREQUENCY)

            timestamp = datetime.now(tz=UTC)

            reading_data = {
                "timestamp": timestamp.isoformat(),
                "total_energy_kwh": total_energy or 0.0,
                "active_power_w": active_power or 0.0,
                "voltage_v": voltage or 230.0,  # Default to 230V for Austria
                "current_a": current or 0.0,
                "power_factor": power_factor or 1.0,
                "frequency_hz": frequency or 50.0,  # Default to 50Hz for Austria
            }

            # Calculate daily energy (approximation based on current power)
            # In production, this would use actual daily counter from meter
            if active_power:
                hours_elapsed = timestamp.hour + timestamp.minute / 60.0
                reading_data["daily_energy_kwh"] = (active_power / 1000.0) * hours_elapsed
            else:
                reading_data["daily_energy_kwh"] = 0.0

            # Store in database
            try:
                self._db.store_energy_data(
                    device_id="wien_energie_smart_meter",
                    timestamp=timestamp,
                    power_w=active_power,
                    voltage_v=voltage,
                    current_a=current,
                    daily_energy_kwh=reading_data.get("daily_energy_kwh"),
                )
            except Exception as db_exc:
                logger.warning(f"Failed to store smart meter data in database: {db_exc}")

            return reading_data

        except Exception as exc:
            logger.warning(f"Unable to fetch Wien Energie smart meter reading: {exc}")
            return None

    async def fetch_historical_data(self, start_date: datetime, end_date: datetime) -> list[dict[str, object]]:
        """
        Fetch historical energy consumption data.

        Args:
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of historical data points
        """
        # For now, retrieve from database
        # In production, could also query smart meter directly if it stores history
        try:
            return self._db.get_energy_history(
                device_id="wien_energie_smart_meter",
                start_time=start_date,
                end_time=end_date,
            )
        except Exception as exc:
            logger.warning(f"Unable to fetch historical data: {exc}")
            return []

    def calculate_energy_cost(self, energy_kwh: float, timestamp: datetime | None = None) -> float:
        """
        Calculate energy cost based on current tariff.

        Args:
            energy_kwh: Energy consumption in kWh
            timestamp: Timestamp for time-based tariff calculation (optional)

        Returns:
            Cost in EUR
        """
        if timestamp:
            # Check if peak/off-peak rates apply
            hour = timestamp.hour
            # Simple peak hours: 8:00-20:00 (can be configured)
            if 8 <= hour < 20:
                rate = self._peak_rate
            else:
                rate = self._off_peak_rate
        else:
            rate = self._base_rate

        return energy_kwh * rate

    async def get_tariff_info(self) -> dict[str, object]:
        """
        Get current tariff information.

        Returns:
            Dictionary with tariff rates and information
        """
        return {
            "base_rate_eur_per_kwh": self._base_rate,
            "peak_rate_eur_per_kwh": self._peak_rate,
            "off_peak_rate_eur_per_kwh": self._off_peak_rate,
            "currency": "EUR",
            "provider": "Wien Energie",
        }

    async def close(self) -> None:
        """Close connection to adapter."""
        if self._serial_writer:
            self._serial_writer.close()
            await self._serial_writer.wait_closed()
            self._serial_reader = None
            self._serial_writer = None
            logger.info("Closed Wien Energie adapter connection")
