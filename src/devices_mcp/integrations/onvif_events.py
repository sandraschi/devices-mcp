"""ONVIF event subscription for motion detection notifications."""

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Store active event subscriptions
_subscriptions: Dict[str, "ONVIFEventSubscription"] = {}
_event_callbacks: List[Callable] = []


class ONVIFEventSubscription:
    """Manages ONVIF PullPointSubscription for a camera."""

    def __init__(self, camera_id: str, host: str, port: int, username: str, password: str):
        self.camera_id = camera_id
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._camera = None
        self._events_service = None
        self._pullpoint = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_event_time: Optional[datetime] = None

    async def start(self) -> bool:
        """Start subscribing to ONVIF events."""
        try:
            from onvif import ONVIFCamera

            # Connect to camera
            loop = asyncio.get_event_loop()
            self._camera = await loop.run_in_executor(
                None, lambda: ONVIFCamera(self.host, self.port, self.username, self.password)
            )

            # Create events service
            self._events_service = await loop.run_in_executor(
                None, self._camera.create_events_service
            )

            # Create PullPointSubscription
            try:
                self._pullpoint = await loop.run_in_executor(None, self._create_pullpoint)
                logger.info("ONVIF event subscription created for %s", self.camera_id)
            except Exception as e:
                logger.warning("Camera %s may not support ONVIF events: %s", self.camera_id, e)
                return False

            # Start polling task
            self._running = True
            self._task = asyncio.create_task(self._poll_events())
            return True

        except Exception:
            logger.exception("Failed to start ONVIF event subscription for %s", self.camera_id)
            return False

    def _create_pullpoint(self):
        """Create PullPointSubscription (runs in executor)."""
        # Create subscription request
        req = self._events_service.create_type("CreatePullPointSubscription")
        req.InitialTerminationTime = "PT60S"  # 60 second timeout
        return self._events_service.CreatePullPointSubscription(req)

    async def stop(self):
        """Stop event subscription."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        logger.info("ONVIF event subscription stopped for %s", self.camera_id)

    async def _poll_events(self):
        """Poll for ONVIF events in a loop."""
        while self._running:
            try:
                loop = asyncio.get_event_loop()

                # Pull messages
                messages = await loop.run_in_executor(None, self._pull_messages)

                # Process events
                if messages:
                    await self._process_messages(messages)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Event poll error for %s: %s", self.camera_id, e)

            # Wait before next poll
            await asyncio.sleep(1)

    def _pull_messages(self):
        """Pull messages from subscription (runs in executor)."""
        if not self._pullpoint:
            return None

        try:
            # Get pull point service
            pullpoint_service = self._camera.create_pullpoint_service()

            # Pull messages
            req = pullpoint_service.create_type("PullMessages")
            req.Timeout = "PT5S"  # 5 second timeout
            req.MessageLimit = 10

            return pullpoint_service.PullMessages(req)
        except Exception:
            return None

    async def _process_messages(self, response):
        """Process ONVIF event messages."""
        if not hasattr(response, "NotificationMessage"):
            return

        for msg in response.NotificationMessage:
            try:
                # Extract event data
                event_data = self._parse_event(msg)
                if event_data:
                    # Notify callbacks
                    await self._notify_event(event_data)
            except Exception as e:
                logger.debug("Failed to parse event: %s", e)

    def _parse_event(self, msg) -> Optional[Dict]:
        """Parse ONVIF notification message."""
        try:
            # Check for motion detection event
            topic = str(getattr(msg, "Topic", {}).get("_value_1", ""))

            if "Motion" in topic or "VideoAnalytics" in topic or "CellMotion" in topic:
                # Motion event detected
                event_data = {
                    "camera_id": self.camera_id,
                    "event_type": "motion",
                    "timestamp": datetime.now().isoformat(),
                    "topic": topic,
                    "source": "onvif",
                }

                # Try to extract more details
                message = getattr(msg, "Message", None)
                if message:
                    data = getattr(message, "Data", None)
                    if data:
                        items = getattr(data, "SimpleItem", [])
                        for item in items:
                            name = getattr(item, "Name", "")
                            value = getattr(item, "Value", "")
                            if name == "IsMotion":
                                event_data["is_motion"] = value.lower() == "true"
                            elif name == "State":
                                event_data["state"] = value

                return event_data

            return None
        except Exception:
            return None

    async def _notify_event(self, event_data: Dict):
        """Notify all registered callbacks of an event."""
        self._last_event_time = datetime.now()

        logger.info("🎬 Motion detected on %s!", self.camera_id)

        for callback in _event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception:
                logger.exception("Event callback error")


# Module-level functions


def register_event_callback(callback: Callable):
    """Register a callback to be notified of camera events."""
    if callback not in _event_callbacks:
        _event_callbacks.append(callback)


def unregister_event_callback(callback: Callable):
    """Unregister an event callback."""
    if callback in _event_callbacks:
        _event_callbacks.remove(callback)


async def subscribe_to_camera(
    camera_id: str, host: str, port: int, username: str, password: str
) -> bool:
    """Subscribe to motion events from a camera."""
    if camera_id in _subscriptions:
        logger.warning("Already subscribed to %s", camera_id)
        return True

    subscription = ONVIFEventSubscription(camera_id, host, port, username, password)
    success = await subscription.start()

    if success:
        _subscriptions[camera_id] = subscription
        return True

    return False


async def unsubscribe_from_camera(camera_id: str):
    """Unsubscribe from camera events."""
    if camera_id in _subscriptions:
        await _subscriptions[camera_id].stop()
        del _subscriptions[camera_id]


async def get_subscription_status() -> Dict:
    """Get status of all event subscriptions."""
    return {
        "subscriptions": [
            {
                "camera_id": sub.camera_id,
                "running": sub._running,
                "last_event": sub._last_event_time.isoformat() if sub._last_event_time else None,
            }
            for sub in _subscriptions.values()
        ],
        "callback_count": len(_event_callbacks),
    }


# Recent events storage
_recent_events: List[Dict] = []
MAX_RECENT_EVENTS = 100


async def _store_event(event_data: Dict):
    """Store event in recent events list."""
    _recent_events.insert(0, event_data)
    if len(_recent_events) > MAX_RECENT_EVENTS:
        _recent_events.pop()


def get_recent_events(camera_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Get recent motion events."""
    events = _recent_events
    if camera_id:
        events = [e for e in events if e.get("camera_id") == camera_id]
    return events[:limit]


# Auto-register storage callback
register_event_callback(_store_event)
