"""
Hardware Initialization Module

Ensures all hardware (cameras, Hue, Tapo plugs, Netatmo, Ring) is properly
initialized and tested at startup with connection verification.
"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global singleton instance (will be initialized after class definition)
_hardware_initializer: Optional["HardwareInitializer"] = None


class HardwareInitializer:
    """Initialize and test all hardware connections at startup."""

    def __init__(self, camera_manager=None):
        self.camera_manager = camera_manager
        self.initialization_results: dict[str, dict] = {}
        self._initialized = False

    async def initialize_all(self) -> dict[str, dict]:
        """
        Initialize all hardware components and test connections.

        Returns:
            Dictionary with initialization results for each component
        """
        if self._initialized:
            return self.initialization_results

        # NOTE: Former lazy-loading check removed. We now handle timeouts/errors gracefully per-component.

        logger.info("=" * 60)
        logger.info("HARDWARE INITIALIZATION - Starting...")
        logger.info("=" * 60)

        # Log environment info for debugging
        import socket

        logger.info(f"Container environment: {os.getenv('CONTAINER', 'No')}")
        logger.info(f"Hostname: {socket.gethostname()}")
        try:
            host_ip = socket.gethostbyname(socket.gethostname())
            logger.info(f"Container IP: {host_ip}")
        except Exception as e:
            logger.debug(f"Could not determine container IP: {e}")

        # Test network connectivity to host network (for Docker debugging)
        if os.getenv("CONTAINER") == "yes":
            logger.info("Testing network connectivity to host network...")
            await self._test_network_connectivity()

        # Check config file location
        from ..config import get_config

        config = get_config()
        logger.info(f"Config loaded: {len(config)} top-level keys")
        logger.info(f"Cameras configured: {len(config.get('cameras', {}))}")
        logger.info(f"Hue configured: {bool(config.get('lighting', {}).get('philips_hue', {}).get('bridge_ip'))}")
        logger.info(
            f"Tapo lighting configured: {len(config.get('lighting', {}).get('tapo_lighting', {}).get('devices', []))}"
        )
        logger.info(f"Tapo plugs configured: {len(config.get('energy', {}).get('tapo_p115', {}).get('devices', []))}")
        logger.info(
            f"Netatmo enabled: {config.get('weather', {}).get('integrations', {}).get('netatmo', {}).get('enabled', False)}"
        )
        logger.info(f"Ring enabled: {config.get('ring', {}).get('enabled', False)}")

        # Initialize all hardware in parallel for speed
        # Network-dependent initializations have internal timeouts to prevent hangs
        results = await asyncio.gather(
            self._init_cameras(),
            self._init_hue_bridge(),
            self._init_tapo_lighting(),
            self._init_tapo_plugs(),
            self._init_netatmo(),
            self._init_ring(),
            self._init_home_assistant(),
            return_exceptions=True,
        )

        # Store results
        self.initialization_results = {
            "cameras": results[0]
            if not isinstance(results[0], Exception)
            else {"success": False, "error": str(results[0])},
            "hue_bridge": results[1]
            if not isinstance(results[1], Exception)
            else {"success": False, "error": str(results[1])},
            "tapo_lighting": results[2]
            if not isinstance(results[2], Exception)
            else {"success": False, "error": str(results[2])},
            "tapo_plugs": results[3]
            if not isinstance(results[3], Exception)
            else {"success": False, "error": str(results[3])},
            "netatmo": results[4]
            if not isinstance(results[4], Exception)
            else {"success": False, "error": str(results[4])},
            "ring": results[5]
            if not isinstance(results[5], Exception)
            else {"success": False, "error": str(results[5])},
            "home_assistant": results[6]
            if not isinstance(results[6], Exception)
            else {"success": False, "error": str(results[6])},
        }

        # Summary
        successful = sum(1 for r in self.initialization_results.values() if r.get("success", False))
        total = len(self.initialization_results)

        logger.info("=" * 60)
        logger.info(f"HARDWARE INITIALIZATION COMPLETE: {successful}/{total} components initialized")
        logger.info("=" * 60)

        for component, result in self.initialization_results.items():
            status = "[OK]" if result.get("success") else "[FAIL]"
            logger.info(f"  {status} {component}: {result.get('message', result.get('error', 'Unknown'))}")

        self._initialized = True
        return self.initialization_results

    async def _init_cameras(self) -> dict:
        """Initialize and test all cameras."""
        try:
            # Wrap entire camera init in timeout to ensure it doesn't block server startup
            return await asyncio.wait_for(self._init_cameras_internal(), timeout=15.0)
        except TimeoutError:
            logger.exception("[CAMERA] Initialization timed out after 15s")
            return {"success": False, "error": "Initialization timed out"}
        except Exception as e:
            logger.exception("[CAMERA] Unexpected error during initialization")
            return {"success": False, "error": str(e)}

    async def _init_cameras_internal(self) -> dict:
        """Internal camera initialization logic."""
        try:
            from ..config import get_config
            from ..core.server import TapoCameraServer

            logger.info("[CAMERA] Initializing cameras...")

            if self.camera_manager:
                camera_manager = self.camera_manager
            else:
                server = await TapoCameraServer.get_instance()
                camera_manager = server.camera_manager

            config = get_config()
            camera_configs = config.get("cameras", {})

            # Build YAML-driven cameras (may be empty). USB webcams are added only via
            # CameraManager.initialize(..., auto_discover_usb=True); the old path returned
            # early when cameras: {} was empty, so no usb_camera_* ever appeared in the API.
            camera_configs_list = []
            for cam_name, cam_config in camera_configs.items():
                if isinstance(cam_config, dict):
                    cam_config["name"] = cam_name
                    camera_configs_list.append(cam_config)

            auto_usb = os.environ.get("DEVICES_MCP_AUTO_DISCOVER_USB", "true").lower() in (
                "1",
                "true",
                "yes",
            )

            await camera_manager.initialize(
                configs=camera_configs_list or None,
                auto_discover_usb=auto_usb,
            )

            connected_count = 0
            failed_cameras = []

            # Test each camera connection
            cameras = await camera_manager.list_cameras()
            in_use_cameras = []

            for cam in cameras:
                cam_name = cam.get("name")
                status = cam.get("status", {})
                connected = status.get("connected", False) if isinstance(status, dict) else False
                in_use = status.get("in_use_by_another_app", False) if isinstance(status, dict) else False

                if in_use:
                    in_use_cameras.append(cam_name)
                    in_use_msg = (
                        status.get("in_use_error") or status.get("warning") or "Camera in use by another application"
                    )
                    logger.warning(f"  [WARN] Camera '{cam_name}': {in_use_msg}")
                elif connected:
                    connected_count += 1
                    logger.info(f"  [OK] Camera '{cam_name}': Connected")
                else:
                    failed_cameras.append(cam_name)
                    logger.warning(f"  [FAIL] Camera '{cam_name}': Not connected")

            # Build result message
            if in_use_cameras:
                message_parts = []
                if connected_count > 0:
                    message_parts.append(f"{connected_count} connected")
                if in_use_cameras:
                    message_parts.append(f"{len(in_use_cameras)} in use by other apps")
                if failed_cameras:
                    message_parts.append(f"{len(failed_cameras)} failed")
                message = f"{connected_count}/{len(cameras)} cameras ready ({', '.join(message_parts)})"
            elif connected_count == len(cameras):
                message = f"All {connected_count} cameras connected"
            else:
                message = f"{connected_count}/{len(cameras)} cameras connected"

            return {
                "success": len(cameras) > 0,
                "message": message,
                "count": connected_count,
                "failed": failed_cameras,
                "in_use": in_use_cameras,
                "cameras": [c.get("name") for c in cameras],
            }

        except Exception as e:
            logger.exception("Failed to initialize cameras")
            return {"success": False, "error": str(e)}

    async def _init_hue_bridge(self) -> dict:
        """Initialize and test Hue Bridge connection."""
        try:
            from ..config import get_config

            logger.info("[LIGHTING] Initializing Philips Hue Bridge...")

            config = get_config()
            hue_cfg = config.get("lighting", {}).get("philips_hue", {})
            from ..tools.lighting.hue_tools import load_hue_bridge_cache

            cache = load_hue_bridge_cache()
            bridge_ip = hue_cfg.get("bridge_ip") or cache.get("bridge_ip")
            if hue_cfg.get("enabled") is False:
                return {"success": True, "message": "Philips Hue not enabled in config"}

            if not bridge_ip:
                return {"success": False, "message": "Hue Bridge not configured (no bridge_ip or hue_bridge.cache)"}

            # Get the lazy-loaded manager
            from devices_mcp.tools.lighting.hue_tools import get_hue_manager

            hue_manager = get_hue_manager()

            # Initialize Hue manager
            if not hue_manager._initialized:
                success = await hue_manager.initialize()
                if not success:
                    return {
                        "success": False,
                        "error": hue_manager._connection_error or "Initialization failed",
                    }

            # Test connection by getting lights
            lights = hue_manager.lights
            groups = hue_manager.groups
            scenes = hue_manager.scenes

            logger.info(f"  [OK] Hue Bridge: {len(lights)} lights, {len(groups)} groups, {len(scenes)} scenes")

            return {
                "success": True,
                "message": f"Connected - {len(lights)} lights, {len(groups)} groups, {len(scenes)} scenes",
                "lights_count": len(lights),
                "groups_count": len(groups),
                "scenes_count": len(scenes),
                "bridge_ip": hue_manager._bridge_ip,
            }

        except Exception as e:
            logger.exception("Failed to initialize Hue Bridge")
            return {"success": False, "error": str(e)}

    async def _init_tapo_lighting(self) -> dict:
        """Initialize and test Tapo lighting devices."""
        try:
            from ..config import get_config
            from ..tools.lighting.tapo_lighting_tools import tapo_lighting_manager

            logger.info("[LIGHTING] Initializing Tapo smart lights...")

            config = get_config()
            tapo_cfg = config.get("lighting", {}).get("tapo_lighting", {})

            if not tapo_cfg:
                return {"success": False, "message": "Tapo lighting not configured"}

            devices_cfg = tapo_cfg.get("devices", [])
            if not devices_cfg:
                return {"success": False, "message": "No Tapo lighting devices configured"}

            # Initialize Tapo lighting manager
            if not tapo_lighting_manager._initialized:
                success = await tapo_lighting_manager.initialize()
                if not success:
                    return {
                        "success": False,
                        "error": tapo_lighting_manager._connection_error or "Initialization failed",
                    }

            # Test connection by rescanning devices (disabled - causing startup hang)
            # await tapo_lighting_manager.rescan_devices()
            lights = tapo_lighting_manager.devices

            logger.info(f"  [OK] Tapo Lighting: {len(lights)} lights")

            return {
                "success": True,
                "message": f"Connected - {len(lights)} lights",
                "lights_count": len(lights),
            }

        except Exception as e:
            logger.exception("Failed to initialize Tapo lighting")
            return {"success": False, "error": str(e)}

    async def _init_tapo_plugs(self) -> dict:
        """Initialize and test Tapo P115 smart plugs."""
        try:
            from ..config import get_config
            from ..tools.energy.tapo_plug_tools import tapo_plug_manager

            logger.info("[ENERGY] Initializing Tapo P115 smart plugs...")

            config = get_config()
            energy_cfg = config.get("energy", {}).get("tapo_p115", {})
            plugs_config = energy_cfg.get("devices", [])

            # Check if tapo library available
            try:
                import tapo
            except ImportError:
                return {"success": False, "error": "tapo library not installed"}

            account = energy_cfg.get("account", {})
            username = (
                account.get("username")
                or account.get("email")
                or os.getenv("TAPO_ACCOUNT_EMAIL")
                or os.getenv("TAPO_ACCOUNT_USERNAME")
            )
            password = account.get("password") or os.getenv("TAPO_ACCOUNT_PASSWORD")

            if not plugs_config:
                if not username or not password:
                    return {"success": True, "message": "No Tapo plugs configured", "count": 0}
                # Credentials without static devices[]: run manager + LAN discovery (see tapo_p115.discover_devices)
                if not tapo_plug_manager._initialized:
                    await tapo_plug_manager.initialize({})
                devices = await tapo_plug_manager.get_all_devices()
                return {
                    "success": len(devices) > 0,
                    "message": (
                        f"Discovered {len(devices)} plug(s)"
                        if devices
                        else "No plugs found (check LAN, TAPO_P115_BROADCAST, or add hosts)"
                    ),
                    "count": len(devices),
                }

            if not username or not password:
                return {"success": False, "error": "Tapo account credentials not configured"}

            # Initialize the manager
            if not tapo_plug_manager._initialized:
                await tapo_plug_manager.initialize(account)

            # Test each plug connection directly
            connected_count = 0
            failed_plugs = []

            for plug_cfg in plugs_config:
                device_id = plug_cfg.get("device_id", "unknown")
                name = plug_cfg.get("name", device_id)
                host = plug_cfg.get("host")

                if not host:
                    failed_plugs.append(name)
                    logger.warning(f"  [FAIL] Plug '{name}': No host configured")
                    continue

                try:
                    # Test connection directly
                    api_client = tapo.ApiClient(username, password)
                    device = await api_client.p115(host)
                    await device.get_device_info()  # Ensure device is accessible
                    energy = await device.get_energy_usage()

                    connected_count += 1
                    power = energy.current_power if energy and hasattr(energy, "current_power") else 0
                    logger.info(f"  [OK] Plug '{name}' ({host}): Connected - {power}W")
                except Exception as e:
                    failed_plugs.append(name)
                    error_msg = str(e)
                    logger.warning(f"  [FAIL] Plug '{name}' ({host}): {error_msg}")

            if connected_count == len(plugs_config):
                return {
                    "success": True,
                    "message": f"All {connected_count} plugs connected",
                    "count": connected_count,
                }
            return {
                "success": connected_count > 0,
                "message": f"{connected_count}/{len(plugs_config)} plugs connected",
                "count": connected_count,
                "failed": failed_plugs,
            }

        except Exception as e:
            logger.exception("Failed to initialize Tapo plugs")
            return {"success": False, "error": str(e)}

    async def _init_netatmo(self) -> dict:
        """Initialize and test Netatmo weather station."""
        try:
            from ..config import get_config
            from ..integrations.netatmo_client import NetatmoService

            logger.info("[WEATHER] Initializing Netatmo weather station...")

            config = get_config()
            weather_cfg = config.get("weather", {}).get("integrations", {}).get("netatmo", {})

            if not weather_cfg.get("enabled"):
                return {"success": True, "message": "Netatmo not enabled in config"}

            # Check if pyatmo available
            import importlib.util

            if importlib.util.find_spec("pyatmo") is None:
                return {"success": False, "error": "pyatmo library not installed"}

            service = None
            try:
                # Use singleton pattern to share instance with web API
                service = await asyncio.wait_for(NetatmoService.get_instance(), timeout=3.0)

                if not service._use_real_api:
                    err = service.last_error or (
                        "Netatmo weather station unavailable — authentication or network issues"
                    )
                    return {"success": False, "error": err}

                # Test connection by getting stations with timeout (reduced from 5s to 2s)
                stations = await asyncio.wait_for(service.list_stations(), timeout=2.0)
                station_count = len(stations)
                module_count = sum(len(s.get("modules", [])) for s in stations)

                logger.info(f"  [OK] Netatmo: {station_count} stations, {module_count} modules")

                return {
                    "success": True,
                    "message": f"Connected - {station_count} stations, {module_count} modules",
                    "stations_count": station_count,
                    "modules_count": module_count,
                }
            except TimeoutError:
                error_msg = "Connection timeout - network/DNS issue"
                logger.warning(f"  [TIMEOUT] Netatmo initialization: {error_msg}")
                return {"success": False, "error": error_msg}
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                logger.exception("  [ERROR] Netatmo initialization failed:")
                # Don't mask DNS errors - let them propagate so they can be fixed
                return {"success": False, "error": f"{error_type}: {error_msg}"}
            # Do not close NetatmoService here: it is a process singleton shared with the web API.

        except Exception as e:
            logger.exception("Failed to initialize Netatmo")
            return {"success": False, "error": str(e)}

    async def _init_ring(self) -> dict:
        """Initialize and test Ring doorbell."""
        try:
            from ..config import get_config
            from ..integrations.ring_client import get_ring_client

            logger.info("[SECURITY] Initializing Ring doorbell...")

            config = get_config()
            ring_cfg = config.get("ring", {})

            if not ring_cfg.get("enabled"):
                return {"success": True, "message": "Ring not enabled in config"}

            # Initialize Ring client if not already done
            ring_client = get_ring_client("default")
            if not ring_client:
                # Initialize the Ring client with config credentials
                from ..integrations.ring_client import init_ring_client

                email = ring_cfg.get("email")
                password = ring_cfg.get("password")
                token_file = ring_cfg.get("token_file", "ring_token.cache")
                cache_ttl = ring_cfg.get("cache_ttl", 60)

                if not email or not password:
                    return {"success": False, "error": "Ring email/password not configured"}

                try:
                    ring_client = await init_ring_client(
                        email=email,
                        password=password,
                        token_file=token_file,
                        cache_ttl=cache_ttl,
                        server_id="default",
                    )

                    if not ring_client.is_initialized and not ring_client.is_2fa_pending:
                        err = ring_client.last_error or "Ring initialization failed"
                        return {"success": False, "error": err}
                except Exception as e:
                    return {"success": False, "error": f"Ring initialization error: {e}"}

            if not ring_client:
                return {"success": False, "error": "Failed to initialize Ring client"}

            # Try to get devices with timeout (reduced from 8s to 3s)
            try:
                # Get only doorbells (cameras) - alarm devices don't have cameras
                doorbells = await asyncio.wait_for(ring_client.get_doorbells(), timeout=3.0)
                devices = doorbells or []
                device_count = len(devices)

                logger.info(f"  [OK] Ring: {device_count} cameras")

                # Register Ring cameras with the camera manager
                for device in devices:
                    camera_config = {
                        "name": f"ring_{device.id}",
                        "type": "ring",
                        "params": {
                            "device_id": device.id,
                            "token_file": str(ring_client.token_file),
                            "username": email,
                            "password": password,
                        },
                    }
                    try:
                        await self.camera_manager.add_camera(camera_config)
                        logger.info(f"Registered Ring camera: {camera_config['name']}")
                    except Exception as e:
                        logger.warning(f"Failed to register Ring camera {device.id}: {e}")

                return {
                    "success": True,
                    "message": f"Connected - {device_count} cameras",
                    "devices_count": device_count,
                }
            except TimeoutError:
                error_msg = "Connection timeout - network/DNS issue"
                logger.warning(f"  [TIMEOUT] Ring: {error_msg}")
                return {"success": False, "error": error_msg}
            except Exception as e:
                logger.warning(f"  [FAIL] Ring: {e!s}")
                return {"success": False, "error": str(e)}

        except Exception as e:
            logger.exception("Failed to initialize Ring")
            return {"success": False, "error": str(e)}

    async def _init_home_assistant(self) -> dict:
        """Initialize and test Home Assistant connection (for Nest Protect)."""
        try:
            from ..config import get_config
            from ..integrations.homeassistant_client import init_homeassistant_client

            logger.info("[SECURITY] Initializing Home Assistant (Nest Protect)...")

            config = get_config()
            security_cfg = config.get("security", {}).get("integrations", {})
            ha_cfg = security_cfg.get("homeassistant", {})

            if not ha_cfg.get("enabled"):
                return {"success": True, "message": "Home Assistant not enabled in config"}

            url = ha_cfg.get("url", "http://localhost:8123")
            token = ha_cfg.get("access_token")

            if not token:
                return {"success": False, "error": "Home Assistant access token not configured"}

            # Initialize client (will auto-detect Docker and adjust URL)
            client = await init_homeassistant_client(
                base_url=url, access_token=token, cache_ttl=ha_cfg.get("cache_ttl", 30)
            )

            if not client or not client.is_initialized:
                return {"success": False, "error": "Failed to connect to Home Assistant"}

            # Test by getting Nest Protect devices
            try:
                devices = await client.get_nest_protect_devices()
                device_count = len(devices) if devices else 0

                logger.info(f"  [OK] Home Assistant: Connected - {device_count} Nest Protect device(s)")

                return {
                    "success": True,
                    "message": f"Connected - {device_count} Nest Protect device(s)",
                    "devices_count": device_count,
                    "url": url,
                }
            except Exception as e:
                logger.warning(f"  [WARN] Home Assistant: Connected but no Nest devices found: {e!s}")
                return {
                    "success": True,  # Connection works, just no devices
                    "message": "Connected but no Nest Protect devices found",
                    "devices_count": 0,
                    "url": url,
                }

        except Exception as e:
            logger.exception("Failed to initialize Home Assistant")
            return {"success": False, "error": str(e)}

    async def _test_network_connectivity(self) -> None:
        """Test network connectivity to common device IPs for Docker debugging."""
        import asyncio
        import socket

        from ..config import get_config

        config = get_config()

        # Collect device IPs from config
        test_ips = []

        # Camera IPs
        cameras = config.get("cameras", {})
        for cam_name, cam_cfg in cameras.items():
            if cam_cfg.get("type") == "onvif":
                host = cam_cfg.get("params", {}).get("host")
                if host:
                    test_ips.append(("camera", cam_name, host))

        # Hue Bridge IP
        hue_cfg = config.get("lighting", {}).get("philips_hue", {})
        bridge_ip = hue_cfg.get("bridge_ip")
        if bridge_ip:
            test_ips.append(("hue_bridge", "Hue Bridge", bridge_ip))

        # Home Assistant (for Nest Protect)
        security_cfg = config.get("security", {}).get("integrations", {})
        ha_cfg = security_cfg.get("homeassistant", {})
        if ha_cfg.get("enabled"):
            ha_url = ha_cfg.get("url", "http://localhost:8123")
            # Extract hostname from URL
            try:
                from urllib.parse import urlparse

                parsed = urlparse(ha_url)
                ha_host = parsed.hostname or "localhost"
                # Only test if it's an IP or known hostname (not localhost in Docker)
                if ha_host and ha_host not in ["localhost", "127.0.0.1"]:
                    test_ips.append(("home_assistant", "Home Assistant", ha_host))
            except Exception as e:
                logger.debug(f"Could not parse Home Assistant URL: {e}")

        # Tapo Plug IPs
        energy_cfg = config.get("energy", {}).get("tapo_p115", {})
        plugs = energy_cfg.get("devices", [])
        for plug in plugs:
            host = plug.get("host")
            name = plug.get("name", "Unknown")
            if host:
                test_ips.append(("tapo_plug", name, host))

        if not test_ips:
            logger.info("  [NETWORK] No device IPs configured for connectivity test")
            return

        logger.info(f"  [NETWORK] Testing connectivity to {len(test_ips)} device(s)...")

        async def test_ip(device_type: str, name: str, ip: str) -> tuple[str, str, bool, str]:
            """Test if we can reach an IP address."""
            try:
                # Try to resolve the IP (if it's a hostname)
                try:
                    resolved_ip = socket.gethostbyname(ip)
                except socket.gaierror:
                    return (device_type, name, False, f"DNS resolution failed for {ip}")

                # Try to connect to common ports
                ports_to_test = [80, 443, 2020, 9999]  # HTTP, HTTPS, ONVIF, Kasa
                reachable = False
                error_msg = "No reachable ports"

                for port in ports_to_test:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((resolved_ip, port))
                        sock.close()
                        if result == 0:
                            reachable = True
                            error_msg = f"Port {port} reachable"
                            break
                    except Exception:
                        continue

                if reachable:
                    return (device_type, name, True, error_msg)
                return (device_type, name, False, error_msg)
            except Exception as e:
                return (device_type, name, False, str(e))

        # Test all IPs in parallel
        results = await asyncio.gather(*[test_ip(dt, n, ip) for dt, n, ip in test_ips], return_exceptions=True)

        # Log results
        reachable_count = 0
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"  [NETWORK] Connectivity test error: {result}")
                continue

            device_type, name, reachable, msg = result
            if reachable:
                logger.info(f"  [NETWORK] OK {name} ({device_type}): {msg}")
                reachable_count += 1
            else:
                logger.warning(f"  [NETWORK] FAILED {name} ({device_type}): {msg}")

        if reachable_count == len(test_ips):
            logger.info(f"  [NETWORK] All {reachable_count} device(s) reachable from container")
        elif reachable_count > 0:
            logger.warning(
                f"  [NETWORK] {reachable_count}/{len(test_ips)} device(s) reachable - check network configuration"
            )
        else:
            logger.error("  [NETWORK] No devices reachable - Docker network may not have access to host network")
            logger.error(
                "  [NETWORK] Check: docker-compose.yml network configuration, Windows Firewall, router settings"
            )


# Lock to prevent concurrent initialization
_init_lock = asyncio.Lock()


async def initialize_all_hardware(camera_manager) -> dict[str, dict]:
    """Initialize all hardware components at startup."""
    global _hardware_initializer

    # Use lock to prevent concurrent initialization
    async with _init_lock:
        if _hardware_initializer is None:
            _hardware_initializer = HardwareInitializer(camera_manager)
        elif _hardware_initializer._initialized:
            # Already initialized, return cached results
            return _hardware_initializer.initialization_results
        return await _hardware_initializer.initialize_all()


def get_initialization_results() -> dict[str, dict]:
    """Get hardware initialization results."""
    if _hardware_initializer:
        return _hardware_initializer.initialization_results
    return {}
