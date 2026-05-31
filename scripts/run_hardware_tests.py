#!/usr/bin/env python3
"""
Hardware Testing Runner Script

Runs comprehensive hardware connectivity tests for Devices MCP.

Usage:
    python scripts/run_hardware_tests.py
    python scripts/run_hardware_tests.py --pytest
    python scripts/run_hardware_tests.py --verify
    python scripts/run_hardware_tests.py --pytest --critical-only
"""

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_pytest_hardware_tests(args) -> bool:
    import os

    env = os.environ.copy()
    if args.live:
        env["RUN_HARDWARE_TESTS"] = "1"

    cmd = [sys.executable, "-m", "pytest", "tests/test_hardware_connectivity.py", "--no-cov"]

    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    if args.critical_only:
        cmd.extend(["-m", "critical"])
    elif args.quick:
        cmd.extend(["-m", "not optional"])
    else:
        cmd.extend(["-m", "hardware"])

    cmd.extend(["--timeout=120", "--tb=short"])

    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False, cwd=REPO_ROOT, env=env)
    return result.returncode == 0


async def run_verification_script() -> bool:
    logger.info("Running hardware connectivity verification...")
    try:
        import importlib.util

        script_path = REPO_ROOT / "scripts" / "verify_hardware_connectivity.py"
        spec = importlib.util.spec_from_file_location("verify_hardware_connectivity", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load {script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        exit_code = await module.main()
        return exit_code == 0
    except Exception as e:
        logger.error("Verification script failed: %s", e)
        return False


async def main() -> int:
    parser = argparse.ArgumentParser(description="Hardware Testing Runner for Devices MCP")
    parser.add_argument("--critical-only", action="store_true", help="Only critical systems")
    parser.add_argument("--quick", action="store_true", help="Skip slow optional tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--pytest", action="store_true", help="Run pytest hardware tests")
    parser.add_argument("--verify", action="store_true", help="Run verification script only")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Set RUN_HARDWARE_TESTS=1 for live device pytest checks",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Devices MCP - HARDWARE CONNECTIVITY TESTING")
    logger.info("=" * 60)

    if args.verify:
        success = await run_verification_script()
    elif args.pytest:
        success = run_pytest_hardware_tests(args)
    else:
        verify_ok = await run_verification_script()
        pytest_ok = run_pytest_hardware_tests(args)
        success = verify_ok and pytest_ok

    logger.info("\n" + "=" * 60)
    if success:
        logger.info("SUCCESS: HARDWARE TESTS COMPLETED")
        return 0
    logger.info("FAILURE: HARDWARE TESTS FAILED")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("\nTesting interrupted by user")
        sys.exit(1)
