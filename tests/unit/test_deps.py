#!/usr/bin/env python3
"""
Test script to identify dependency installation issues
"""

import subprocess
import sys
import tempfile


def test_dependency_installation():
    """Test if core dependencies can be installed."""

    dependencies = [
        ("pytapo", "pytapo>=3.3.0"),
        ("fastmcp", "fastmcp>=2.10.0"),
        ("aiohttp", "aiohttp>=3.8.0"),
        ("python-dotenv", "python-dotenv>=0.19.0"),
        ("pydantic", "pydantic>=1.9.0"),
    ]

    failed_deps = []

    for dep_name, dep_spec in dependencies:
        # First check if it's already installed
        check_cmd = [sys.executable, "-m", "pip", "show", dep_name]
        result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)

        if result.returncode == 0:
            lines = result.stdout.split("\n")
            for line in lines:
                if line.startswith("Version:"):
                    break

        # Test installation to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            install_cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                temp_dir,
                dep_spec,
            ]

            result = subprocess.run(install_cmd, check=False, capture_output=True, text=True)

            if result.returncode == 0:
                pass
            else:
                failed_deps.append(dep_spec)

    if failed_deps:
        for _dep in failed_deps:
            pass
        raise AssertionError(f"Failed to install dependencies: {failed_deps}")

    assert True


def main():
    """Test all dependencies."""
    return test_dependency_installation()


if __name__ == "__main__":
    sys.exit(main())
