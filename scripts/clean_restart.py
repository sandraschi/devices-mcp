#!/usr/bin/env python3
"""
Clean restart script for Devices MCP webapp.
Ensures no file watchers or lingering processes interfere with restart.
"""

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def kill_processes_on_ports(*ports):
    """Kill any processes listening on the specified ports."""
    for port in ports:
        try:
            # Use netstat to find processes on the port
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=True)

            for line in result.stdout.split("\n"):
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        try:
                            # Kill the process
                            if sys.platform == "win32":
                                subprocess.run(["taskkill", "/PID", pid, "/F"], check=False)
                            else:
                                os.kill(int(pid), signal.SIGTERM)
                            logger.info(f"Killed process {pid} on port {port}")
                            time.sleep(0.5)  # Wait for cleanup
                        except (ValueError, OSError) as e:
                            logger.info(f"Failed to kill process {pid}: {e}")
        except subprocess.CalledProcessError:
            pass


def kill_watchfiles_processes():
    """Kill any watchfiles processes that might be running."""
    try:
        if sys.platform == "win32":
            # Kill watchfiles processes on Windows
            subprocess.run(["taskkill", "/F", "/IM", "watchfiles.exe"], check=False)
            subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq watchfiles*"], check=False)
        else:
            # Kill watchfiles processes on Unix-like systems
            subprocess.run(["pkill", "-f", "watchfiles"], check=False)
        logger.info("Killed any running watchfiles processes")
    except Exception as e:
        logger.info(f"Error killing watchfiles processes: {e}")


def start_webapp():
    """Start the Devices MCP webapp."""
    repo_root = Path(__file__).parent.parent
    webapp_script = repo_root / "src" / "devices_mcp" / "web" / "server.py"

    logger.info("Starting Devices MCP webapp...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    try:
        subprocess.run([sys.executable, str(webapp_script), "--port", "7777"], env=env, check=False)
    except KeyboardInterrupt:
        logger.info("Webapp stopped by user")
    except Exception as e:
        logger.info(f"Error starting webapp: {e}")


def main():
    """Main clean restart function."""
    logger.info("🧹 Performing clean restart of Devices MCP webapp...")

    # Kill processes on webapp ports
    logger.info("🔪 Killing processes on webapp ports...")
    kill_processes_on_ports(7777)

    # Kill any file watchers
    logger.info("🔪 Killing file watchers...")
    kill_watchfiles_processes()

    # Wait a moment for cleanup
    logger.info("⏳ Waiting for cleanup...")
    time.sleep(2)

    # Start the webapp
    start_webapp()


if __name__ == "__main__":
    main()
