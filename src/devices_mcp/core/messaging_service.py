"""
Messaging Service - Info/Warning/Alarm system with Prometheus/Loki integration.

Structured alerting system designed for:
- Real-time UI notifications
- Prometheus metrics exposition
- Loki structured logging
- Grafana dashboard integration

Message Levels:
- INFO: Informational events (device connected, data updated)
- WARNING: Issues requiring attention (high CO2, device reconnecting)
- ALARM: Critical issues requiring immediate action (device offline, sensor failure)
"""

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class MessageSeverity(StrEnum):
    """Message severity levels."""

    INFO = "info"
    WARNING = "warning"
    ALARM = "alarm"


class MessageCategory(StrEnum):
    """Message categories for filtering."""

    DEVICE_CONNECTION = "device_connection"
    DEVICE_STATUS = "device_status"
    SENSOR_READING = "sensor_reading"
    ENERGY_ALERT = "energy_alert"
    SECURITY_EVENT = "security_event"
    SYSTEM_EVENT = "system_event"
    MEDIA_EVENT = "media_event"


@dataclass
class Message:
    """Alert message with monitoring metadata."""

    id: str
    timestamp: datetime
    severity: MessageSeverity
    category: MessageCategory
    source: str  # Device ID or system component
    title: str
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    ack_timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "acknowledged": self.acknowledged,
            "ack_timestamp": self.ack_timestamp.isoformat() if self.ack_timestamp else None,
        }

    def to_prometheus_labels(self) -> dict[str, str]:
        """Convert to Prometheus label format."""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "source": self.source,
            "device_type": self.details.get("device_type", "unknown"),
        }

    def to_loki_entry(self) -> str:
        """Convert to Loki JSON log entry."""
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "level": self.severity.value.upper(),
                "category": self.category.value,
                "source": self.source,
                "message": f"{self.title}: {self.description}",
                "details": self.details,
                "labels": {
                    "app": "devices_mcp",
                    "severity": self.severity.value,
                    "category": self.category.value,
                    "source": self.source,
                },
            }
        )


class MessagingService:
    """
    Central messaging service for alerts and notifications.

    Features:
    - Three severity levels (info, warning, alarm)
    - In-memory circular buffer (last N messages)
    - Prometheus metrics exposition
    - Loki-compatible structured logging
    - Acknowledgement tracking
    - Filtering by severity, category, source
    """

    def __init__(self, max_messages: int = 1000):
        """
        Initialize messaging service.

        Args:
            max_messages: Max messages to keep in memory (older ones dropped)
        """
        self.messages: deque = deque(maxlen=max_messages)
        self._message_counter = 0
        self._metrics = {"info_count": 0, "warning_count": 0, "alarm_count": 0, "total_count": 0}

        # Prometheus metrics (for future integration)
        self._prom_metrics = {}

    def add_message(
        self,
        severity: MessageSeverity,
        category: MessageCategory,
        source: str,
        title: str,
        description: str,
        details: dict[str, Any] | None = None,
    ) -> Message:
        """
        Add a new message to the system.

        Args:
            severity: Message severity level
            category: Message category
            source: Device ID or component name
            title: Short message title
            description: Detailed description
            details: Additional metadata

        Returns:
            Created message object
        """
        self._message_counter += 1
        msg_id = f"msg_{self._message_counter}_{int(datetime.now().timestamp())}"

        message = Message(
            id=msg_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            source=source,
            title=title,
            description=description,
            details=details or {},
        )

        self.messages.append(message)

        # Update metrics
        self._metrics["total_count"] += 1
        if severity == MessageSeverity.INFO:
            self._metrics["info_count"] += 1
        elif severity == MessageSeverity.WARNING:
            self._metrics["warning_count"] += 1
        elif severity == MessageSeverity.ALARM:
            self._metrics["alarm_count"] += 1

        # Log to standard logging (for Promtail/Loki)
        log_level = (
            logging.INFO
            if severity == MessageSeverity.INFO
            else logging.WARNING
            if severity == MessageSeverity.WARNING
            else logging.ERROR
        )

        logger.log(log_level, message.to_loki_entry())

        return message

    def info(self, category: MessageCategory, source: str, title: str, description: str, **details):
        """Convenience method for INFO messages."""
        return self.add_message(MessageSeverity.INFO, category, source, title, description, details)

    def warning(self, category: MessageCategory, source: str, title: str, description: str, **details):
        """Convenience method for WARNING messages."""
        return self.add_message(MessageSeverity.WARNING, category, source, title, description, details)

    def alarm(self, category: MessageCategory, source: str, title: str, description: str, **details):
        """Convenience method for ALARM messages."""
        return self.add_message(MessageSeverity.ALARM, category, source, title, description, details)

    def get_messages(
        self,
        severity: MessageSeverity | None = None,
        category: MessageCategory | None = None,
        source: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
        acknowledged: bool | None = None,
    ) -> list[Message]:
        """
        Get messages with optional filtering.

        Args:
            severity: Filter by severity
            category: Filter by category
            source: Filter by source device/component
            since: Only messages after this time
            limit: Max messages to return
            acknowledged: Filter by ack status (None = all)

        Returns:
            List of matching messages (newest first)
        """
        filtered = list(self.messages)

        if severity:
            filtered = [m for m in filtered if m.severity == severity]

        if category:
            filtered = [m for m in filtered if m.category == category]

        if source:
            filtered = [m for m in filtered if m.source == source]

        if since:
            filtered = [m for m in filtered if m.timestamp >= since]

        if acknowledged is not None:
            filtered = [m for m in filtered if m.acknowledged == acknowledged]

        # Sort by timestamp desc (newest first)
        filtered.sort(key=lambda m: m.timestamp, reverse=True)

        return filtered[:limit]

    def get_unacknowledged_alarms(self) -> list[Message]:
        """Get all unacknowledged ALARM messages."""
        return self.get_messages(severity=MessageSeverity.ALARM, acknowledged=False)

    def acknowledge_message(self, message_id: str) -> bool:
        """Mark a message as acknowledged."""
        for msg in self.messages:
            if msg.id == message_id:
                msg.acknowledged = True
                msg.ack_timestamp = datetime.now()
                logger.info(f"Message {message_id} acknowledged")
                return True
        return False

    def acknowledge_all(self, severity: MessageSeverity | None = None):
        """Acknowledge all messages, optionally filtered by severity."""
        count = 0
        for msg in self.messages:
            if not msg.acknowledged and (severity is None or msg.severity == severity):
                msg.acknowledged = True
                msg.ack_timestamp = datetime.now()
                count += 1
        logger.info(f"Acknowledged {count} messages")
        return count

    def get_metrics(self) -> dict[str, Any]:
        """Get messaging metrics for Prometheus."""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)

        recent_hour = [m for m in self.messages if m.timestamp >= last_hour]
        recent_day = [m for m in self.messages if m.timestamp >= last_day]

        unacked_alarms = len([m for m in self.messages if m.severity == MessageSeverity.ALARM and not m.acknowledged])

        return {
            # Lifetime counts
            "total_messages": self._metrics["total_count"],
            "info_total": self._metrics["info_count"],
            "warning_total": self._metrics["warning_count"],
            "alarm_total": self._metrics["alarm_count"],
            # Recent activity
            "messages_last_hour": len(recent_hour),
            "messages_last_day": len(recent_day),
            # Current state
            "messages_in_buffer": len(self.messages),
            "unacknowledged_alarms": unacked_alarms,
            # By severity (current buffer)
            "info_current": len([m for m in self.messages if m.severity == MessageSeverity.INFO]),
            "warning_current": len([m for m in self.messages if m.severity == MessageSeverity.WARNING]),
            "alarm_current": len([m for m in self.messages if m.severity == MessageSeverity.ALARM]),
        }

    def export_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns metrics that Prometheus can scrape from /metrics endpoint.
        """
        metrics = self.get_metrics()

        lines = [
            "# HELP tapo_messages_total Total messages by severity",
            "# TYPE tapo_messages_total counter",
            f'tapo_messages_total{{severity="info"}} {metrics["info_total"]}',
            f'tapo_messages_total{{severity="warning"}} {metrics["warning_total"]}',
            f'tapo_messages_total{{severity="alarm"}} {metrics["alarm_total"]}',
            "",
            "# HELP tapo_unacknowledged_alarms Number of unacknowledged alarms",
            "# TYPE tapo_unacknowledged_alarms gauge",
            f"tapo_unacknowledged_alarms {metrics['unacknowledged_alarms']}",
            "",
            "# HELP tapo_messages_last_hour Messages in last hour",
            "# TYPE tapo_messages_last_hour gauge",
            f"tapo_messages_last_hour {metrics['messages_last_hour']}",
            "",
        ]

        return "\n".join(lines)


# Global messaging service instance
_messaging_service: MessagingService | None = None


def get_messaging_service() -> MessagingService:
    """Get or create global messaging service instance."""
    global _messaging_service
    if _messaging_service is None:
        _messaging_service = MessagingService(max_messages=1000)
    return _messaging_service
