"""
Network utilities for PlexMCP.

This module provides functions for network-related operations.
"""

import asyncio
import ipaddress
import logging
import socket
import ssl
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import aiohttp

logger = logging.getLogger(__name__)


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open on a remote host.

    Args:
        host: Hostname or IP address to check.
        port: Port number to check.
        timeout: Connection timeout in seconds.

    Returns:
        True if the port is open, False otherwise.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except (socket.gaierror, socket.timeout, ConnectionRefusedError):
        return False
    except Exception as e:
        logger.warning(f"Error checking port {port} on {host}: {e}")
        return False


async def async_is_port_open(
    host: str, port: int, timeout: float = 2.0, loop: Optional[asyncio.AbstractEventLoop] = None
) -> bool:
    """Asynchronously check if a TCP port is open on a remote host.

    Args:
        host: Hostname or IP address to check.
        port: Port number to check.
        timeout: Connection timeout in seconds.
        loop: Optional event loop to use.

    Returns:
        True if the port is open, False otherwise.
    """
    loop = loop or asyncio.get_event_loop()

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, loop=loop), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False
    except Exception as e:
        logger.warning(f"Error checking port {port} on {host}: {e}")
        return False


def get_local_ip() -> str:
    """Get the local IP address of the machine.

    Returns:
        Local IP address as a string.
    """
    try:
        # Create a socket connection to an external server but don't send any data
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Using Google's public DNS server to find our own IP
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        logger.warning(f"Could not determine local IP: {e}")
        return "127.0.0.1"


def is_valid_ip(ip: str) -> bool:
    """Check if a string is a valid IP address.

    Args:
        ip: IP address to validate.

    Returns:
        True if the IP address is valid, False otherwise.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_port(port: int) -> bool:
    """Check if a port number is valid.

    Args:
        port: Port number to validate.

    Returns:
        True if the port is valid, False otherwise.
    """
    return 1 <= port <= 65535


async def is_plex_server_reachable(
    base_url: str, token: Optional[str] = None, timeout: float = 5.0, ssl_verify: bool = True
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if a Plex server is reachable and return its status.

    Args:
        base_url: Base URL of the Plex server (e.g., 'http://localhost:32400').
        token: Plex authentication token.
        timeout: Request timeout in seconds.
        ssl_verify: Whether to verify SSL certificates.

    Returns:
        A tuple of (is_reachable, server_info).
        is_reachable: Boolean indicating if the server is reachable.
        server_info: Dictionary containing server information if reachable, None otherwise.
    """
    headers = {
        "Accept": "application/json",
        "X-Plex-Product": "PlexMCP",
        "X-Plex-Version": "1.0",
        "X-Plex-Client-Identifier": "plex-mcp",
        "X-Plex-Platform": "Python",
        "X-Plex-Platform-Version": "3.9",
        "X-Plex-Device": "PlexMCP",
        "X-Plex-Device-Name": "PlexMCP",
        "X-Plex-Device-Screen-Resolution": "1920x1080",
    }

    if token:
        headers["X-Plex-Token"] = token

    try:
        # Parse the URL to extract components
        parsed = urllib.parse.urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            return False, None

        # Reconstruct the base URL with proper scheme and netloc
        server_url = f"{parsed.scheme}://{parsed.netloc}"

        # Test connection to the server
        async with aiohttp.ClientSession() as session:
            # First, try to connect to the server root
            try:
                async with session.get(
                    f"{server_url}", headers=headers, timeout=timeout, ssl=ssl_verify
                ) as response:
                    if response.status != 200:
                        return False, None
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return False, None

            # Then try to get server info from the API
            try:
                async with session.get(
                    f"{server_url}/identity", headers=headers, timeout=timeout, ssl=ssl_verify
                ) as response:
                    if response.status == 200:
                        data = await response.text()
                        return True, {"status": "online", "data": data}
                    return False, None
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return False, None

    except Exception as e:
        logger.warning(f"Error checking Plex server at {base_url}: {e}")
        return False, None


def get_plex_auth_url(
    client_id: str, redirect_uri: str, app_name: str = "PlexMCP", forward_url: Optional[str] = None
) -> str:
    """Generate a Plex OAuth authentication URL.

    Args:
        client_id: Your Plex client identifier.
        redirect_uri: The redirect URI registered with Plex.
        app_name: Name of your application.
        forward_url: Optional URL to forward to after authentication.

    Returns:
        The authentication URL.
    """
    params = {
        "clientID": client_id,
        "code": "",
        "context[device][product]": app_name,
        "context[device][environment]=bundled": "",
        "context[device][layout]": "desktop",
        "context[device][platform]": "desktop",
        "context[device][device]": "PlexMCP",
        "forwardUrl": forward_url or "",
        "redirect_uri": redirect_uri,
    }

    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    return f"https://app.plex.tv/auth/#!?{query}"


def check_plex_url_connectivity(url: str) -> bool:
    """Check if a Plex server URL is valid and reachable.

    Args:
        url: URL to check connectivity for.

    Returns:
        True if the URL is a valid Plex server URL, False otherwise.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        # Check if the hostname is valid
        try:
            socket.gethostbyname(parsed.hostname)
        except (socket.gaierror, UnicodeError):
            return False

        # Check if the port is valid (if specified)
        if parsed.port is not None and not is_valid_port(parsed.port):
            return False

        return True
    except Exception:
        return False


def get_ssl_context(
    cert_file: Optional[Union[str, Path]] = None,
    key_file: Optional[Union[str, Path]] = None,
    ca_certs: Optional[Union[str, Path]] = None,
    verify: bool = True,
) -> ssl.SSLContext:
    """Create an SSL context for secure connections.

    Args:
        cert_file: Path to the certificate file.
        key_file: Path to the private key file.
        ca_certs: Path to the CA certificates file.
        verify: Whether to verify SSL certificates.

    Returns:
        Configured SSL context.
    """
    context = ssl.create_default_context()

    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    if cert_file and key_file:
        context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))

    if ca_certs:
        context.load_verify_locations(cafile=str(ca_certs))

    return context
