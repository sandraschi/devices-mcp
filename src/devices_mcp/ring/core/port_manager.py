"""
Ring MCP Port Management Utility

Handles non-standard port allocation and graceful termination of previous instances.
Avoids popular ports like 8000 to prevent conflicts in development environments.
"""

import os
import socket
import subprocess
import sys
import time
from typing import Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# Use non-standard port to avoid conflicts
DEFAULT_RING_MCP_PORT = 8123
PORT_RANGE_START = 8100
PORT_RANGE_END = 8200


def find_free_port(preferred_port: int = DEFAULT_RING_MCP_PORT) -> int:
    """
    Find a free port, starting with preferred_port.

    If preferred_port is taken, searches in PORT_RANGE_START to PORT_RANGE_END.
    If all ports in range are taken, returns the first available port.
    """
    # First try the preferred port
    if is_port_free(preferred_port):
        return preferred_port

    # Search in the designated range
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if is_port_free(port):
            return port

    # Fallback: find any available port
    return _find_any_free_port()


def is_port_free(port: int) -> bool:
    """Check if a port is free on localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", port))
            return True
    except OSError:
        return False


def _find_any_free_port() -> int:
    """Find any available port by creating a temporary socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        return port


def get_process_using_port(port: int) -> Optional[int]:
    """
    Get the PID of the process using the specified port.

    Returns None if port is free or if we can't determine the PID.
    """
    try:
        # Windows: use netstat
        if sys.platform == "win32":
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid_str = parts[-1]
                        try:
                            return int(pid_str)
                        except ValueError:
                            continue

        # Linux/Unix: use lsof or ss
        elif sys.platform in ["linux", "darwin"]:
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}"], capture_output=True, text=True, check=True
                )
                for line in result.stdout.splitlines()[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            return int(parts[1])
                        except (ValueError, IndexError):
                            continue
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Try alternative method
                try:
                    result = subprocess.run(
                        ["ss", "-tlnp"], capture_output=True, text=True, check=True
                    )
                    for line in result.stdout.splitlines():
                        if f":{port} " in line:
                            parts = line.split()
                            if len(parts) >= 6 and "pid=" in parts[5]:
                                pid_str = parts[5].split("=")[1].split(",")[0]
                                try:
                                    return int(pid_str)
                                except ValueError:
                                    continue
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass

    except subprocess.CalledProcessError:
        pass

    return None


def gracefully_terminate_process(pid: int) -> bool:
    """
    Gracefully terminate a process by PID.

    First tries SIGTERM, then SIGKILL if needed.
    """
    try:
        if sys.platform == "win32":
            # Windows: use taskkill
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, check=True)
        else:
            # Unix/Linux: use kill
            subprocess.run(["kill", "-TERM", str(pid)], check=False, capture_output=True)
            # Wait a bit for graceful shutdown
            time.sleep(2)
            # Check if process is still running
            try:
                subprocess.run(["kill", "-0", str(pid)], check=False, capture_output=True)
                # Process still exists, force kill
                subprocess.run(["kill", "-KILL", str(pid)], check=False, capture_output=True)
            except subprocess.CalledProcessError:
                # Process already terminated
                pass
        return True
    except subprocess.CalledProcessError:
        return False


def handle_port_conflict(port: int) -> Tuple[int, bool]:
    """
    Handle port conflicts by terminating previous instances.

    Returns (final_port, was_terminated) where:
    - final_port: The port to use (may be different from requested)
    - was_terminated: True if we terminated a previous instance
    """
    if is_port_free(port):
        return port, False

    pid = get_process_using_port(port)
    if pid is None:
        # Port taken but can't identify process - find alternative
        new_port = find_free_port(port + 1)
        return new_port, False

    # We found a process using our port - likely a previous instance
    logger.info(f"Found previous Ring MCP instance (PID {pid}) using port {port}")
    logger.info("Attempting graceful termination...")

    if gracefully_terminate_process(pid):
        logger.info(f"Successfully terminated previous instance (PID {pid})")
        # Wait a moment for port to be released
        time.sleep(1)
        if is_port_free(port):
            logger.info(f"Port {port} is now available")
            return port, True
        logger.warning(f"Port {port} still occupied, finding alternative...")
        new_port = find_free_port(port + 1)
        return new_port, True
    logger.error(f"Failed to terminate previous instance (PID {pid})")
    logger.info("Finding alternative port...")
    new_port = find_free_port(port + 1)
    return new_port, False


def get_ring_mcp_port() -> int:
    """
    Get the Ring MCP port, handling conflicts gracefully.

    Uses environment variable PORT if set, otherwise uses DEFAULT_RING_MCP_PORT.
    Automatically handles conflicts by terminating previous instances.
    """
    port_env = os.getenv("PORT")
    if port_env:
        try:
            port = int(port_env)
        except ValueError:
            logger.warning(
                f"Invalid PORT value '{port_env}', using default {DEFAULT_RING_MCP_PORT}"
            )
            port = DEFAULT_RING_MCP_PORT
    else:
        port = DEFAULT_RING_MCP_PORT

    final_port, was_terminated = handle_port_conflict(port)

    if was_terminated:
        logger.info(f"Using port {final_port} (terminated previous instance)")
    elif final_port != port:
        logger.info(f"Port {port} was taken, using alternative port {final_port}")
    else:
        logger.info(f"Using port {final_port}")

    return final_port


def print_port_info(port: int) -> None:
    """Log information about the port being used."""
    logger.info("Ring MCP Port Configuration:")
    logger.info(f"   Default Port: {DEFAULT_RING_MCP_PORT}")
    logger.info(f"   Port Range: {PORT_RANGE_START}-{PORT_RANGE_END}")
    logger.info(f"   Current Port: {port}")
    logger.info(f"   Health Check: http://localhost:{port}/health")
    logger.info(f"   API Access: http://localhost:{port}")


if __name__ == "__main__":
    # Test the port management
    port = get_ring_mcp_port()
    print_port_info(port)
