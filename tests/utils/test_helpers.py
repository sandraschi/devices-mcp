"""
Comprehensive Test Utilities and Helpers

This module provides extensive utilities for testing the Devices MCP platform,
including test data factories, assertion helpers, performance testing tools,
and integration testing utilities.
"""

import asyncio
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, TypeVar
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from devices_mcp.core.models import TapoCameraConfig

# Type variables for generic functions
T = TypeVar("T")
ModelType = TypeVar("ModelType", bound=BaseModel)


# ============================================================================
# TEST DATA FACTORIES
# ============================================================================


class TestDataFactory:
    """Factory for generating test data."""

    @staticmethod
    def create_camera_config(
        host: str = "192.168.1.100",
        username: str = "testuser",
        password: str = "testpass",
        **overrides,
    ) -> TapoCameraConfig:
        """Create a test camera configuration."""
        config_data = {
            "host": host,
            "port": 443,
            "username": username,
            "password": password,
            "use_https": True,
            "verify_ssl": False,
            "timeout": 5,
            **overrides,
        }
        return TapoCameraConfig(**config_data)

    @staticmethod
    def create_energy_device(
        device_id: str | None = None,
        device_type: str = "tapo_p115",
        name: str | None = None,
        **overrides,
    ) -> dict[str, Any]:
        """Create test energy device data."""
        return {
            "device_id": device_id or f"{device_type}_{uuid.uuid4().hex[:8]}",
            "name": name or f"Test {device_type.title()}",
            "type": device_type,
            "power_state": True,
            "current_power": 45.2,
            "voltage": 230.1,
            "current": 0.196,
            "daily_energy": 2.34,
            "monthly_energy": 68.9,
            "daily_cost": 0.45,
            "monthly_cost": 13.2,
            "last_seen": "2023-01-01T12:00:00Z",
            **overrides,
        }

    @staticmethod
    def create_motion_event(
        camera_id: str = "test_camera",
        event_type: str = "motion_detected",
        confidence: float = 0.95,
        **overrides,
    ) -> dict[str, Any]:
        """Create test motion event data."""
        return {
            "event_id": f"motion_{uuid.uuid4().hex[:8]}",
            "camera_id": camera_id,
            "timestamp": "2023-01-01T12:00:00Z",
            "event_type": event_type,
            "confidence": confidence,
            "regions": [[100, 100, 200, 200]],
            "metadata": {"brightness": 0.7, "motion_strength": 0.8},
            **overrides,
        }

    @staticmethod
    def create_weather_data(
        station_id: str = "weather_test",
        temperature: float = 22.5,
        humidity: float = 65.0,
        **overrides,
    ) -> dict[str, Any]:
        """Create test weather station data."""
        return {
            "station_id": station_id,
            "timestamp": "2023-01-01T12:00:00Z",
            "temperature": temperature,
            "humidity": humidity,
            "pressure": 1013.25,
            "wind_speed": 12.5,
            "wind_direction": 180,
            "rainfall": 0.0,
            "uv_index": 6.0,
            **overrides,
        }

    @staticmethod
    def create_system_status(**overrides) -> dict[str, Any]:
        """Create test system status data."""
        return {
            "uptime": 3600,
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 23.1,
            "network_rx": 1024000,
            "network_tx": 512000,
            "active_connections": 5,
            "error_count": 0,
            **overrides,
        }

    @staticmethod
    def create_mcp_tool_response(
        success: bool = True,
        action: str | None = None,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Create a mock MCP tool response."""
        response = {"success": success}
        if action:
            response["action"] = action
        if data:
            response["data"] = data
        if error:
            response["error"] = error
        return response

    @staticmethod
    def create_api_request_data(**overrides) -> dict[str, Any]:
        """Create test API request data."""
        return {
            "camera_name": "test_camera",
            "device_id": "test_device_123",
            "filename": "test_output.jpg",
            "quality": "high",
            "timeout": 30,
            **overrides,
        }


# ============================================================================
# ASSERTION HELPERS
# ============================================================================


class AssertionHelpers:
    """Enhanced assertion helpers for comprehensive testing."""

    @staticmethod
    def assert_dict_contains_subset(superset: dict[Any, Any], subset: dict[Any, Any]) -> None:
        """Assert that superset contains all key-value pairs from subset."""
        for key, expected_value in subset.items():
            assert key in superset, f"Key '{key}' not found in dictionary"
            actual_value = superset[key]

            if isinstance(expected_value, dict) and isinstance(actual_value, dict):
                AssertionHelpers.assert_dict_contains_subset(actual_value, expected_value)
            elif isinstance(expected_value, list) and isinstance(actual_value, list):
                AssertionHelpers.assert_list_contains_subset(actual_value, expected_value)
            else:
                assert actual_value == expected_value, (
                    f"Value for key '{key}' does not match. Expected {expected_value}, got {actual_value}"
                )

    @staticmethod
    def assert_list_contains_subset(superset: list[Any], subset: list[Any]) -> None:
        """Assert that superset contains all elements from subset."""
        for item in subset:
            assert item in superset, f"Item '{item}' not found in list"

    @staticmethod
    def assert_api_response_success(response: dict[str, Any], required_fields: list[str] | None = None) -> None:
        """Assert that an API response indicates success and has required fields."""
        assert isinstance(response, dict), "Response must be a dictionary"
        assert "success" in response, "Response missing 'success' field"
        assert response["success"] is True, f"API call failed: {response}"

        if required_fields:
            for field in required_fields:
                assert field in response, f"Required field '{field}' missing from successful response"

    @staticmethod
    def assert_api_response_error(
        response: dict[str, Any],
        expected_status: int | None = None,
        expected_error_contains: str | None = None,
    ) -> None:
        """Assert that an API response indicates an error."""
        assert isinstance(response, dict), "Response must be a dictionary"
        assert "success" in response, "Response missing 'success' field"
        assert response["success"] is False, "Expected error response but got success"

        if expected_status:
            assert "status_code" in response, "Error response missing status_code"
            assert response["status_code"] == expected_status, (
                f"Expected status {expected_status}, got {response['status_code']}"
            )

        if expected_error_contains:
            assert "error" in response, "Error response missing error field"
            assert expected_error_contains in str(response["error"]), (
                f"Error message doesn't contain '{expected_error_contains}'"
            )

    @staticmethod
    def assert_mcp_response_valid(response: dict[str, Any], expected_action: str | None = None) -> None:
        """Assert that an MCP response is valid."""
        assert isinstance(response, dict), "MCP response must be a dictionary"
        assert "success" in response, "MCP response missing 'success' field"

        if expected_action:
            assert "action" in response, "MCP response missing 'action' field"
            assert response["action"] == expected_action, (
                f"Expected action '{expected_action}', got '{response['action']}'"
            )

        if response.get("success"):
            assert "data" in response, "Successful MCP response missing 'data' field"
        else:
            assert "error" in response, "Failed MCP response missing 'error' field"

    @staticmethod
    def assert_performance_under_limit(elapsed_time: float, limit_seconds: float, operation: str = "operation") -> None:
        """Assert that an operation completed within the time limit."""
        assert elapsed_time < limit_seconds, (
            f"{operation} took {elapsed_time:.2f}s, which exceeds the limit of {limit_seconds}s"
        )

    @staticmethod
    def assert_no_exceptions(func, *args, **kwargs) -> Any:
        """Assert that a function executes without raising exceptions."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            pytest.fail(f"Function raised unexpected exception: {e}")

    @staticmethod
    async def assert_async_no_exceptions(async_func, *args, **kwargs) -> Any:
        """Assert that an async function executes without raising exceptions."""
        try:
            return await async_func(*args, **kwargs)
        except Exception as e:
            pytest.fail(f"Async function raised unexpected exception: {e}")


# ============================================================================
# MOCKING UTILITIES
# ============================================================================


class MockingUtils:
    """Utilities for creating comprehensive mocks."""

    @staticmethod
    def create_mock_tapo_camera(status: str = "connected") -> Mock:
        """Create a mock Tapo camera with configurable status."""
        mock_camera = Mock()
        mock_camera.status = status
        mock_camera.is_connected.return_value = status == "connected"
        mock_camera.connect.return_value = asyncio.Future()
        mock_camera.connect.return_value.set_result(None)
        mock_camera.disconnect.return_value = asyncio.Future()
        mock_camera.disconnect.return_value.set_result(None)

        # Mock camera info
        mock_camera.get_device_info.return_value = TestDataFactory.create_energy_device()
        mock_camera.get_stream_url.return_value = "rtsp://192.168.1.100:554/stream1"

        return mock_camera

    @staticmethod
    def create_mock_mcp_client(responses: dict[str, Any] | None = None) -> Mock:
        """Create a mock MCP client with configurable responses."""
        mock_client = AsyncMock()
        default_responses = responses or {
            "energy_management.status": {"success": True, "data": {"devices": []}},
            "motion_management.status": {"success": True, "data": {"subscriptions": []}},
            "camera_management.info": {"success": True, "data": {"camera_id": "test"}},
        }

        async def mock_call_tool(tool_name, arguments=None):
            key = f"{tool_name}"
            if arguments and "action" in arguments:
                key += f".{arguments['action']}"
            return default_responses.get(key, {"success": False, "error": "Unknown tool"})

        mock_client.call_tool.side_effect = mock_call_tool
        return mock_client

    @staticmethod
    def create_mock_database(initial_data: dict[str, list[dict]] | None = None) -> Mock:
        """Create a mock database with initial data."""
        mock_db = Mock()
        data_store = initial_data or {}

        def mock_insert(table, data):
            if table not in data_store:
                data_store[table] = []
            record_id = len(data_store[table]) + 1
            data_copy = data.copy()
            data_copy["id"] = record_id
            data_store[table].append(data_copy)
            return record_id

        def mock_select(table, where=None):
            if table not in data_store:
                return []
            records = data_store[table]
            if where:
                return [r for r in records if all(r.get(k) == v for k, v in where.items())]
            return records

        mock_db.insert.side_effect = mock_insert
        mock_db.select.side_effect = mock_select
        mock_db.data = data_store

        return mock_db

    @staticmethod
    @contextmanager
    def mock_environment_variables(**env_vars):
        """Context manager for mocking environment variables."""
        original_values = {}
        for key, value in env_vars.items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    @staticmethod
    @asynccontextmanager
    async def mock_async_context():
        """Async context manager for testing async contexts."""
        # Setup
        yield
        # Cleanup


# ============================================================================
# PERFORMANCE TESTING UTILITIES
# ============================================================================


class PerformanceTestUtils:
    """Utilities for performance testing."""

    @staticmethod
    def create_performance_timer():
        """Create a performance timer for measuring execution time."""

        class PerformanceTimer:
            def __init__(self):
                self.start_time = None
                self.end_time = None

            def start(self):
                self.start_time = time.time()

            def stop(self):
                self.end_time = time.time()

            @property
            def elapsed(self):
                if self.start_time is None or self.end_time is None:
                    return 0
                return self.end_time - self.start_time

            def assert_under_limit(self, limit_seconds: float, operation: str = "operation"):
                AssertionHelpers.assert_performance_under_limit(self.elapsed, limit_seconds, operation)

            def reset(self):
                self.start_time = None
                self.end_time = None

        return PerformanceTimer()

    @staticmethod
    def benchmark_async_function(async_func, iterations: int = 100, *args, **kwargs) -> dict[str, float]:
        """Benchmark an async function over multiple iterations."""

        async def run_benchmark():
            times = []
            for _ in range(iterations):
                start = time.time()
                await async_func(*args, **kwargs)
                end = time.time()
                times.append(end - start)

            return {
                "iterations": iterations,
                "total_time": sum(times),
                "average_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "median_time": sorted(times)[len(times) // 2],
            }

        return asyncio.run(run_benchmark())

    @staticmethod
    def create_load_test_scenario(
        endpoints: list[str], concurrent_users: int = 10, requests_per_user: int = 50
    ) -> dict[str, Any]:
        """Create a load testing scenario."""
        return {
            "endpoints": endpoints,
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": concurrent_users * requests_per_user,
            "test_duration_estimate": concurrent_users * requests_per_user * 0.1,  # Rough estimate
        }


# ============================================================================
# INTEGRATION TESTING UTILITIES
# ============================================================================


class IntegrationTestUtils:
    """Utilities for integration testing."""

    @staticmethod
    def create_test_client_with_middleware(app) -> TestClient:
        """Create a test client with additional middleware for testing."""
        # Add any custom middleware for integration testing
        return TestClient(app)

    @staticmethod
    def create_end_to_end_test_scenario(scenario_name: str) -> dict[str, Any]:
        """Create an end-to-end test scenario definition."""
        scenarios = {
            "camera_lifecycle": {
                "steps": [
                    {"action": "discover_cameras", "endpoint": "/api/cameras/discover"},
                    {"action": "list_cameras", "endpoint": "/api/cameras"},
                    {"action": "get_camera_info", "endpoint": "/api/cameras/{camera_id}"},
                    {"action": "get_stream", "endpoint": "/api/cameras/{camera_id}/stream"},
                ],
                "expected_responses": ["success", "cameras_list", "camera_info", "stream_url"],
            },
            "energy_monitoring": {
                "steps": [
                    {"action": "list_devices", "endpoint": "/api/energy/devices"},
                    {"action": "current_usage", "endpoint": "/api/energy/current-usage"},
                    {"action": "energy_stats", "endpoint": "/api/energy/stats"},
                ],
                "expected_responses": ["devices_list", "usage_data", "statistics"],
            },
            "motion_detection": {
                "steps": [
                    {"action": "motion_status", "endpoint": "/api/motion/status"},
                    {"action": "motion_events", "endpoint": "/api/motion/events"},
                    {"action": "subscribe_motion", "endpoint": "/api/motion/subscribe/{camera_id}"},
                ],
                "expected_responses": ["status_info", "events_list", "subscription_result"],
            },
        }

        return scenarios.get(scenario_name, {"error": f"Unknown scenario: {scenario_name}"})

    @staticmethod
    async def run_integration_test_scenario(
        client: TestClient, scenario: dict[str, Any], **context_vars
    ) -> dict[str, Any]:
        """Run an integration test scenario."""
        results = {"scenario": scenario, "steps_executed": [], "failures": [], "success": True}

        for step in scenario["steps"]:
            try:
                endpoint = step["endpoint"].format(**context_vars)
                method = step.get("method", "GET")

                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    data = step.get("data", {})
                    response = client.post(endpoint, json=data)
                else:
                    results["failures"].append(f"Unsupported method: {method}")
                    results["success"] = False
                    continue

                if response.status_code != step.get("expected_status", 200):
                    results["failures"].append(
                        f"Step {step['action']}: Expected status {step.get('expected_status', 200)}, got {response.status_code}"
                    )
                    results["success"] = False

                results["steps_executed"].append(
                    {
                        "step": step,
                        "status_code": response.status_code,
                        "response_size": len(response.content),
                    }
                )

            except Exception as e:
                results["failures"].append(f"Step {step['action']}: Exception {e}")
                results["success"] = False

        return results


# ============================================================================
# FILE AND RESOURCE TESTING UTILITIES
# ============================================================================


class FileTestUtils:
    """Utilities for testing file operations."""

    @staticmethod
    @contextmanager
    def create_temp_file(content: str = "", suffix: str = ".txt"):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            yield temp_path
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @staticmethod
    @contextmanager
    def create_temp_dir():
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @staticmethod
    def create_test_image_file(width: int = 100, height: int = 100) -> bytes:
        """Create a test image file content."""
        # Create a minimal valid PNG
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\xdac\x00\x01\x00\x00\x05\x00\x01\x0f\xa5\xea\xfd\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    @staticmethod
    def create_test_video_file() -> bytes:
        """Create test video file content."""
        # Mock video content
        return b"mock_video_data_mp4_format"


# ============================================================================
# CONFIGURATION TESTING UTILITIES
# ============================================================================


class ConfigTestUtils:
    """Utilities for testing configuration loading and validation."""

    @staticmethod
    def create_test_config_file(config_data: dict[str, Any], temp_dir: Path) -> Path:
        """Create a test configuration file."""
        import yaml

        config_path = temp_dir / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        return config_path

    @staticmethod
    def validate_config_schema(config: dict[str, Any], schema: dict[str, Any]) -> list[str]:
        """Validate configuration against a schema."""
        errors = []

        def validate_dict(data, schema_dict, path=""):
            for key, rules in schema_dict.items():
                current_path = f"{path}.{key}" if path else key

                if key not in data:
                    if rules.get("required", False):
                        errors.append(f"Missing required key: {current_path}")
                    continue

                value = data[key]
                expected_type = rules.get("type")

                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Type mismatch for {current_path}: expected {expected_type.__name__}, got {type(value).__name__}"
                    )

                if rules.get("type") is dict and "schema" in rules:
                    if isinstance(value, dict):
                        validate_dict(value, rules["schema"], current_path)

        validate_dict(config, schema)
        return errors


# ============================================================================
# ASYNC TESTING UTILITIES
# ============================================================================


class AsyncTestUtils:
    """Utilities for testing async functionality."""

    @staticmethod
    async def wait_for_condition(
        condition_func, timeout: float = 5.0, interval: float = 0.1, description: str = "condition"
    ):
        """Wait for an async condition to become true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)

        pytest.fail(f"Condition not met within {timeout}s: {description}")

    @staticmethod
    async def run_concurrent_tasks(tasks: list[asyncio.Task], timeout: float = 10.0):
        """Run multiple async tasks concurrently with timeout."""
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
            return results
        except TimeoutError:
            pytest.fail(f"Concurrent tasks did not complete within {timeout}s")

    @staticmethod
    async def assert_eventually_true(
        condition_func, timeout: float = 5.0, message: str = "Condition never became true"
    ):
        """Assert that a condition eventually becomes true."""
        await AsyncTestUtils.wait_for_condition(condition_func, timeout, message=message)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Create global instances for easy importing
test_data = TestDataFactory()
assertions = AssertionHelpers()
mocks = MockingUtils()
performance = PerformanceTestUtils()
integration = IntegrationTestUtils()
files = FileTestUtils()
config_utils = ConfigTestUtils()
async_utils = AsyncTestUtils()

# Export key functions for direct importing
__all__ = [
    # Assertions
    "AssertionHelpers",
    # Async
    "AsyncTestUtils",
    # Config
    "ConfigTestUtils",
    # Files
    "FileTestUtils",
    # Integration
    "IntegrationTestUtils",
    # Mocking
    "MockingUtils",
    # Performance
    "PerformanceTestUtils",
    # Factories
    "TestDataFactory",
    "assertions",
    "async_utils",
    "config_utils",
    "files",
    "integration",
    "mocks",
    "performance",
    "test_data",
]
