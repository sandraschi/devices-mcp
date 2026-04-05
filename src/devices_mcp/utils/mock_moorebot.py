"""
Mock Moorebot Scout for Testing

Provides realistic mock data and behaviors for development without hardware.

**Timestamp**: 2025-12-02
**Usage**: Testing, CI/CD, development before hardware arrival
"""

import random
import time
from datetime import datetime
from typing import Dict, List


class MockMoorebotScout:
    """Mock Moorebot Scout robot for testing"""

    def __init__(self):
        self.battery_level = 100
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0
        self.status = "idle"
        self.charging = False
        self.last_move_time = time.time()

    def get_mock_status(self) -> Dict:
        """Generate realistic status data"""
        # Simulate battery drain
        if not self.charging and self.status == "moving":
            self.battery_level = max(0, self.battery_level - 0.5)
        elif self.charging:
            self.battery_level = min(100, self.battery_level + 2.0)

        return {
            "success": True,
            "status": self.status,
            "battery_level": int(self.battery_level),
            "charging": self.charging,
            "position": {
                "x": round(self.x, 2),
                "y": round(self.y, 2),
                "heading": round(self.heading, 1),
                "room": self._get_current_room(),
            },
            "wifi_signal": random.randint(-60, -40),
            "uptime": int(time.time() - self.last_move_time),
            "mock_mode": True,
        }

    def get_mock_sensors(self) -> Dict:
        """Generate realistic sensor data"""
        return {
            "tof_distance": round(random.uniform(0.2, 2.5), 3),
            "light_ch0": random.randint(5000, 60000),
            "light_ch1": random.randint(3000, 50000),
            "imu": {
                "orientation": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": round(random.uniform(-0.1, 0.1), 3),
                    "w": round(random.uniform(0.95, 1.0), 3),
                },
                "angular_velocity": {
                    "x": round(random.uniform(-0.05, 0.05), 4),
                    "y": round(random.uniform(-0.05, 0.05), 4),
                    "z": round(random.uniform(-0.1, 0.1), 4),
                },
                "linear_acceleration": {
                    "x": round(random.uniform(-0.2, 0.2), 3),
                    "y": round(random.uniform(-0.2, 0.2), 3),
                    "z": round(9.81 + random.uniform(-0.1, 0.1), 2),
                },
            },
            "timestamp": datetime.now().isoformat(),
            "mock_mode": True,
        }

    def simulate_movement(self, linear: float, angular: float, duration: float):
        """Simulate robot movement"""
        if duration > 0:
            # Simple physics simulation
            self.x += linear * duration * 0.5  # Rough estimation
            self.heading += angular * duration * 57.3  # rad to deg
            self.heading = self.heading % 360

        self.status = "moving" if (linear != 0 or angular != 0) else "idle"
        self.last_move_time = time.time()

    def simulate_patrol(self, route: str) -> Dict:
        """Simulate patrol behavior"""
        waypoints = self._get_patrol_waypoints(route)
        return {
            "success": True,
            "route": route,
            "waypoints": len(waypoints),
            "estimated_duration": len(waypoints) * 60,
            "current_waypoint": 0,
            "mock_mode": True,
        }

    def simulate_docking(self) -> Dict:
        """Simulate docking attempt (sometimes fails!)"""
        # 70% success rate (realistic based on reports)
        success = random.random() > 0.3

        if success:
            self.status = "charging"
            self.charging = True
            self.x = 0.0
            self.y = 0.0
            return {"success": True, "docking_status": "success", "mock_mode": True}
        return {
            "success": False,
            "error": "Docking failed - alignment issue",
            "suggestion": "Manually place robot on dock or retry",
            "attempts": random.randint(2, 5),
            "mock_mode": True,
        }

    def _get_current_room(self) -> str:
        """Determine room based on position"""
        if -1.0 <= self.x <= 5.0 and -1.0 <= self.y <= 4.0:
            return "living_room"
        if 5.0 < self.x <= 8.0 and -1.0 <= self.y <= 3.0:
            return "bedroom"
        if -1.0 <= self.x <= 3.0 and 4.0 < self.y <= 7.0:
            return "kitchen"
        return "unknown"

    def _get_patrol_waypoints(self, route: str) -> List[Dict]:
        """Get waypoints for patrol route"""
        routes = {
            "default": [
                {"x": 2.0, "y": 2.0, "room": "living_room"},
                {"x": 6.0, "y": 1.5, "room": "bedroom"},
                {"x": 1.0, "y": 5.0, "room": "kitchen"},
                {"x": 0.0, "y": 0.0, "room": "home_base"},
            ],
            "perimeter": [
                {"x": 0.0, "y": 0.0, "room": "home_base"},
                {"x": 5.0, "y": 0.0, "room": "living_room"},
                {"x": 8.0, "y": 0.0, "room": "bedroom"},
                {"x": 8.0, "y": 7.0, "room": "kitchen"},
                {"x": 0.0, "y": 7.0, "room": "living_room"},
                {"x": 0.0, "y": 0.0, "room": "home_base"},
            ],
            "rooms": [
                {"x": 2.5, "y": 2.0, "room": "living_room"},
                {"x": 6.5, "y": 1.5, "room": "bedroom"},
                {"x": 1.5, "y": 5.5, "room": "kitchen"},
                {"x": 0.0, "y": 0.0, "room": "home_base"},
            ],
        }
        return routes.get(route, routes["default"])


# Mock fixtures for pytest
MOCK_STATUS_IDLE = {
    "success": True,
    "status": "idle",
    "battery_level": 85,
    "charging": False,
    "position": {"x": 0.0, "y": 0.0, "heading": 0.0, "room": "living_room"},
    "wifi_signal": -45,
    "uptime": 1200,
    "mock_mode": True,
}

MOCK_STATUS_MOVING = {
    "success": True,
    "status": "moving",
    "battery_level": 82,
    "charging": False,
    "position": {"x": 2.5, "y": 1.2, "heading": 45.0, "room": "living_room"},
    "wifi_signal": -48,
    "uptime": 1250,
    "mock_mode": True,
}

MOCK_STATUS_CHARGING = {
    "success": True,
    "status": "charging",
    "battery_level": 95,
    "charging": True,
    "position": {"x": 0.0, "y": 0.0, "heading": 0.0, "room": "home_base"},
    "wifi_signal": -42,
    "uptime": 3600,
    "mock_mode": True,
}

MOCK_STATUS_LOW_BATTERY = {
    "success": True,
    "status": "idle",
    "battery_level": 18,
    "charging": False,
    "position": {"x": 5.5, "y": 3.2, "heading": 180.0, "room": "bedroom"},
    "wifi_signal": -52,
    "uptime": 7200,
    "mock_mode": True,
}

MOCK_SENSOR_DATA = {
    "tof_distance": 1.235,
    "light_ch0": 45000,
    "light_ch1": 32000,
    "imu": {
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.05, "w": 0.998},
        "angular_velocity": {"x": 0.001, "y": -0.002, "z": 0.015},
        "linear_acceleration": {"x": 0.05, "y": -0.03, "z": 9.78},
    },
    "timestamp": "2025-12-02T10:30:45.123456",
    "mock_mode": True,
}

MOCK_MOVE_SUCCESS = {
    "success": True,
    "linear": 0.3,
    "angular": 0.0,
    "duration": 0.0,
    "mock_mode": True,
}

MOCK_PATROL_SUCCESS = {
    "success": True,
    "route": "default",
    "waypoints": 4,
    "estimated_duration": 240,
    "current_waypoint": 0,
    "mock_mode": True,
}

MOCK_DOCK_SUCCESS = {"success": True, "docking_status": "success", "mock_mode": True}

MOCK_DOCK_FAILURE = {
    "success": False,
    "error": "Docking failed - alignment issue",
    "suggestion": "Manually place robot on dock or retry",
    "attempts": 3,
    "mock_mode": True,
}
