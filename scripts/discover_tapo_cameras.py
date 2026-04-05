"""
Discover Tapo cameras on the local network.

This script scans the local network for Tapo cameras and attempts to connect
to them using the provided credentials.
"""

import asyncio
import logging
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Network
from typing import List, Optional

from pytapo import Tapo

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is open on a host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def discover_tapo_on_ip(
    ip: str, username: str, password: str, timeout: float = 3.0
) -> Optional[dict]:
    """Attempt to connect to a Tapo camera on a specific IP.

    Uses safe single-attempt logic to avoid triggering camera lockouts.
    """
    try:
        # Check if port 443 is open (Tapo cameras use HTTPS)
        if not check_port(ip, 443, timeout=0.5):
            return None

        logger.info(f"Checking {ip}...")

        # Try to connect to Tapo camera - ONLY ONCE to prevent lockouts
        try:
            camera = Tapo(ip, username, password)
            basic_info = camera.getBasicInfo()
        except Exception as auth_error:
            error_msg = str(auth_error)

            # Check for lockout - stop immediately
            if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
                logger.warning(
                    f"  ⚠️  Camera at {ip} is LOCKED OUT (too many failed attempts). Skipping."
                )
                logger.warning("     Wait 30 minutes before retrying this camera.")
                return None

            # Authentication errors - wrong credentials, not a Tapo camera, or wrong IP
            if "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
                # This is normal during discovery - might not be a Tapo camera or wrong creds
                logger.debug(f"  Not a Tapo camera at {ip} or wrong credentials")
                return None

            # Other errors - camera might be at this IP but has issues
            logger.debug(f"  Connection to {ip} failed: {error_msg}")
            return None

        if basic_info and "device_info" in basic_info:
            device_info = basic_info["device_info"]
            logger.info(f"✅ Found Tapo camera at {ip}")
            return {
                "ip": ip,
                "hostname": device_info.get("device_alias", ""),
                "model": device_info.get("device_model", "Unknown"),
                "firmware": device_info.get("firmware_version", "Unknown"),
                "serial": device_info.get("serial_number", "Unknown"),
                "mac": device_info.get("mac", "Unknown"),
            }
    except Exception as e:
        # Unexpected error - log but don't retry
        logger.debug(f"  Error checking {ip}: {e}")
        return None

    return None


def get_local_network() -> Optional[IPv4Network]:
    """Get the local network CIDR."""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # Doesn't need to be reachable
            s.connect(("10.254.254.254", 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        finally:
            s.close()

        # Get network interface info
        try:
            import netifaces

            gateways = netifaces.gateways()
            default_interface = gateways["default"][netifaces.AF_INET][1]
            addresses = netifaces.ifaddresses(default_interface)
            ip_info = addresses[netifaces.AF_INET][0]

            ip = ip_info["addr"]
            netmask = ip_info["netmask"]

            # Calculate network CIDR
            import ipaddress

            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            return network
        except ImportError:
            logger.warning("netifaces not installed. Trying alternative method...")
            # Fallback: assume /24 network
            import ipaddress

            ip_parts = local_ip.split(".")
            network_cidr = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
            return ipaddress.IPv4Network(network_cidr)
    except Exception:
        logger.exception("Error getting network info:")
        return None


def discover_tapo_cameras(
    username: str, password: str, network: Optional[str] = None, scan_common: bool = True
) -> List[dict]:
    """Discover Tapo cameras on the local network."""
    logger.info("🔍 Scanning network for Tapo cameras...")

    # Determine networks to scan
    networks_to_scan = []

    if network:
        import ipaddress

        try:
            networks_to_scan.append(ipaddress.IPv4Network(network))
        except ValueError:
            logger.exception("Invalid network CIDR:")
            return []
    else:
        # Get local network
        local_network = get_local_network()
        if local_network:
            networks_to_scan.append(local_network)

        # Also scan common network ranges if requested
        if scan_common:
            import ipaddress

            common_ranges = [
                "192.168.1.0/24",
                "192.168.0.0/24",
                "192.168.2.0/24",
                "10.0.0.0/24",
                "172.16.0.0/24",
            ]
            for cidr in common_ranges:
                try:
                    net = ipaddress.IPv4Network(cidr)
                    # Don't duplicate local network
                    if not local_network or str(net) != str(local_network):
                        networks_to_scan.append(net)
                except Exception:
                    continue

    if not networks_to_scan:
        logger.error("Could not determine networks to scan.")
        logger.info("Example: python discover_tapo_cameras.py --network 192.168.1.0/24")
        return []

    logger.info(
        f"Scanning {len(networks_to_scan)} network(s): {', '.join(str(n) for n in networks_to_scan[:3])}..."
    )

    # Scan all networks
    all_cameras = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for ip_network in networks_to_scan:
            for ip in ip_network.hosts():
                future = executor.submit(discover_tapo_on_ip, str(ip), username, password)
                futures.append(future)

        # Process futures as they complete
        import time
        from concurrent.futures import as_completed

        start_time = time.time()
        timeout = 300  # 5 minute total timeout

        for future in as_completed(futures, timeout=timeout):
            try:
                if time.time() - start_time > timeout:
                    break
                result = future.result(timeout=1.0)
                if result:
                    all_cameras.append(result)
                    logger.info(f"✅ Found camera at {result['ip']} - {result['model']}")
            except Exception:
                continue

    return all_cameras


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Discover Tapo cameras on local network")
    parser.add_argument("--username", "-u", required=True, help="Tapo account username (email)")
    parser.add_argument("--password", "-p", required=True, help="Tapo account password")
    parser.add_argument("--network", "-n", help="Network CIDR to scan (e.g., 192.168.1.0/24)")
    parser.add_argument("--output", "-o", help="Output file for camera config (YAML format)")

    args = parser.parse_args()

    # Discover cameras
    cameras = discover_tapo_cameras(args.username, args.password, args.network)

    if cameras:
        logger.info(f"\n✅ Found {len(cameras)} Tapo camera(s):\n")
        for cam in cameras:
            logger.info(f"  IP: {cam['ip']}")
            logger.info(f"  Hostname: {cam['hostname']}")
            logger.info(f"  Model: {cam['model']}")
            logger.info(f"  Firmware: {cam['firmware']}")
            logger.info(f"  Serial: {cam['serial']}")
            logger.info(f"  MAC: {cam['mac']}")
            logger.info()

        # Generate config YAML if requested
        if args.output:
            import yaml

            config = {"cameras": {}}
            for i, cam in enumerate(cameras, 1):
                camera_name = f"tapo_camera_{i}" if len(cameras) > 1 else "tapo_camera"
                config["cameras"][camera_name] = {
                    "type": "tapo",
                    "params": {
                        "host": cam["ip"],
                        "username": args.username,
                        "password": args.password,
                        "port": 443,
                        "verify_ssl": True,
                    },
                }

            with open(args.output, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"✅ Configuration saved to {args.output}")
    else:
        logger.warning("❌ No Tapo cameras found on the network.")
        logger.info("Make sure:")
        logger.info("  1. Camera is powered on and connected to WiFi")
        logger.info("  2. Credentials are correct")
        logger.info("  3. Camera is on the same network as this computer")


if __name__ == "__main__":
    # Handle event loop for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    main()
