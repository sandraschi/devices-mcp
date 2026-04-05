"""
Time series database for storing energy and weather data.

Uses SQLite for simplicity and portability.
"""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TimeSeriesDB:
    """SQLite database for time series data storage."""

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize the time series database.

        Args:
            db_path: Path to SQLite database file. Defaults to 'data/timeseries.db'
        """
        if db_path is None:
            # Default to data/timeseries.db in project root
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "timeseries.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Energy time series table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS energy_timeseries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    power_w REAL,
                    voltage_v REAL,
                    current_a REAL,
                    daily_energy_kwh REAL,
                    monthly_energy_kwh REAL,
                    power_state INTEGER,
                    UNIQUE(device_id, timestamp)
                )
            """)

            # Create index for fast queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_energy_device_timestamp
                ON energy_timeseries(device_id, timestamp)
            """)

            # Weather time series table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_timeseries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id TEXT NOT NULL,
                    module_type TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    temperature_c REAL,
                    humidity_percent REAL,
                    co2_ppm INTEGER,
                    pressure_mbar REAL,
                    noise_db REAL,
                    UNIQUE(station_id, module_type, timestamp)
                )
            """)

            # Create index for fast queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_weather_station_timestamp
                ON weather_timeseries(station_id, module_type, timestamp)
            """)

            conn.commit()
            logger.info(f"Time series database initialized at {self.db_path}")

    def store_energy_data(
        self,
        device_id: str,
        timestamp: datetime,
        power_w: float | None = None,
        voltage_v: float | None = None,
        current_a: float | None = None,
        daily_energy_kwh: float | None = None,
        monthly_energy_kwh: float | None = None,
        power_state: bool | None = None,
    ) -> None:
        """
        Store energy data point.

        Args:
            device_id: Device identifier
            timestamp: Timestamp of the data point
            power_w: Power in watts
            voltage_v: Voltage in volts
            current_a: Current in amps
            daily_energy_kwh: Daily energy in kWh
            monthly_energy_kwh: Monthly energy in kWh
            power_state: Power state (True/False)
        """
        ts = int(timestamp.timestamp())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO energy_timeseries
                (device_id, timestamp, power_w, voltage_v, current_a,
                 daily_energy_kwh, monthly_energy_kwh, power_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    device_id,
                    ts,
                    power_w,
                    voltage_v,
                    current_a,
                    daily_energy_kwh,
                    monthly_energy_kwh,
                    1 if power_state else 0 if power_state is not None else None,
                ),
            )
            conn.commit()

    def store_weather_data(
        self,
        station_id: str,
        module_type: str,
        timestamp: datetime,
        temperature_c: float | None = None,
        humidity_percent: float | None = None,
        co2_ppm: int | None = None,
        pressure_mbar: float | None = None,
        noise_db: float | None = None,
    ) -> None:
        """
        Store weather data point.

        Args:
            station_id: Weather station identifier
            module_type: Module type (indoor, outdoor, etc.)
            timestamp: Timestamp of the data point
            temperature_c: Temperature in Celsius
            humidity_percent: Humidity percentage
            co2_ppm: CO2 level in ppm
            pressure_mbar: Pressure in mbar
            noise_db: Noise level in dB
        """
        ts = int(timestamp.timestamp())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO weather_timeseries
                (station_id, module_type, timestamp, temperature_c, humidity_percent,
                 co2_ppm, pressure_mbar, noise_db)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    station_id,
                    module_type,
                    ts,
                    temperature_c,
                    humidity_percent,
                    co2_ppm,
                    pressure_mbar,
                    noise_db,
                ),
            )
            conn.commit()

    def get_energy_history(
        self,
        device_id: str | None = None,
        hours: int = 24,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get energy history data.

        Args:
            device_id: Device identifier (None for all devices)
            hours: Number of hours to look back (if start_time not provided)
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of data points
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=hours)

        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if device_id:
                cursor.execute(
                    """
                    SELECT * FROM energy_timeseries
                    WHERE device_id = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                """,
                    (device_id, start_ts, end_ts),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM energy_timeseries
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                """,
                    (start_ts, end_ts),
                )

            rows = cursor.fetchall()

            return [
                {
                    "device_id": row["device_id"],
                    "timestamp": row["timestamp"],
                    "power_w": row["power_w"],
                    "voltage_v": row["voltage_v"],
                    "current_a": row["current_a"],
                    "daily_energy_kwh": row["daily_energy_kwh"],
                    "monthly_energy_kwh": row["monthly_energy_kwh"],
                    "power_state": bool(row["power_state"])
                    if row["power_state"] is not None
                    else None,
                }
                for row in rows
            ]

    def get_weather_history(
        self,
        station_id: str,
        module_type: str | None = None,
        data_type: str = "temperature",
        hours: int = 24,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get weather history data.

        Args:
            station_id: Weather station identifier
            module_type: Module type (indoor, outdoor, etc.) or None for all
            data_type: Type of data (temperature, humidity, co2, pressure, noise)
            hours: Number of hours to look back (if start_time not provided)
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            List of data points with timestamp and value
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=hours)

        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        # Map data_type to column name
        column_map = {
            "temperature": "temperature_c",
            "humidity": "humidity_percent",
            "co2": "co2_ppm",
            "pressure": "pressure_mbar",
            "noise": "noise_db",
        }
        value_column = column_map.get(data_type, "temperature_c")
        # value_column is validated against column_map whitelist, safe for SQL

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if module_type:
                cursor.execute(
                    f"""
                    SELECT timestamp, {value_column} as value FROM weather_timeseries
                    WHERE station_id = ? AND module_type = ?
                    AND timestamp >= ? AND timestamp <= ?
                    AND {value_column} IS NOT NULL
                    ORDER BY timestamp ASC
                """,
                    (station_id, module_type, start_ts, end_ts),
                )
            else:
                cursor.execute(
                    f"""
                    SELECT timestamp, {value_column} as value FROM weather_timeseries
                    WHERE station_id = ?
                    AND timestamp >= ? AND timestamp <= ?
                    AND {value_column} IS NOT NULL
                    ORDER BY timestamp ASC
                """,
                    (station_id, start_ts, end_ts),
                )

            rows = cursor.fetchall()

            return [
                {
                    "timestamp": row["timestamp"],
                    "value": row["value"],
                }
                for row in rows
            ]
