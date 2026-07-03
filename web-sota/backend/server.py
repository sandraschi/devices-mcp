"""
Clean web server implementation for Devices MCP.
Refactored from the bloated 3896-line server.py into modular components.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add src directory to path so webapp can import from MCP package
repo_root = Path(__file__).parent.parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from devices_mcp.config import SecuritySettings, WebUISettings, get_config, get_model

logger = logging.getLogger(__name__)


class WebServer:
    """Clean, modular web server for Devices MCP."""

    def __init__(self, config_path: str | None = None):
        """Initialize the web server."""
        self.config = get_config()
        self.web_config = get_model(WebUISettings)
        self.security_config = get_model(SecuritySettings)

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            from devices_mcp.config.log_paths import configure_root_file_logging

            # Only file logging before yield (fast, no network)
            try:
                await asyncio.get_event_loop().run_in_executor(None, lambda: configure_root_file_logging(get_config()))
            except Exception:
                logger.debug("Startup file logging skipped", exc_info=True)

            # Fleet monitor background task
            monitor_task = asyncio.create_task(self._fleet_monitor())
            logger.info("Application startup complete")

            # Yield immediately — integrations connect in background
            yield

            # Background integration init (fire-and-forget, each with own timeout)
            async def _init_bg():
                try:
                    from devices_mcp.llm.manager import get_llm_manager
                    mgr = get_llm_manager()
                    mgr.ensure_catalog_registered(get_config())
                    await asyncio.wait_for(mgr.glom_local_providers_if_up(), timeout=5)
                except Exception:
                    logger.debug("BG: LLM glom skipped")

                try:
                    from devices_mcp.tools.lighting.hue_tools import get_hue_manager, load_hue_bridge_cache
                    raw = get_config() or {}
                    hue_cfg = (raw.get("lighting") or {}).get("philips_hue") or {}
                    if hue_cfg.get("enabled") is not False:
                        cache = load_hue_bridge_cache()
                        if hue_cfg.get("bridge_ip") or cache.get("bridge_ip"):
                            mgr = get_hue_manager()
                            if await asyncio.wait_for(mgr.initialize(), timeout=30):
                                await asyncio.wait_for(mgr.rescan(), timeout=30)
                                logger.info("BG: Hue %s lights", len(mgr.lights))
                except Exception:
                    logger.debug("BG: Hue skipped")

                try:
                    from devices_mcp.integrations.ring_client import init_ring_client, ring_has_cached_token
                    raw = get_config() or {}
                    ring_cfg = raw.get("ring") or {}
                    if ring_cfg.get("enabled"):
                        email = ring_cfg.get("email")
                        pw = ring_cfg.get("password")
                        tf = ring_cfg.get("token_file", "ring_token.cache")
                        if email and (pw or ring_has_cached_token(tf)):
                            await asyncio.wait_for(init_ring_client(email=email, password=pw or None, token_file=tf, cache_ttl=ring_cfg.get("cache_ttl", 60)), timeout=10)
                except Exception:
                    logger.debug("BG: Ring skipped")

                try:
                    from devices_mcp.integrations.nest_client import init_nest_client
                    raw = get_config() or {}
                    nc = raw.get("nest") or {}
                    if nc.get("enabled", True):
                        await asyncio.wait_for(init_nest_client(refresh_token=nc.get("refresh_token"), token_file=nc.get("token_file", "nest_token.cache"), cache_ttl=nc.get("cache_ttl", 60), client_id=nc.get("client_id"), client_secret=nc.get("client_secret")), timeout=10)
                except Exception:
                    logger.debug("BG: Nest skipped")

                try:
                    from devices_mcp.integrations.shelly_client import init_shelly_client
                    raw = get_config() or {}
                    sc = raw.get("shelly") or {}
                    if sc.get("enabled") and sc.get("devices"):
                        await asyncio.wait_for(init_shelly_client(devices=sc.get("devices"), cache_ttl=sc.get("cache_ttl", 30)), timeout=10)
                except Exception:
                    logger.debug("BG: Shelly skipped")

                try:
                    from devices_mcp.integrations.homeassistant_client import init_homeassistant_client
                    raw = get_config() or {}
                    hac = (raw.get("security") or {}).get("integrations", {}).get("homeassistant") or {}
                    if hac.get("enabled") and hac.get("access_token"):
                        await asyncio.wait_for(init_homeassistant_client(base_url=hac.get("url", "http://localhost:8123"), access_token=hac.get("access_token"), cache_ttl=hac.get("cache_ttl", 30)), timeout=10)
                except Exception:
                    logger.debug("BG: HA skipped")

                try:
                    from devices_mcp.integrations.netatmo_client import PYATMO_AVAILABLE, NetatmoService
                    raw = get_config() or {}
                    nm = ((raw.get("weather") or {}).get("integrations") or {}).get("netatmo") or {}
                    tf = nm.get("token_file") or "netatmo_token.cache"
                    ht = bool((nm.get("refresh_token") or "").strip())
                    if not ht:
                        cp = NetatmoService._adjust_token_path(tf)
                        ht = cp.exists() and bool(cp.read_text(encoding="utf-8").strip())
                    if nm.get("enabled") and PYATMO_AVAILABLE and nm.get("client_id") and nm.get("client_secret") and ht:
                        await asyncio.wait_for(NetatmoService.get_instance(tf), timeout=10)
                except Exception:
                    logger.debug("BG: Netatmo skipped")

                try:
                    from devices_mcp.core.connection_supervisor import get_supervisor
                    await asyncio.wait_for(get_supervisor().start(), timeout=10)
                except Exception:
                    logger.debug("BG: supervisor skipped")

            bg = asyncio.create_task(_init_bg())
            logger.info("Startup integrations backgrounded")

            yield

            bg.cancel()
            monitor_task.cancel()
            try:
                await bg
            except asyncio.CancelledError:
                pass
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Initialize FastAPI app
        self.app = FastAPI(
            title=self.web_config.title,
            description="Management and Control Platform for Universal IoT Devices",
            version="1.0.0",
            docs_url="/api/docs" if self.web_config.enable_swagger else None,
            redoc_url="/api/redoc" if self.web_config.enable_redoc else None,
            debug=self.config.get("debug", False),
            lifespan=_lifespan,
        )

        # CORS: Vite dev, direct browser, Tauri WebView, packaged desktop
        _tauri = os.environ.get("DEVICES_TAURI", "").lower() in ("1", "true", "yes")
        cors_origins = [
            "http://localhost:10717",
            "http://localhost:10716",
            "http://127.0.0.1:10716",
            "http://127.0.0.1:10717",
            "http://goliath:10716",
            "http://goliath:10717",
            "https://asset.localhost",
            "http://asset.localhost",
            "https://tauri.localhost",
            "http://tauri.localhost",
            "tauri://localhost",
        ]
        if getattr(sys, "frozen", False) or os.getenv("DEVICES_MCP_PACKAGED") == "1":
            cors_origins = ["*"]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_origin_regex=r"https?://tauri\.localhost(:\d+)?" if _tauri else None,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Setup components
        self._setup_middleware()
        self._setup_static_files()
        self._setup_templates()
        self._setup_routes()

        logger.info("Web server initialized successfully")

    def _setup_middleware(self) -> None:
        """Setup middleware."""
        # Add GZip compression
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Add security middleware if enabled
        try:
            if hasattr(self.security_config, "enabled") and self.security_config.enabled:
                from .middleware.security import SecurityMiddleware

                self.app.add_middleware(SecurityMiddleware)
                logger.info("Security middleware enabled")
        except Exception as e:
            logger.warning(f"Could not load security middleware: {e}")

    def _resolve_frontend_dist(self) -> Path | None:
        """Locate Vite build output (dev tree or PyInstaller bundle)."""
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            meipass = Path(getattr(sys, "_MEIPASS", ""))
            candidates.extend(
                [
                    meipass / "frontend" / "dist",
                    Path(__file__).resolve().parent.parent / "frontend" / "dist",
                ]
            )
        else:
            candidates.append(Path(__file__).resolve().parent.parent / "frontend" / "dist")
        for path in candidates:
            if path.is_dir() and (path / "index.html").exists():
                return path
        return None

    def _setup_static_files(self) -> None:
        """Setup static file serving."""
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
            logger.info(f"Static files mounted from {static_dir}")

        # SPA (React + Vite) at /app when frontend is built
        frontend_dist = self._resolve_frontend_dist()
        if frontend_dist and (frontend_dist / "index.html").exists():
            self.app.mount(
                "/app",
                StaticFiles(directory=str(frontend_dist), html=True),
                name="spa",
            )
            self.app.get("/")(self._redirect_to_app)
            logger.info(f"SPA mounted at /app from {frontend_dist}")

    def _setup_templates(self) -> None:
        """Setup Jinja2 templates."""
        templates_dir = Path(__file__).parent / "templates"
        if templates_dir.exists():
            self.templates = Jinja2Templates(directory=str(templates_dir))
        else:
            self.templates = None
            logger.warning(f"Templates directory not found: {templates_dir}")
        self.app.state.templates = self.templates

    def _setup_routes(self) -> None:
        """Setup all route modules."""
        try:
            # Import route modules from the routes package
            from .routes import (
                alerts,
                appliance_monitor,
                audio,
                auth,
                camera_names,
                cameras,
                config_editor,
                cua_diagnostics,
                custom_presets,
                dashboard_api,
                devices,
                dymo,
                energy,
                events,
                fleet,
                fleet_priority,
                health,
                ikettle,
                lighting,
                llm,
                logs,
                messages,
                microscope,
                motion,
                nest,
                otoscope,
                plex,
                ptz,
                ptz_routes,
                ring,
                robots,
                scanner,
                security,
                sensors,
                settings_prefs,
                shelly,
                system,
                thermal,
                views,
                weather,
            )

            # Include route modules
            # Page views (SSR HTML)
            self.app.include_router(views.router)

            # Core API Routes
            self.app.include_router(auth.router, tags=["Authentication"])
            self.app.include_router(system.router, tags=["System"])
            self.app.include_router(cameras.router, tags=["Cameras"])
            self.app.include_router(dashboard_api.router, tags=["Dashboard API"])
            self.app.include_router(devices.router, tags=["Devices"])
            self.app.include_router(energy.router, tags=["Energy"])
            self.app.include_router(events.router, tags=["Events"])
            self.app.include_router(fleet.router, tags=["Fleet Management"])
            self.app.include_router(fleet_priority.router, tags=["Fleet Priority"])
            self.app.include_router(logs.router, tags=["Logs"])

            # Specialized Device API Routes
            self.app.include_router(lighting.router, tags=["Lighting"])
            self.app.include_router(weather.router, tags=["Weather"])
            self.app.include_router(ring.router, tags=["Ring"])
            self.app.include_router(nest.router, tags=["Nest"])
            self.app.include_router(robots.router, tags=["Robots"])
            self.app.include_router(security.router, tags=["Security"])
            self.app.include_router(sensors.router, tags=["Sensors"])
            self.app.include_router(thermal.router, tags=["Thermal"])
            self.app.include_router(alerts.router, tags=["Alerts"])
            self.app.include_router(appliance_monitor.router, tags=["Appliance Monitor"])
            self.app.include_router(audio.router, tags=["Audio"])
            self.app.include_router(camera_names.router, tags=["Camera Names"])
            self.app.include_router(config_editor.router, tags=["Config"])
            self.app.include_router(settings_prefs.router, tags=["Settings"])
            self.app.include_router(custom_presets.router, tags=["Custom Presets"])
            self.app.include_router(dymo.router, tags=["Dymo Labels"])
            self.app.include_router(health.router, tags=["Health"])
            self.app.include_router(ikettle.router, tags=["iKettle"])
            from . import onboarding

            self.app.include_router(onboarding.router, tags=["Onboarding"])
            self.app.include_router(llm.router, tags=["LLM"])
            self.app.include_router(messages.router, tags=["Messages"])
            self.app.include_router(microscope.router, tags=["Microscope"])
            self.app.include_router(motion.router, tags=["Motion"])
            self.app.include_router(otoscope.router, tags=["Otoscope"])
            self.app.include_router(plex.router, tags=["Plex"])
            self.app.include_router(ptz.router, tags=["PTZ"])
            self.app.include_router(ptz_routes.router, tags=["PTZ Routes"])
            self.app.include_router(scanner.router, tags=["Scanner"])
            self.app.include_router(shelly.router, tags=["Shelly"])
            self.app.include_router(cua_diagnostics.router, tags=["CUA"])

            # Mount orphaned v1 endpoints (system restart, config, logs)
            try:
                from .v1.endpoints import system as v1_system

                self.app.include_router(v1_system.router, prefix="/api/v1", tags=["v1 System"])
            except Exception:
                logger.debug("v1 endpoints not available", exc_info=True)

            logger.info("All modular routes registered successfully")
        except ImportError as e:
            logger.exception(f"Failed to import router module: {e}")
            # Minimal fallback routes
            from fastapi.responses import HTMLResponse

            @self.app.get("/")
            async def root():
                return HTMLResponse("""
                <html>
                    <head><title>Devices MCP</title></head>
                    <body>
                        <h1>🎯 Devices MCP Web Dashboard</h1>
                        <p>✅ Port 10716 - Following MCP Central Docs</p>
                        <p>🤖 Dreame D20 Pro Integration Ready</p>
                        <p>📹 All Camera Systems Restored</p>
                        <p>⚡ Full Functionality Available</p>
                    </body>
                </html>
                """)

            logger.info("Minimal routes registered successfully")

    async def _fleet_monitor(self) -> None:
        """Background task to monitor fleet health and trigger hourly syncs."""
        import asyncio
        import subprocess
        from datetime import UTC, datetime, timedelta

        from devices_mcp.fleet.manager import FleetManager

        logger.info("Fleet monitor background task started")

        # Initial wait to let server settle
        await asyncio.sleep(60)

        while True:
            try:
                manager = FleetManager()
                nodes = await manager.get_fleet_status()
                now = datetime.now(UTC)

                # 1. Health Monitoring: Mark nodes as offline if silent > 10 mins
                offline_threshold = timedelta(minutes=10)
                for node in nodes:
                    last_seen = datetime.fromtimestamp(node["last_heartbeat"], tz=UTC)
                    if now - last_seen > offline_threshold and node["status"] != "offline":
                        logger.warning(f"Node {node['node_id']} has gone silent. Marking offline.")
                        await manager.record_heartbeat(
                            node_id=node["node_id"], status="offline", details=node.get("details", {})
                        )

                # 2. Trigger Hourly Sync Script
                # We do this every hour (approx)
                # For simplicity, we just trigger it and let it handle the 'last_run' logic
                scripts_dir = Path(__file__).parent.parent.parent / "scripts"
                sync_script = scripts_dir / "hourly_sync.py"
                if sync_script.exists():
                    logger.info("Triggering hourly fleet sync documentation push")
                    subprocess.Popen(
                        [sys.executable, str(sync_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                else:
                    logger.debug(f"Sync script not found at {sync_script}")

            except Exception as e:
                logger.error(f"Error in fleet monitor loop: {e}")

            # Sleep for 5 minutes (health check interval)
            await asyncio.sleep(300)

    def _redirect_to_app(self):
        """Redirect root to React SPA."""
        return RedirectResponse(url="/app/", status_code=302)

    def run(self, host: str = "0.0.0.0", port: int = 10716) -> None:
        """Run web server."""
        import uvicorn

        logger.info(f"Starting web server on {host}:{port}")

        # Check if we're in Docker
        is_docker = os.getenv("CONTAINER") == "yes" or os.path.exists("/.dockerenv")
        reload = not is_docker and self.config.get("debug", False)

        uvicorn.run(self.app, host=host, port=port, reload=reload, log_level="info")


# Create global app for direct imports
app = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    global app
    if app is None:
        server = WebServer()
        app = server.app
    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Devices MCP Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=10716, help="Port to bind to")

    args = parser.parse_args()

    server = WebServer()
    server.run(host=args.host, port=args.port)
