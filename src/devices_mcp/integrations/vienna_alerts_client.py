"""
Vienna Public Alerts Client

Fetches emergency alerts from multiple Austrian/Vienna sources:
- GeoSphere Austria (ZAMG) - Weather warnings
- Meteoalarm - European weather alerts
- Vienna-specific sources

No API key required for most sources.
"""

from __future__ import annotations

import asyncio
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp
import certifi

from ..utils import get_logger

# Note: Meteoalarm is a trusted EU source; for untrusted XML consider defusedxml

logger = get_logger(__name__)

# Vienna region codes
VIENNA_REGION = "Wien"
VIENNA_REGION_CODE = "AT009"  # Meteoalarm region code for Vienna


class AlertSeverity(Enum):
    """Alert severity levels (Meteoalarm standard)."""

    UNKNOWN = "unknown"
    MINOR = "minor"  # Yellow - Be aware
    MODERATE = "moderate"  # Orange - Be prepared
    SEVERE = "severe"  # Red - Take action
    EXTREME = "extreme"  # Purple/Dark red - Extreme danger


class AlertType(Enum):
    """Types of alerts."""

    WEATHER = "weather"
    AIR_QUALITY = "air_quality"
    FLOOD = "flood"
    FIRE = "fire"
    WIND = "wind"
    STORM = "storm"
    RAIN = "rain"
    SNOW = "snow"
    ICE = "ice"
    FOG = "fog"
    HEAT = "heat"
    COLD = "cold"
    THUNDERSTORM = "thunderstorm"
    AVALANCHE = "avalanche"
    OTHER = "other"


# Map GeoSphere warning types to AlertType
GEOSPHERE_TYPE_MAP = {
    "wind": AlertType.WIND,
    "storm": AlertType.STORM,
    "rain": AlertType.RAIN,
    "snow": AlertType.SNOW,
    "ice": AlertType.ICE,
    "fog": AlertType.FOG,
    "heat": AlertType.HEAT,
    "cold": AlertType.COLD,
    "thunderstorm": AlertType.THUNDERSTORM,
    "gewitter": AlertType.THUNDERSTORM,
    "regen": AlertType.RAIN,
    "schnee": AlertType.SNOW,
    "glatteis": AlertType.ICE,
    "nebel": AlertType.FOG,
    "hitze": AlertType.HEAT,
    "kälte": AlertType.COLD,
    "frost": AlertType.COLD,
    "sturm": AlertType.STORM,
    "orkan": AlertType.STORM,
}

# Severity color mapping for UI
SEVERITY_COLORS = {
    AlertSeverity.UNKNOWN: "#9CA3AF",  # Gray
    AlertSeverity.MINOR: "#FCD34D",  # Yellow
    AlertSeverity.MODERATE: "#FB923C",  # Orange
    AlertSeverity.SEVERE: "#EF4444",  # Red
    AlertSeverity.EXTREME: "#7C3AED",  # Purple
}

SEVERITY_ICONS = {
    AlertSeverity.UNKNOWN: "?",
    AlertSeverity.MINOR: "!",
    AlertSeverity.MODERATE: "!!",
    AlertSeverity.SEVERE: "!!!",
    AlertSeverity.EXTREME: "!!!!",
}


@dataclass
class Alert:
    """Represents a single alert/warning."""

    id: str
    source: str  # "geosphere", "meteoalarm", etc.
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    region: str
    start_time: datetime | None
    end_time: datetime | None
    issued_time: datetime
    raw_data: dict = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if alert is currently active."""
        now = datetime.now()
        if self.start_time and now < self.start_time:
            return False
        return not (self.end_time and now > self.end_time)

    @property
    def severity_color(self) -> str:
        """Get color for UI display."""
        return SEVERITY_COLORS.get(self.severity, SEVERITY_COLORS[AlertSeverity.UNKNOWN])

    @property
    def severity_icon(self) -> str:
        """Get icon for UI display."""
        return SEVERITY_ICONS.get(self.severity, SEVERITY_ICONS[AlertSeverity.UNKNOWN])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source": self.source,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "severity_color": self.severity_color,
            "severity_icon": self.severity_icon,
            "title": self.title,
            "description": self.description,
            "region": self.region,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "issued_time": self.issued_time.isoformat(),
            "is_active": self.is_active,
        }


class ViennaAlertsClient:
    """Client for fetching Vienna/Austria emergency alerts."""

    # GeoSphere Austria (formerly ZAMG) endpoints
    # NOTE: Old zamg.ac.at URLs are broken (SSL cert mismatch after rebrand)
    # Trying new geosphere.at domain first, falling back to disabled if both fail
    GEOSPHERE_WARNINGS_URL = "https://warnungen.zamg.at/wsapp/api/getWarningsForRegion"
    GEOSPHERE_ALL_WARNINGS_URL = "https://warnungen.zamg.at/wsapp/api/getWarnings"
    GEOSPHERE_ENABLED = False  # Disabled - API endpoints no longer work after GeoSphere rebrand

    # Meteoalarm CAP feed (primary source - always works)
    METEOALARM_ATOM_URL = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-austria"

    # Cache settings
    CACHE_TTL = 300  # 5 minutes

    def __init__(self, regions: list[str] | None = None):
        """Initialize the client.

        Args:
            regions: List of regions to monitor (default: ["Wien"])
        """
        self.regions = regions or ["Wien"]
        self._cache: dict[str, Any] = {}
        self._cache_time: float = 0
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper SSL context."""
        if self._session is None or self._session.closed:
            # Create SSL context with certifi certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=connector,
            )
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_all_alerts(self, use_cache: bool = True) -> list[Alert]:
        """Fetch alerts from all sources.

        Args:
            use_cache: Whether to use cached results if available

        Returns:
            List of active alerts sorted by severity
        """
        # Check cache
        if use_cache and self._cache and (time.time() - self._cache_time) < self.CACHE_TTL:
            return self._cache.get("alerts", [])

        alerts = []

        # Fetch from all available sources in parallel
        tasks = [self._fetch_meteoalarm_alerts()]  # Primary source (always enabled)

        # GeoSphere is disabled due to API endpoint changes after 2024 rebrand
        if self.GEOSPHERE_ENABLED:
            tasks.append(self._fetch_geosphere_alerts())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.exception("Error fetching alerts", exc_info=result)
            elif result:
                alerts.extend(result)

        # Filter to active alerts only and sort by severity
        active_alerts = [a for a in alerts if a.is_active]
        active_alerts.sort(key=lambda a: list(AlertSeverity).index(a.severity), reverse=True)

        # Update cache
        self._cache["alerts"] = active_alerts
        self._cache_time = time.time()

        logger.info(f"Fetched {len(active_alerts)} active alerts from {len(tasks)} sources")
        return active_alerts

    async def _fetch_geosphere_alerts(self) -> list[Alert]:
        """Fetch alerts from GeoSphere Austria (ZAMG)."""
        alerts = []

        try:
            session = await self._get_session()

            # Fetch all warnings
            async with session.get(self.GEOSPHERE_ALL_WARNINGS_URL) as response:
                if response.status != 200:
                    logger.warning(f"GeoSphere API returned {response.status}")
                    return alerts

                data = await response.json()

                # GeoSphere returns a structure with warnings per region
                if isinstance(data, dict):
                    warnings = data.get("warnings", data.get("warnungen", []))
                    if isinstance(warnings, dict):
                        # Warnings might be keyed by region
                        for region_key, region_warnings in warnings.items():
                            if any(
                                r.lower() in region_key.lower() for r in self.regions
                            ) and isinstance(region_warnings, list):
                                for w in region_warnings:
                                    alert = self._parse_geosphere_warning(w, region_key)
                                    if alert:
                                        alerts.append(alert)
                    elif isinstance(warnings, list):
                        for w in warnings:
                            region = w.get("region", w.get("bundesland", ""))
                            if any(r.lower() in region.lower() for r in self.regions):
                                alert = self._parse_geosphere_warning(w, region)
                                if alert:
                                    alerts.append(alert)
                elif isinstance(data, list):
                    for w in data:
                        region = w.get("region", w.get("bundesland", "Wien"))
                        if any(r.lower() in region.lower() for r in self.regions):
                            alert = self._parse_geosphere_warning(w, region)
                            if alert:
                                alerts.append(alert)

        except aiohttp.ClientError as e:
            logger.warning(f"Network error fetching GeoSphere alerts: {e}")
        except Exception:
            logger.exception("Error parsing GeoSphere alerts")

        logger.debug(f"GeoSphere: {len(alerts)} alerts for regions {self.regions}")
        return alerts

    def _parse_geosphere_warning(self, data: dict, region: str) -> Alert | None:
        """Parse a GeoSphere warning into an Alert object."""
        try:
            # Extract warning type
            warn_type = data.get("type", data.get("warntyp", "other")).lower()
            alert_type = GEOSPHERE_TYPE_MAP.get(warn_type, AlertType.WEATHER)

            # Extract severity (GeoSphere uses levels 1-4 or colors)
            level = data.get("level", data.get("stufe", data.get("warnstufe", 1)))
            if isinstance(level, str):
                level_map = {"gelb": 1, "orange": 2, "rot": 3, "violett": 4}
                level = level_map.get(level.lower(), 1)

            severity_map = {
                1: AlertSeverity.MINOR,
                2: AlertSeverity.MODERATE,
                3: AlertSeverity.SEVERE,
                4: AlertSeverity.EXTREME,
            }
            severity = severity_map.get(level, AlertSeverity.MINOR)

            # Parse times
            start_str = data.get("start", data.get("von", data.get("begin")))
            end_str = data.get("end", data.get("bis", data.get("ende")))
            issued_str = data.get("issued", data.get("ausgegeben", data.get("erstellt")))

            start_time = self._parse_datetime(start_str) if start_str else None
            end_time = self._parse_datetime(end_str) if end_str else None
            issued_time = self._parse_datetime(issued_str) if issued_str else datetime.now()

            # Build title and description
            title = data.get("title", data.get("titel", f"{warn_type.title()} Warning"))
            description = data.get("text", data.get("beschreibung", data.get("description", "")))

            return Alert(
                id=f"geosphere_{data.get('id', hash(f'{warn_type}{start_str}{region}'))}",
                source="geosphere",
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                region=region,
                start_time=start_time,
                end_time=end_time,
                issued_time=issued_time,
                raw_data=data,
            )
        except Exception:
            logger.exception("Failed to parse GeoSphere warning")
            return None

    async def _fetch_meteoalarm_alerts(self) -> list[Alert]:
        """Fetch alerts from Meteoalarm (European weather warnings)."""
        alerts = []

        try:
            session = await self._get_session()

            async with session.get(self.METEOALARM_ATOM_URL) as response:
                if response.status != 200:
                    logger.warning(f"Meteoalarm API returned {response.status}")
                    return alerts

                text = await response.text()

                # Parse Atom/XML feed (Meteoalarm is a trusted EU government source)
                root = ET.fromstring(text)  # noqa: S314

                # Define namespaces
                ns = {
                    "atom": "http://www.w3.org/2005/Atom",
                    "cap": "urn:oasis:names:tc:emergency:cap:1.2",
                }

                # Find all entry elements
                entries = root.findall(".//atom:entry", ns)
                if not entries:
                    # Try without namespace
                    entries = root.findall(".//entry")

                for entry in entries:
                    alert = self._parse_meteoalarm_entry(entry, ns)
                    if alert and any(r.lower() in alert.region.lower() for r in self.regions):
                        alerts.append(alert)

        except aiohttp.ClientError as e:
            logger.warning(f"Network error fetching Meteoalarm alerts: {e}")
        except ET.ParseError:
            logger.warning("Failed to parse Meteoalarm XML feed")
        except Exception:
            logger.exception("Error fetching Meteoalarm alerts")

        logger.debug(f"Meteoalarm: {len(alerts)} alerts for regions {self.regions}")
        return alerts

    def _parse_meteoalarm_entry(self, entry: ET.Element, ns: dict) -> Alert | None:
        """Parse a Meteoalarm Atom entry into an Alert object."""
        try:
            # Helper to find elements with or without namespace
            def find_text(element: ET.Element, tag: str, default: str = "") -> str:
                elem = element.find(f"atom:{tag}", ns)
                if elem is None:
                    elem = element.find(tag)
                return elem.text if elem is not None and elem.text else default

            title = find_text(entry, "title", "Weather Alert")
            summary = find_text(entry, "summary", "")
            entry_id = find_text(entry, "id", str(hash(title)))
            updated = find_text(entry, "updated")

            # Note: CAP info available at entry.find(".//cap:info", ns) for future use

            # Determine severity from title or content
            severity = AlertSeverity.MINOR
            title_lower = title.lower()
            if "extreme" in title_lower or "rot" in title_lower or "red" in title_lower:
                severity = AlertSeverity.SEVERE
            elif "severe" in title_lower or "orange" in title_lower:
                severity = AlertSeverity.MODERATE
            elif "moderate" in title_lower or "gelb" in title_lower or "yellow" in title_lower:
                severity = AlertSeverity.MINOR

            # Determine alert type
            alert_type = AlertType.WEATHER
            for type_keyword, atype in GEOSPHERE_TYPE_MAP.items():
                if type_keyword in title_lower or type_keyword in summary.lower():
                    alert_type = atype
                    break

            # Extract region - usually in title like "Austria - Wien - ..."
            region = "Wien"
            if "Wien" in title or "Vienna" in title:
                region = "Wien"
            elif " - " in title:
                parts = title.split(" - ")
                if len(parts) > 1:
                    region = parts[1].strip()

            issued_time = self._parse_datetime(updated) if updated else datetime.now()

            return Alert(
                id=f"meteoalarm_{hash(entry_id)}",
                source="meteoalarm",
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=summary,
                region=region,
                start_time=None,  # Meteoalarm doesn't always provide this
                end_time=None,
                issued_time=issued_time,
                raw_data={"title": title, "summary": summary},
            )
        except Exception:
            logger.exception("Failed to parse Meteoalarm entry")
            return None

    def _parse_datetime(self, dt_string: str) -> datetime | None:
        """Parse various datetime string formats."""
        if not dt_string:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_string.strip(), fmt)
            except ValueError:
                continue

        logger.debug(f"Could not parse datetime: {dt_string}")
        return None

    async def get_alert_summary(self) -> dict[str, Any]:
        """Get a summary of current alerts for dashboard display."""
        alerts = await self.get_all_alerts()
        return summarize_alerts(alerts)


def summarize_alerts(alerts: list[Alert]) -> dict[str, Any]:
    """Build dashboard summary dict from an alert list (Vienna + indoor air, etc.)."""
    # Count by severity
    severity_counts = {s.value: 0 for s in AlertSeverity}
    for alert in alerts:
        severity_counts[alert.severity.value] += 1

    # Find highest severity
    highest_severity = AlertSeverity.UNKNOWN
    for alert in alerts:
        if list(AlertSeverity).index(alert.severity) > list(AlertSeverity).index(highest_severity):
            highest_severity = alert.severity

    return {
        "total_alerts": len(alerts),
        "highest_severity": highest_severity.value,
        "highest_severity_color": SEVERITY_COLORS[highest_severity],
        "highest_severity_icon": SEVERITY_ICONS[highest_severity],
        "severity_counts": severity_counts,
        "alerts": [a.to_dict() for a in alerts[:5]],  # Top 5 alerts
        "last_updated": datetime.now().isoformat(),
        "status": "ok"
        if not alerts
        else "warning"
        if highest_severity in [AlertSeverity.MINOR, AlertSeverity.MODERATE]
        else "danger",
    }


# Global client instance
alerts_client = ViennaAlertsClient()
