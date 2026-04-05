"""
Open-Meteo Weather API Client

Free weather API - no API key required!
Provides external weather data for any location.
https://open-meteo.com/
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from ..utils import get_logger

logger = get_logger(__name__)

# Vienna coordinates
VIENNA_LAT = 48.2082
VIENNA_LON = 16.3738


@dataclass
class ExternalWeather:
    """External weather data."""

    location: str
    latitude: float
    longitude: float
    temperature: float  # Celsius
    humidity: int  # Percentage
    pressure: float  # hPa
    wind_speed: float  # km/h
    wind_direction: int  # degrees
    weather_code: int  # WMO weather code
    weather_description: str
    cloud_cover: int  # percentage
    precipitation: float  # mm
    is_day: bool
    timestamp: float


# WMO Weather interpretation codes
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class OpenMeteoClient:
    """Client for Open-Meteo free weather API."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # Add timeout to prevent DNS hangs
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_current_weather(
        self,
        latitude: float = VIENNA_LAT,
        longitude: float = VIENNA_LON,
        location_name: str = "Vienna, Austria",
    ) -> ExternalWeather | None:
        """Get current weather for a location."""
        try:
            session = await self._get_session()

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,weather_code,cloud_cover,precipitation,is_day",
                "timezone": "Europe/Vienna",
            }

            # Use session's built-in timeout (configured in _get_session)
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Open-Meteo API error: {resp.status}")
                    return None

                data = await resp.json()
                current = data.get("current", {})

                weather_code = current.get("weather_code", 0)

                return ExternalWeather(
                    location=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    temperature=current.get("temperature_2m", 0),
                    humidity=int(current.get("relative_humidity_2m", 0)),
                    pressure=current.get("surface_pressure", 0),
                    wind_speed=current.get("wind_speed_10m", 0),
                    wind_direction=int(current.get("wind_direction_10m", 0)),
                    weather_code=weather_code,
                    weather_description=WMO_CODES.get(weather_code, "Unknown"),
                    cloud_cover=int(current.get("cloud_cover", 0)),
                    precipitation=current.get("precipitation", 0),
                    is_day=bool(current.get("is_day", 1)),
                    timestamp=time.time(),
                )

        except Exception:
            logger.exception("Failed to fetch Open-Meteo weather")
            return None

    async def get_forecast(
        self, latitude: float = VIENNA_LAT, longitude: float = VIENNA_LON, days: int = 7
    ) -> list[dict[str, Any]]:
        """Get weather forecast for upcoming days."""
        try:
            session = await self._get_session()

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max",
                "timezone": "Europe/Vienna",
                "forecast_days": days,
            }

            # Use session's built-in timeout (configured in _get_session)
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Open-Meteo forecast API error: {resp.status}")
                    return []

                data = await resp.json()
                daily = data.get("daily", {})

                forecast = []
                dates = daily.get("time", [])
                for i, date in enumerate(dates):
                    weather_code = (
                        daily.get("weather_code", [])[i]
                        if i < len(daily.get("weather_code", []))
                        else 0
                    )
                    forecast.append(
                        {
                            "date": date,
                            "temp_max": daily.get("temperature_2m_max", [])[i]
                            if i < len(daily.get("temperature_2m_max", []))
                            else None,
                            "temp_min": daily.get("temperature_2m_min", [])[i]
                            if i < len(daily.get("temperature_2m_min", []))
                            else None,
                            "precipitation": daily.get("precipitation_sum", [])[i]
                            if i < len(daily.get("precipitation_sum", []))
                            else 0,
                            "weather_code": weather_code,
                            "weather_description": WMO_CODES.get(weather_code, "Unknown"),
                            "wind_speed_max": daily.get("wind_speed_10m_max", [])[i]
                            if i < len(daily.get("wind_speed_10m_max", []))
                            else 0,
                        }
                    )

                return forecast

        except Exception:
            logger.exception("Failed to fetch Open-Meteo forecast")
            return []


# Global client instance
openmeteo_client = OpenMeteoClient()
