#!/usr/bin/env python3
"""
Test runner for Devices MCP Platform.

Supports both mock tests (for CI/GitHub) and real hardware tests.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_pytest(args):
    """Run pytest with specified arguments."""
    cmd = [sys.executable, "-m", "pytest", *args]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=False, cwd=Path(__file__).parent.parent)


def main():
    parser = argparse.ArgumentParser(description="Run Devices MCP tests")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "hardware", "all"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument("--mock-only", action="store_true", help="Run only mock tests (no real hardware/network)")
    parser.add_argument("--hardware", action="store_true", help="Include hardware tests (requires real devices)")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--ci", action="store_true", help="CI mode (fail fast, no hardware tests)")

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = []

    if args.ci:
        # CI mode: fast, no hardware
        pytest_args.extend(["-x", "--tb=short"])
        pytest_args.extend(["-m", "not hardware"])
    elif args.mock_only:
        # Mock only mode - run only our new test files
        pytest_args.extend(
            [
                "tests/unit/test_config.py",
                "tests/unit/test_mcp_tools.py",
                "tests/integration/test_web_api.py::TestWebAPI::test_health_endpoint",
                "tests/integration/test_web_api.py::TestWebAPI::test_dashboard_endpoint",
            ]
        )
    elif args.hardware:
        pytest_args.extend(["tests/test_hardware_connectivity.py", "--no-cov"])
        pytest_args.extend(["-m", "hardware"])
    # Default: run unit and mock integration tests
    elif args.type == "unit":
        pytest_args.extend(["-m", "unit"])
    elif args.type == "integration":
        pytest_args.extend(["-m", "integration and mock"])
    elif args.type == "all":
        pytest_args.extend(["-m", "not hardware and not real"])

    if args.coverage:
        pytest_args.extend(
            [
                "--cov=devices_mcp",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-fail-under=80",
            ]
        )

    if args.verbose:
        pytest_args.append("-v")

    # Run tests
    result = run_pytest(pytest_args)

    # Print results
    if result.returncode == 0:
        print("All tests passed!")
        if args.coverage:
            print("Coverage report generated in htmlcov/")
    else:
        print("Tests failed!")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
