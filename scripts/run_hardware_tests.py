#!/usr/bin/env python3
"""
Hardware Testing Runner Script

Runs comprehensive hardware connectivity tests for Devices MCP.
This script tests ALL hardware devices to ensure the webapp will be functional.

Usage:
    python run_hardware_tests.py                    # Run all tests
    python run_hardware_tests.py --critical-only   # Only critical systems
    python run_hardware_tests.py --quick           # Skip slow tests
    python run_hardware_tests.py --verbose         # Detailed output
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_pytest_hardware_tests(args):
    """Run hardware tests using pytest."""
    import subprocess

    logger.info("Running hardware connectivity tests with pytest...")

    # Build pytest command
    cmd = ["python", "-m", "pytest", "tests/test_hardware_connectivity.py"]

    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    if args.critical_only:
        cmd.extend(["-m", "critical"])
    elif args.quick:
        # Skip slow optional tests
        cmd.extend(["-m", "not optional"])
    else:
        cmd.extend(["-m", "hardware"])

    # Add timeout for tests
    cmd.extend(["--timeout=60", "--tb=short"])

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, cwd=Path(__file__).parent)

    return result.returncode == 0


async def run_verification_script(args):
    """Run the hardware connectivity verification script."""
    logger.info("Running hardware connectivity verification...")

    # Import and run the verification script
    try:
        exec(open("verify_hardware_connectivity.py").read())
        return True
    except SystemExit as e:
        return e.code == 0
    except Exception as e:
        logger.info(f"Verification script failed: {e}")
        return False


def run_selected_tests(args):
    """Run selected individual tests."""
    logger.info(f"Running selected hardware tests: {', '.join(args.tests)}")

    # This would run specific test functions
    # For now, just run the verification script
    return asyncio.run(run_verification_script(args))


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Hardware Testing Runner for Devices MCP")
    parser.add_argument(
        "--critical-only", action="store_true", help="Only test critical systems (cameras, config)"
    )
    parser.add_argument("--quick", action="store_true", help="Skip slow optional tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--pytest", action="store_true", help="Use pytest for running tests")
    parser.add_argument("--verify", action="store_true", help="Run verification script only")
    parser.add_argument("--tests", nargs="+", help="Run specific tests (not implemented yet)")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Devices MCP - HARDWARE CONNECTIVITY TESTING")
    logger.info("=" * 60)

    success = False

    if args.tests:
        success = run_selected_tests(args)
    elif args.verify:
        success = await run_verification_script(args)
    elif args.pytest:
        success = run_pytest_hardware_tests(args)
    else:
        # Default: run verification script
        success = await run_verification_script(args)

    logger.info("\n" + "=" * 60)
    if success:
        logger.info("SUCCESS: HARDWARE TESTS COMPLETED")
        logger.info("\nIf all critical systems are working, the webapp should be functional.")
        return 0
    logger.info("FAILURE: HARDWARE TESTS FAILED")
    logger.info("\nCritical hardware systems are not working.")
    logger.info("The webapp will NOT be functional until these issues are resolved.")
    return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTesting interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\nTesting suite crashed: {e}")
        sys.exit(1)
