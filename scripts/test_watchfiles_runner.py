import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Test script for Devices MCP WebApp Watchfiles Runner

This script tests the crashproof runner functionality without actually running the full webapp.
Use this to verify the watchfiles implementation works correctly.

Usage:
    python test_watchfiles_runner.py
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from watchfiles_runner import CrashproofRunner


class TestProcessRunner(CrashproofRunner):
    """Test version that uses a simple test command instead of the full webapp."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crash_count = 0
        self.max_test_crashes = 3


async def test_basic_functionality():
    """Test basic crashproof runner functionality."""
    logger.info("Testing basic crashproof runner functionality...")

    # Create a test runner that runs a simple Python command
    runner = TestProcessRunner(
        command=[sys.executable, "-c", "import time; time.sleep(2); exit(0)"],
        max_restarts=3,
        restart_delay=0.5,  # Fast restarts for testing
        health_check_interval=1,
    )

    # Start process
    success = await runner.start_process()
    assert success, "Failed to start test process"

    # Wait for process to complete
    await asyncio.sleep(3)

    # Check that process completed normally
    assert runner.process.returncode == 0, f"Process exited with code {runner.process.returncode}"

    logger.info("Basic functionality test passed")


async def test_crash_recovery():
    """Test crash detection and recovery."""
    logger.info("Testing crash recovery functionality...")

    # Create a runner that will intentionally crash
    crash_script = """
import time
import sys
time.sleep(1)
sys.exit(42)  # Intentional crash
"""

    runner = TestProcessRunner(
        command=[sys.executable, "-c", crash_script],
        max_restarts=2,
        restart_delay=0.1,  # Very fast for testing
        health_check_interval=1,
    )

    # Start monitoring
    monitor_task = asyncio.create_task(runner.monitor_process())

    # Wait for initial process to start
    await asyncio.sleep(0.5)

    # Wait for crash and restart
    await asyncio.sleep(3)

    # Stop monitoring
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    # Check that crashes were detected and restarts attempted
    assert len(runner.crash_log) > 0, "No crashes were logged"
    assert runner.restart_count > 0, "No restarts were attempted"

    logger.info(
        f"Crash recovery test passed - detected {len(runner.crash_log)} crashes, {runner.restart_count} restarts"
    )


async def test_health_check():
    """Test health check functionality."""
    logger.info("Testing health check functionality...")

    # Create a mock health check URL (will fail)
    runner = TestProcessRunner(
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        health_check_url="http://nonexistent:9999/health",
        health_check_interval=1,
    )

    # Start process
    await runner.start_process()

    # Wait for health check to run a few times
    await asyncio.sleep(3)

    # Stop process gracefully
    if runner.process:
        runner.process.terminate()
        await runner.process.wait()

    logger.info("Health check test passed")


async def test_signal_handling():
    """Test signal handling for graceful shutdown."""
    logger.info("Testing signal handling...")

    runner = TestProcessRunner(command=[sys.executable, "-c", "import time; time.sleep(10)"], max_restarts=1)

    # Start process
    await runner.start_process()

    # Send SIGTERM
    if runner.process:
        if os.name == "nt":
            runner.process.terminate()
        else:
            os.kill(runner.process.pid, signal.SIGTERM)

    # Wait for process to be cleaned up
    await asyncio.sleep(1)

    # Process should be terminated
    assert runner.process.returncode is not None, "Process was not terminated"

    logger.info("Signal handling test passed")


async def test_statistics():
    """Test statistics collection."""
    logger.info("Testing statistics collection...")

    runner = TestProcessRunner(command=[sys.executable, "-c", "import time; time.sleep(1); exit(0)"], max_restarts=1)

    # Start process
    await runner.start_process()
    await asyncio.sleep(1.5)

    # Get stats
    stats = runner.get_stats()

    # Verify stats structure
    required_keys = ["process_running", "restart_count", "max_restarts", "total_uptime", "crash_count", "command"]
    for key in required_keys:
        assert key in stats, f"Missing stat key: {key}"

    logger.info("Statistics test passed")


async def main():
    """Run all tests."""
    logger.info("Starting Devices MCP WebApp Watchfiles Runner Tests")
    logger.info("=" * 55)

    tests = [test_basic_functionality, test_crash_recovery, test_health_check, test_signal_handling, test_statistics]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            logger.info(f"FAILED {test.__name__}: {e}")
            failed += 1
        finally:
            logger.info()

    logger.info("=" * 55)
    logger.info(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        logger.info("All tests passed!")
        return 0
    else:
        logger.info("Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
