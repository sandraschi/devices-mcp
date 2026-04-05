# Testing Infrastructure Guide

Comprehensive guide to the testing infrastructure for the Devices MCP platform.

## 🏗️ **Testing Architecture**

The platform features a comprehensive testing scaffold designed for enterprise-grade reliability:

```
tests/
├── conftest.py                 # Global fixtures and configuration
├── unit/                       # Unit tests (92% coverage target)
├── integration/               # Integration tests (85% coverage target)
├── e2e/                       # End-to-end tests
├── utils/                     # Testing utilities and helpers
│   ├── mock_mcp_server.py    # Mock MCP server for testing
│   └── test_helpers.py        # Test data factories and assertions
└── README.md                  # Testing documentation
```

## 🧪 **Test Categories**

### **Unit Tests** (`tests/unit/`)
- **Isolation**: Single component testing with mocked dependencies
- **Speed**: < 100ms per test execution
- **Coverage**: 92% target coverage
- **Scope**: Individual functions, classes, and modules

### **Integration Tests** (`tests/integration/`)
- **Component Interaction**: Testing how components work together
- **MCP Protocol**: Full client-server interaction testing
- **Real Dependencies**: Actual implementations where safe
- **Coverage**: 85% target coverage

### **End-to-End Tests** (`tests/e2e/`)
- **Full Workflows**: Complete user journeys
- **API Contracts**: OpenAPI specification validation
- **Performance**: Real-world performance validation
- **Reliability**: System stability under load

## 🛠️ **Core Testing Infrastructure**

### **Configuration** (`conftest.py`)

#### **Global Fixtures**
```python
@pytest.fixture(scope="session")
def event_loop():
    """Async event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def config():
    """Test configuration data."""
    return TapoCameraConfig(**TEST_CONFIG)

@pytest.fixture
async def mock_session():
    """Mock aiohttp client session."""
    # Comprehensive HTTP mocking
```

#### **Mock Infrastructure**
```python
@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock(spec=MCPClient)
    client.call_tool.return_value = {"success": True, "data": {}}
    return client

@pytest.fixture
def mock_energy_tool_success():
    """Pre-configured successful tool response."""
    return {
        "success": True,
        "action": "status",
        "data": {"devices": [test_device_data]}
    }
```

#### **Data Fixtures**
```python
@pytest.fixture
def sample_energy_device():
    """Sample energy device data."""
    return TestDataFactory.create_energy_device(
        "test_plug", "tapo_p115", "Living Room Plug"
    )

@pytest.fixture
def sample_motion_event():
    """Sample motion detection event."""
    return TestDataFactory.create_motion_event(
        camera_id="front_door",
        confidence=0.95
    )
```

### **Test Utilities** (`utils/test_helpers.py`)

#### **Test Data Factories**
```python
class TestDataFactory:
    """Factory for generating consistent test data."""

    @staticmethod
    def create_energy_device(device_id, device_type, name, **overrides):
        """Create realistic energy device data."""
        return {
            "device_id": device_id,
            "name": name,
            "type": device_type,
            "power_state": True,
            "current_power": 45.2,
            # ... comprehensive device data
            **overrides
        }
```

#### **Assertion Helpers**
```python
class AssertionHelpers:
    """Enhanced assertions for comprehensive testing."""

    @staticmethod
    def assert_api_response_success(response, required_fields=None):
        """Assert API response success with validation."""
        assert response["success"] is True
        if required_fields:
            for field in required_fields:
                assert field in response

    @staticmethod
    def assert_mcp_response_valid(response, expected_action=None):
        """Assert MCP response validity."""
        assert response.get("success") in [True, False]
        if expected_action:
            assert response.get("action") == expected_action
```

#### **Performance Testing**
```python
class PerformanceTestUtils:
    """Performance testing utilities."""

    @staticmethod
    def create_performance_timer():
        """Create timer for performance validation."""
        class PerformanceTimer:
            def start(self): self.start_time = time.time()
            def stop(self): self.end_time = time.time()
            def assert_under_limit(self, limit):
                assert self.elapsed < limit
        return PerformanceTimer()

    @staticmethod
    async def benchmark_async_function(func, iterations=100, *args, **kwargs):
        """Benchmark async function performance."""
        times = []
        for _ in range(iterations):
            start = time.time()
            await func(*args, **kwargs)
            times.append(time.time() - start)
        return {
            "iterations": iterations,
            "average_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times)
        }
```

### **Mock MCP Server** (`utils/mock_mcp_server.py`)

#### **Configurable Mock Server**
```python
class MockMCPServer:
    """Mock MCP server for testing client interactions."""

    def __init__(self, response_config=None):
        self.response_config = response_config or self._get_default_config()
        self.requests_received = []
        self.responses_sent = []

    def configure_response(self, tool, action, response):
        """Configure custom tool responses."""
        if tool not in self.response_config["tools"]:
            self.response_config["tools"][tool] = {}
        self.response_config["tools"][tool][action] = response

    def configure_delay(self, tool, action, delay_seconds):
        """Configure response delays for timeout testing."""
        self.response_config["delays"][f"{tool}.{action}"] = delay_seconds

    def configure_error(self, tool, action, error_response):
        """Configure error responses for failure testing."""
        self.response_config["errors"][f"{tool}.{action}"] = error_response
```

#### **Scenario Testing**
```python
async def run_mcp_test_scenario(server, client, scenario):
    """Run complete MCP interaction scenarios."""
    results = {"steps_executed": 0, "errors": [], "responses": []}

    for step in scenario:
        try:
            if step["type"] == "tool_call":
                result = await client.call_tool(
                    step["tool"], step["action"], **step.get("args", {})
                )
                results["responses"].append(result)
                results["steps_executed"] += 1
        except Exception as e:
            results["errors"].append({"step": step, "error": str(e)})

    return results
```

## 🚀 **Running Tests**

### **Quick Start**
```bash
# Run all tests
poetry run pytest

# Run specific categories
poetry run pytest tests/unit/         # Unit tests only
poetry run pytest tests/integration/  # Integration tests only

# Run with coverage
poetry run pytest --cov=devices_mcp --cov-report=html

# Run performance tests
poetry run pytest -k "performance" --benchmark-only
```

### **Advanced Options**
```bash
# Parallel execution
poetry run pytest -n auto

# Detailed output with durations
poetry run pytest -v --durations=10

# Stop on first failure
poetry run pytest -x

# Run with specific markers
poetry run pytest -m "integration and not slow"

# Generate coverage report
poetry run pytest --cov=devices_mcp --cov-report=xml --cov-fail-under=90
```

## 📝 **Writing Tests**

### **Unit Test Example**
```python
import pytest
from tests.utils.test_helpers import test_data, assertions

class TestEnergyAPI:
    def test_list_devices_success(self, client, mock_energy_tool_success):
        """Test successful device listing."""
        with patch("devices_mcp.mcp_client.call_mcp_tool",
                   return_value=mock_energy_tool_success):
            response = client.get("/api/energy/devices")

            assertions.assert_api_response_success(response.json())
            assert len(response.json()["devices"]) == 1
```

### **Integration Test Example**
```python
import pytest
from tests.utils.mock_mcp_server import MockMCPServer, run_mcp_test_scenario

class TestMCPIntegration:
    async def test_energy_workflow(self):
        """Test complete energy management workflow."""
        server = MockMCPServer()
        client = MockMCPClient(server)

        scenario = [
            {"type": "tool_call", "tool": "energy_management", "action": "status"},
            {"type": "tool_call", "tool": "energy_management", "action": "consumption"},
            {"type": "tool_call", "tool": "energy_management", "action": "control",
             "args": {"device_id": "plug1", "power_state": "off"}},
        ]

        results = await run_mcp_test_scenario(server, client, scenario)
        assert results["success"] is True
        assert results["steps_executed"] == 3
```

### **Performance Test Example**
```python
import pytest
from tests.utils.test_helpers import performance

class TestPerformance:
    def test_api_response_time(self, client, performance_timer):
        """Test API response time is acceptable."""
        with patch("devices_mcp.mcp_client.call_mcp_tool",
                   return_value={"success": True, "data": {}}):
            performance_timer.start()
            response = client.get("/api/energy/devices")
            performance_timer.stop()

            assert response.status_code == 200
            performance_timer.assert_under_limit(1.0)  # 1 second max
```

## 🎯 **Test Data Management**

### **Factory Pattern**
```python
# Consistent test data generation
device = test_data.create_energy_device(
    device_id="test_plug",
    name="Test Smart Plug",
    power_state=True,
    current_power=45.2
)

event = test_data.create_motion_event(
    camera_id="front_door",
    confidence=0.95,
    regions=[[100, 100, 200, 200]]
)
```

### **Mock Management**
```python
# Pre-configured mock responses
mock_response = test_data.create_mcp_tool_response(
    success=True,
    action="status",
    data={"devices": [device]}
)

# Custom responses for edge cases
error_response = test_data.create_mcp_tool_response(
    success=False,
    error="Device not found"
)
```

## 🔍 **Test Debugging**

### **Debugging Techniques**
```bash
# Detailed traceback
poetry run pytest tests/unit/test_api_energy.py::TestEnergyAPI::test_list_devices -v --tb=long

# PDB on failure
poetry run pytest tests/unit/test_api_energy.py -x --pdb

# Inspect mock calls
def test_with_inspection(self, client):
    with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
        mock_call.return_value = {"success": True}
        client.get("/api/energy/devices")

        # Inspect the call
        call_args = mock_call.call_args
        print(f"Called with: {call_args}")
```

### **Common Debugging Patterns**
```python
# Log test execution
def test_with_logging(self, client, caplog):
    with caplog.at_level(logging.DEBUG):
        response = client.get("/api/energy/devices")
        assert "MCP call" in caplog.text

# Inspect response details
def test_response_inspection(self, client):
    response = client.get("/api/energy/devices")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print(f"Headers: {dict(response.headers)}")
```

## 📊 **Coverage Analysis**

### **Coverage Reporting**
```bash
# Terminal coverage report
poetry run pytest --cov=devices_mcp --cov-report=term-missing

# HTML coverage report
poetry run pytest --cov=devices_mcp --cov-report=html
open htmlcov/index.html

# Coverage by test type
poetry run pytest --cov=devices_mcp --cov-report=term-missing:skip-covered
```

### **Coverage Goals**
- **Unit Tests**: > 92% coverage
- **Integration Tests**: > 85% coverage
- **API Endpoints**: 100% coverage
- **MCP Tools**: 95% coverage
- **Critical Paths**: 100% coverage

### **Coverage Configuration**
```ini
[tool.coverage.run]
source = ["devices_mcp"]
omit = [
    "**/tests/**",
    "**/__main__.py",
    "**/migrations/**"
]

[tool.coverage.report]
show_missing = true
skip_covered = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

## 🚀 **CI/CD Integration**

### **GitHub Actions Pipeline**
The comprehensive CI/CD pipeline includes:

1. **Quality Checks**: Linting, type checking, security scanning
2. **Unit Tests**: Multi-version Python testing with coverage
3. **Integration Tests**: MCP client-server interaction testing
4. **API Contract Tests**: OpenAPI specification validation
5. **Performance Tests**: Benchmarking and load testing
6. **Security Tests**: Vulnerability scanning and dependency analysis
7. **Windows Tests**: Windows compatibility
8. **Container Tests**: Docker image validation
9. **Deployment Tests**: Production deployment validation

### **Local CI Execution**
```bash
# Run full CI pipeline locally
make ci

# Run individual CI stages
make ci-quality     # Code quality checks
make ci-unit       # Unit tests
make ci-integration # Integration tests
make ci-performance # Performance tests
```

## 🐛 **Troubleshooting**

### **Test Discovery Issues**
```bash
# Check test collection
poetry run pytest --collect-only -q | head -20

# Verify import paths
python -c "import tests.conftest; print('Conftest loaded successfully')"
```

### **Mock Configuration Issues**
```bash
# Verify mock setup
poetry run pytest tests/unit/test_api_energy.py::TestEnergyAPI::test_list_devices -v -s

# Debug mock interactions
def test_mock_debug(self, client):
    with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
        mock_call.return_value = {"success": True}
        response = client.get("/api/energy/devices")

        print(f"Mock called: {mock_call.called}")
        print(f"Call args: {mock_call.call_args}")
        print(f"Response: {response.json()}")
```

### **Performance Issues**
```bash
# Identify slow tests
poetry run pytest --durations=10 --durations-min=1.0

# Profile test execution
poetry run pytest --profile --maxfail=1
```

### **Coverage Issues**
```bash
# Check coverage configuration
coverage run --source=devices_mcp -m pytest tests/unit/
coverage report --show-missing

# Debug coverage collection
coverage run --debug=trace -m pytest tests/unit/test_api_energy.py -v
```

## 📚 **Best Practices**

### **Test Organization**
- **One concept per test**: Each test should verify one behavior
- **Descriptive names**: Test names should explain what they verify
- **Arrange-Act-Assert**: Clear test structure
- **Independent tests**: Tests should not depend on each other

### **Mocking Guidelines**
- **Minimal mocking**: Only mock external dependencies
- **Realistic mocks**: Mock responses should match real behavior
- **Verification**: Verify mock interactions when relevant
- **Isolation**: Tests should not share mock state

### **Performance Testing**
- **Realistic scenarios**: Test with production-like data
- **Measurable thresholds**: Define acceptable performance limits
- **Regression detection**: Catch performance regressions
- **Environment consistency**: Test in similar environments

### **Integration Testing**
- **Realistic scenarios**: Test complete user workflows
- **Proper cleanup**: Clean up resources after tests
- **Error simulation**: Test error conditions and recovery
- **Concurrent safety**: Test concurrent operations

## 🤝 **Contributing**

### **Adding New Tests**
1. **Choose appropriate category**: unit/, integration/, or e2e/
2. **Follow naming conventions**: `test_*.py`, `Test*` classes, `test_*` methods
3. **Use existing fixtures**: Leverage conftest.py fixtures
4. **Add comprehensive assertions**: Cover success and error cases
5. **Update documentation**: Add docstrings and comments

### **Test Maintenance**
- **Keep tests updated**: Update tests when code changes
- **Remove obsolete tests**: Delete tests for removed functionality
- **Refactor test code**: Apply same standards as production code
- **Review test coverage**: Ensure new code has adequate test coverage

## 📞 **Support**

For testing infrastructure issues:
1. Check this guide first
2. Review existing test examples
3. Check CI/CD pipeline logs
4. Create an issue with test failure details
5. Include environment information and reproduction steps

## 🔗 **Related Documentation**

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [MCP Client Architecture](MCP_CLIENT_ARCHITECTURE.md) - MCP integration details
- [Development Setup](../docs/development/) - Development environment setup
- [CI/CD Pipeline](../.github/workflows/ci-comprehensive.yml) - Automated testing pipeline
