"""iKettle smart kettle integration client."""

import logging
from typing import Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class IKettleClient:
    """Client for Smarter iKettle smart kettle."""

    def __init__(self, host: str, username: str = None, password: str = None):
        """Initialize iKettle client.

        Args:
            host: IP address or hostname of the iKettle
            username: Optional username (usually not required)
            password: Optional password (usually not required)
        """
        self.host = host
        self.username = username
        self.password = password
        self.base_url = f"http://{host}/smarter/api/v2"
        self.session = None
        self._last_status = {}
        self._connected = False

    async def connect(self) -> bool:
        """Establish connection to the iKettle."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            # Test connection by getting status
            status = await self.get_status()
            if status:
                self._connected = True
                logger.info(f"Connected to iKettle at {self.host}")
                return True
            logger.warning(f"Failed to connect to iKettle at {self.host}")
            return False

        except Exception:
            logger.exception("Error connecting to iKettle:")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from the iKettle."""
        if self.session:
            await self.session.close()
            self.session = None
        self._connected = False

    async def _make_request(
        self, endpoint: str, method: str = "GET", data: Dict = None
    ) -> Optional[Dict]:
        """Make HTTP request to iKettle API."""
        if not self.session:
            await self.connect()
            if not self.session:
                return None

        url = f"{self.base_url}/{endpoint}"

        try:
            if method == "GET":
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.error(f"iKettle API error: {response.status} - {await response.text()}")
                    return None
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    if response.status in [200, 204]:
                        return await response.json() if response.status == 200 else {}
                    logger.error(f"iKettle API error: {response.status} - {await response.text()}")
                    return None

        except Exception:
            logger.exception("Error making request to iKettle:")
            return None

    async def get_status(self) -> Optional[Dict]:
        """Get current kettle status."""
        try:
            status = await self._make_request("status")
            if status:
                self._last_status = status
                return status
            return None

        except Exception:
            logger.exception("Error getting iKettle status:")
            return None

    async def boil(self, temperature: int = 100) -> bool:
        """Start boiling water to specified temperature (Celsius)."""
        try:
            # Convert Celsius to Fahrenheit for iKettle API
            temp_f = int((temperature * 9 / 5) + 32)

            # Ensure temperature is within iKettle range (68°F to 212°F)
            temp_f = max(68, min(212, temp_f))

            data = {"temperature": temp_f}
            result = await self._make_request("boil", method="POST", data=data)

            if result is not None:
                logger.info(f"iKettle: Started boiling to {temperature}°C ({temp_f}°F)")
                return True
            return False

        except Exception:
            logger.exception("Error starting boil:")
            return False

    async def keep_warm(self, temperature: int = 95, duration: int = 30) -> bool:
        """Set keep warm mode."""
        try:
            # Convert to Fahrenheit
            temp_f = int((temperature * 9 / 5) + 32)
            temp_f = max(68, min(212, temp_f))

            data = {
                "temperature": temp_f,
                "duration": duration,  # minutes
            }

            result = await self._make_request("keepwarm", method="POST", data=data)

            if result is not None:
                logger.info(f"iKettle: Set keep warm to {temperature}°C for {duration} minutes")
                return True
            return False

        except Exception:
            logger.exception("Error setting keep warm:")
            return False

    async def stop(self) -> bool:
        """Stop current operation."""
        try:
            result = await self._make_request("stop", method="POST")

            if result is not None:
                logger.info("iKettle: Stopped current operation")
                return True
            return False

        except Exception:
            logger.exception("Error stopping iKettle:")
            return False

    async def set_mode(self, mode: str) -> bool:
        """Set kettle mode (wake_up, home, formula)."""
        try:
            valid_modes = ["wake_up", "home", "formula"]
            if mode not in valid_modes:
                logger.error(f"Invalid mode: {mode}. Must be one of: {valid_modes}")
                return False

            data = {"mode": mode}
            result = await self._make_request("mode", method="POST", data=data)

            if result is not None:
                logger.info(f"iKettle: Set mode to {mode}")
                return True
            return False

        except Exception:
            logger.exception("Error setting mode:")
            return False

    async def schedule_boil(self, temperature: int = 100, delay_minutes: int = 0) -> bool:
        """Schedule a boil operation."""
        try:
            temp_f = int((temperature * 9 / 5) + 32)
            temp_f = max(68, min(212, temp_f))

            data = {"temperature": temp_f, "delay": delay_minutes}

            result = await self._make_request("schedule", method="POST", data=data)

            if result is not None:
                logger.info(
                    f"iKettle: Scheduled boil to {temperature}°C in {delay_minutes} minutes"
                )
                return True
            return False

        except Exception:
            logger.exception("Error scheduling boil:")
            return False

    def get_temperature_celsius(self, temp_f: int) -> float:
        """Convert Fahrenheit to Celsius."""
        return round((temp_f - 32) * 5 / 9, 1)

    def get_temperature_fahrenheit(self, temp_c: int) -> int:
        """Convert Celsius to Fahrenheit."""
        return int((temp_c * 9 / 5) + 32)

    async def get_water_level(self) -> Optional[str]:
        """Get current water level status."""
        status = await self.get_status()
        if status and "water_level" in status:
            return status["water_level"]
        return None

    async def is_boiling(self) -> bool:
        """Check if kettle is currently boiling."""
        status = await self.get_status()
        if status and "state" in status:
            return status["state"] == "boiling"
        return False

    async def get_current_temperature(self) -> Optional[float]:
        """Get current water temperature in Celsius."""
        status = await self.get_status()
        if status and "temperature" in status:
            return self.get_temperature_celsius(status["temperature"])
        return None

    async def get_formatted_status(self) -> Dict:
        """Get formatted status for display."""
        status = await self.get_status()

        if not status:
            return {"connected": False, "error": "Unable to get status"}

        # Convert temperatures to Celsius
        current_temp_c = None
        target_temp_c = None

        if "temperature" in status:
            current_temp_c = self.get_temperature_celsius(status["temperature"])
        if "target_temperature" in status:
            target_temp_c = self.get_temperature_celsius(status["target_temperature"])

        return {
            "connected": True,
            "state": status.get("state", "unknown"),
            "current_temperature_c": current_temp_c,
            "current_temperature_f": status.get("temperature"),
            "target_temperature_c": target_temp_c,
            "target_temperature_f": status.get("target_temperature"),
            "water_level": status.get("water_level", "unknown"),
            "mode": status.get("mode", "unknown"),
            "keep_warm_active": status.get("keep_warm", False),
            "keep_warm_minutes": status.get("keep_warm_minutes", 0),
            "last_updated": status.get("timestamp"),
        }

    async def setup_morning_routine(self, wake_time: str = "07:00", coffee_temp: int = 95) -> Dict:
        """Set up morning coffee routine."""
        try:
            # Calculate delay until wake time
            from datetime import datetime, timedelta

            now = datetime.now()
            wake_hour, wake_minute = map(int, wake_time.split(":"))
            wake_datetime = now.replace(hour=wake_hour, minute=wake_minute, second=0, microsecond=0)

            # If wake time has passed today, schedule for tomorrow
            if wake_datetime <= now:
                wake_datetime += timedelta(days=1)

            delay_minutes = int((wake_datetime - now).total_seconds() / 60)

            # Schedule the boil
            success = await self.schedule_boil(coffee_temp, delay_minutes)

            if success:
                return {
                    "success": True,
                    "message": f"Morning coffee scheduled for {wake_time} (in {delay_minutes} minutes)",
                    "wake_time": wake_time,
                    "coffee_temperature": coffee_temp,
                    "delay_minutes": delay_minutes,
                }
            return {"success": False, "error": "Failed to schedule morning coffee"}

        except Exception as e:
            logger.exception("Error setting up morning routine:")
            return {"success": False, "error": str(e)}
