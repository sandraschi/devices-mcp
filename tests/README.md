# Comprehensive Testing Infrastructure

This directory contains a comprehensive testing suite for the Devices MCP platform, designed to ensure code quality, reliability, and performance across all components.

## 🏗️ Architecture Overview

```
tests/
├── conftest.py                 # Global test configuration and fixtures
├── unit/                       # Unit tests (isolated component testing)
├── integration/               # Integration tests (component interaction)
├── e2e/                       # End-to-end tests (full workflow testing)
├── utils/                     # Testing utilities and helpers
├── unit/
│   ├── test_api_*.py         # API endpoint unit tests
│   ├── test_mcp_*.py         # MCP client/server tests
│   ├── test_core.py          # Core functionality tests
│   └── ...
├── integration/
│   ├── test_mcp_integration.py # MCP integration tests
│   └── test_*.py              # Component integration tests
├── utils/
│   ├── mock_mcp_server.py    # Mock MCP server for testing
│   ├── test_helpers.py        # Test utilities and factories
│   └── ...
└── README.md                  # This file
```

## TEST Test Categories

### Unit Tests (`tests/unit/`)
- **Isolation**: Each test focuses on a single component
- **Mocking**: External dependencies are mocked
- **Speed**: Fast execution (< 100ms per test)
- **Coverage**: High code coverage target (> 90%)

### Integration Tests (`tests/integration/`)
- **Component Interaction**: Test how components work together
- **Real Dependencies**: Use actual implementations where safe
- **MCP Protocol**: Full MCP client-server interaction testing
- **API Contracts**: Verify API behavior across components

### End-to-End Tests (`tests/e2e/`)
- **Full Workflows**: Complete user journeys
- **Real Services**: Limited use of real external services
- **Performance**: Real-world performance validation
- **Reliability**: System stability under load

## 🛠️ Testing Infrastructure

### Core Fixtures (`conftest.py`)

```python
# Example fixtures available globally
@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""

@pytest.fixture
def test_energy_device():
    """Factory for test energy device data."""

@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
```

### Test Data Factories (`utils/test_helpers.py`)

```python
from tests.utils.test_helpers import test_data, assertions

# Create test data
device = test_data.create_energy_device("plug1", "tapo_p115", "Test Plug")

# Assert API responses
assertions.assert_api_response_success(response)
assertions.assert_mcp_response_valid(result, "status")
```

### Mock MCP Server (`utils/mock_mcp_server.py`)

```python
from tests.utils.mock_mcp_server import MockMCPServer, MockMCPClient

# Create configurable mock server
server = MockMCPServer()
server.configure_response("energy_management", "status", {...})

# Test client-server interaction
client = MockMCPClient(server)
result = await client.call_tool("energy_management", "status")
```

## RUN Running Tests

### Quick Start

```bash
# Run all tests
poetry run pytest

# Run specific test categories
poetry run pytest tests/unit/        # Unit tests only
poetry run pytest tests/integration/ # Integration tests only
poetry run pytest tests/e2e/         # End-to-end tests only

# Run tests with coverage
poetry run pytest --cov=devices_mcp --cov-report=html

# Run specific test files
poetry run pytest tests/unit/test_api_energy.py

# Run tests matching pattern
poetry run pytest -k "energy" -v
```

### Advanced Options

```bash
# Run with performance benchmarking
poetry run pytest tests/unit/ -k "performance" --benchmark-only

# Run tests in parallel
poetry run pytest tests/unit/ -n auto

# Run tests with detailed output
poetry run pytest tests/unit/ -v --tb=short --durations=10

# Run tests and stop on first failure
poetry run pytest tests/unit/ -x

# Run tests with coverage and fail if below threshold
poetry run pytest --cov=devices_mcp --cov-fail-under=90
```

## CONFIG Test Configuration

### pytest.ini

```ini
[tool:pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --cov=devices_mcp --cov-report=term-missing"
markers = [
    "integration: marks tests as integration tests",
    "performance: marks tests as performance tests",
    "security: marks tests as security tests",
    "slow: marks tests as slow running"
]
```

### Coverage Configuration

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

## WRITE Writing Tests

### Unit Test Example

```python
import pytest
from tests.utils.test_helpers import test_data, assertions

class TestEnergyAPI:
    def test_list_devices_success(self, client):
        """Test successful device listing."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            # Setup mock response
            mock_call.return_value = test_data.create_mcp_tool_response(
                success=True,
                action="status",
                data={"devices": [test_data.create_energy_device()]}
            )

            # Execute test
            response = client.get("/api/energy/devices")

            # Assert results
            assertions.assert_api_response_success(response.json())
            assert len(response.json()["devices"]) == 1
```

### Integration Test Example

```python
import pytest
from tests.utils.mock_mcp_server import MockMCPServer, run_mcp_test_scenario

class TestMCPIntegration:
    async def test_energy_workflow(self):
        """Test complete energy management workflow."""
        server = MockMCPServer()
        client = server.get_client()

        scenario = [
            {"tool": "energy_management", "action": "status"},
            {"tool": "energy_management", "action": "consumption"},
            {"tool": "energy_management", "action": "control", "args": {"device_id": "plug1"}},
        ]

        results = await run_mcp_test_scenario(server, client, scenario)

        assert results["success"] is True
        assert results["steps_executed"] == 3
```

### Performance Test Example

```python
import pytest
from tests.utils.test_helpers import performance

class TestPerformance:
    def test_api_response_time(self, client, performance_timer):
        """Test API response time is acceptable."""
        performance_timer.start()

        response = client.get("/api/energy/devices")

        performance_timer.stop()

        assert response.status_code == 200
        performance_timer.assert_under_limit(1.0)  # 1 second max
```

## DATA Test Data Management

### Test Data Factories

```python
from tests.utils.test_helpers import test_data

# Create consistent test data
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

### Mock Data Management

```python
# Use predefined mock responses
mock_response = test_data.create_mcp_tool_response(
    success=True,
    action="status",
    data={"devices": [device]}
)

# Or create custom responses
custom_response = {
    "success": True,
    "action": "custom_action",
    "data": {"custom_field": "value"}
}
```

## 🔍 Test Debugging

### Debug Test Failures

```bash
# Run with detailed traceback
poetry run pytest tests/unit/test_api_energy.py::TestEnergyAPI::test_list_devices -v --tb=long

# Run with PDB on failure
poetry run pytest tests/unit/test_api_energy.py -x --pdb

# Run with IPython debugger
poetry run pytest tests/unit/test_api_energy.py --pdbcls=IPython.terminal.debugger:TerminalPdb
```

### Inspect Test Data

```python
# Add debug prints in tests
def test_debug_example(self, client):
    response = client.get("/api/energy/devices")
    print(f"Response: {response.json()}")  # Debug output
    assert response.status_code == 200
```

### Mock Debugging

```python
# Inspect mock calls
def test_mock_inspection(self, client):
    with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
        mock_call.return_value = {"success": True}

        client.get("/api/energy/devices")

        # Inspect the call
        assert mock_call.called
        call_args = mock_call.call_args
        print(f"Called with: {call_args}")
```

## COVERAGE Coverage Reporting

### Generate Coverage Reports

```bash
# Terminal coverage report
poetry run pytest --cov=devices_mcp --cov-report=term-missing

# HTML coverage report
poetry run pytest --cov=devices_mcp --cov-report=html
open htmlcov/index.html

# XML coverage report (for CI/CD)
poetry run pytest --cov=devices_mcp --cov-report=xml
```

### Coverage Goals

- **Unit Tests**: > 90% coverage
- **Integration Tests**: > 80% coverage
- **Critical Paths**: 100% coverage
- **API Endpoints**: 100% coverage

## RUN CI/CD Integration

### GitHub Actions Workflow

The comprehensive CI/CD pipeline includes:

- **Quality Checks**: Linting, type checking, security scanning
- **Unit Tests**: Multi-version Python testing
- **Integration Tests**: Component interaction testing
- **API Contract Tests**: OpenAPI specification validation
- **Performance Tests**: Benchmarking and load testing
- **Security Tests**: Vulnerability scanning and secrets detection
- **Windows Tests**: Windows compatibility
- **Container Tests**: Docker image validation

### Running CI Locally

```bash
# Run the full CI pipeline locally
make ci

# Or run individual CI jobs
make ci-quality
make ci-unit
make ci-integration
```

## 🐛 Troubleshooting

### Common Issues

#### Test Discovery Issues
```bash
# Check test discovery
poetry run pytest --collect-only

# Check for import errors
poetry run python -c "import tests.conftest"
```

#### Mock Issues
```bash
# Verify mock setup
poetry run pytest tests/unit/test_api_energy.py::TestEnergyAPI::test_list_devices -v -s
```

#### Coverage Issues
```bash
# Check coverage configuration
poetry run coverage run --source=devices_mcp -m pytest tests/unit/
poetry run coverage report
```

### Performance Issues

#### Slow Tests
```bash
# Identify slow tests
poetry run pytest --durations=10

# Profile test performance
poetry run pytest --profile
```

#### Memory Issues
```bash
# Check memory usage
poetry run pytest --memusage
```

## PRACTICES Best Practices

### Test Organization
- **One concept per test**: Each test should verify one behavior
- **Descriptive names**: Test names should explain what they verify
- **Arrange-Act-Assert**: Clear test structure
- **Independent tests**: Tests should not depend on each other

### Mocking Guidelines
- **Minimal mocking**: Only mock external dependencies
- **Realistic mocks**: Mock responses should match real behavior
- **Verification**: Verify mock interactions when relevant
- **Isolation**: Tests should not share mock state

### Performance Testing
- **Realistic scenarios**: Test with production-like data
- **Measurable thresholds**: Define acceptable performance limits
- **Regression detection**: Catch performance regressions
- **Environment consistency**: Test in similar environments

## 🤝 Contributing

### Adding New Tests

1. **Choose appropriate category**: unit/, integration/, or e2e/
2. **Follow naming conventions**: `test_*.py`, `Test*` classes, `test_*` methods
3. **Use existing fixtures**: Leverage conftest.py fixtures
4. **Add comprehensive assertions**: Cover success and error cases
5. **Update documentation**: Add docstrings and comments

### Test Maintenance

- **Keep tests updated**: Update tests when code changes
- **Remove obsolete tests**: Delete tests for removed functionality
- **Refactor test code**: Apply same standards as production code
- **Review test coverage**: Ensure new code has adequate test coverage

## 📞 Support

For testing infrastructure issues:

1. Check this README first
2. Review existing test examples
3. Check CI/CD pipeline logs
4. Create an issue with test failure details
5. Include environment information and reproduction steps

## 🔗 Related Documentation

- [API Documentation](../docs/api/)
- [MCP Protocol Documentation](../docs/mcp/)
- [Development Setup](../docs/development/)
- [CI/CD Pipeline](../.github/workflows/)
