"""
Command-line interface for Devices MCP (FastMCP 3.1).
"""

import argparse
import sys
import traceback
from typing import Any

from fastmcp import Client

from .core.server import DevicesMCPServer
from .transport import run_server, run_server_async

# ANSI color codes
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_END = "\033[0m"


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{COLOR_GREEN}[SUCCESS]{COLOR_END} {message}", file=sys.stderr)


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{COLOR_RED}[ERROR]{COLOR_END} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{COLOR_YELLOW}[WARNING]{COLOR_END} {message}", file=sys.stderr)


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{COLOR_BLUE}[INFO]{COLOR_END} {message}", file=sys.stderr)


class TapoCameraCLI:
    """Command-line interface for Devices MCP (FastMCP 3.1)."""

    def __init__(self):
        self.parser = self._create_parser()
        self.client = None

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(description="Devices MCP CLI (FastMCP 3.1)")
        parser.add_argument(
            "--url",
            default="http://localhost:8000",
            help="MCP server URL (default: http://localhost:8000)",
        )
        parser.add_argument(
            "--stdio", action="store_true", help="Use stdio transport instead of HTTP"
        )
        parser.add_argument("--debug", action="store_true", help="Enable debug output")

        # Subcommands (default to serve for MCP compatibility)
        subparsers = parser.add_subparsers(dest="command", required=False)
        parser.set_defaults(command="serve")

        # Server commands
        server_parser = subparsers.add_parser("serve", help="Start the MCP server")
        server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")  # nosec B104
        server_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
        server_parser.add_argument(
            "--no-stdio",
            action="store_false",
            dest="stdio",
            help="Disable stdio transport",
        )

        # Camera connection
        connect_parser = subparsers.add_parser("connect", help="Connect to a camera")
        connect_parser.add_argument("host", help="Camera IP address or hostname")
        connect_parser.add_argument("username", help="Camera username")
        connect_parser.add_argument("password", help="Camera password")

        # Camera commands
        camera_parser = subparsers.add_parser("camera", help="Camera operations")
        camera_subparsers = camera_parser.add_subparsers(dest="camera_command", required=True)

        # Camera info
        camera_subparsers.add_parser("info", help="Get camera information")

        # Camera status
        camera_subparsers.add_parser("status", help="Get camera status")

        # PTZ control
        ptz_parser = camera_subparsers.add_parser("ptz", help="PTZ control")
        ptz_parser.add_argument("action", choices=["move", "preset"], help="PTZ action")
        ptz_parser.add_argument("--pan", type=float, default=0.0, help="Pan position (-1.0 to 1.0)")
        ptz_parser.add_argument(
            "--tilt", type=float, default=0.0, help="Tilt position (-1.0 to 1.0)"
        )
        ptz_parser.add_argument(
            "--speed", type=float, default=0.5, help="Movement speed (0.1 to 1.0)"
        )

        # Stream control
        stream_parser = camera_subparsers.add_parser("stream", help="Stream operations")
        stream_parser.add_argument("action", choices=["start", "stop"], help="Action to perform")
        stream_parser.add_argument(
            "--quality", choices=["hd", "sd"], default="hd", help="Stream quality"
        )

        # Motion detection
        motion_parser = camera_subparsers.add_parser("motion", help="Motion detection control")
        motion_parser.add_argument(
            "action", choices=["enable", "disable", "status"], help="Action to perform"
        )

        # LED control
        led_parser = camera_subparsers.add_parser("led", help="LED control")
        led_parser.add_argument("action", choices=["on", "off", "status"], help="Action to perform")

        # Privacy mode
        privacy_parser = camera_subparsers.add_parser("privacy", help="Privacy mode control")
        privacy_parser.add_argument(
            "action", choices=["on", "off", "status"], help="Action to perform"
        )

        # Reboot
        camera_subparsers.add_parser("reboot", help="Reboot the camera")

        # Help command
        subparsers.add_parser("help", help="Show help for commands")

        return parser

    async def run(self, args=None):
        """Run the CLI."""
        if args is None:
            # Use parse_known_args to handle cases where no subcommand is provided
            args, unknown = self.parser.parse_known_args()

            # If no command was specified (which can happen with set_defaults), ensure it's serve
            if (
                not hasattr(args, "command")
                or args.command is None
                or args.command not in ["serve", "connect", "camera", "help"]
            ):
                args.command = "serve"

        try:
            # Handle help command
            if args.command == "help":
                self.parser.print_help()
                return 0

            # Handle serve command (start the server)
            if args.command == "serve":
                server = await DevicesMCPServer.get_instance()
                print_info(f"Starting Devices MCP server on {args.host}:{args.port}")
                if args.stdio:
                    print_info("Stdio transport enabled")
                await run_server_async(server.mcp, args, server_name="devices-mcp")
                return 0

            # For other commands, we need a client
            transport = "stdio" if args.stdio else "http"
            self.client = Client(transport=transport, url=args.url)

            # Handle connect command
            if args.command == "connect":
                return await self._handle_connect(args)

            # Handle camera commands
            if args.command == "camera":
                return await self._handle_camera(args)

        except Exception as e:
            if args.debug:
                traceback.print_exc()
            print_error(f"An error occurred: {e!s}")
            return 1
        else:
            # If we get here, the command is not implemented
            print_error(f"Command not implemented: {args.command}")
            return 1
        finally:
            if self.client:
                await self.client.close()

    async def _handle_connect(self, args) -> int:
        """Handle the connect command."""
        print_info(f"Connecting to camera at {args.host}...")
        result = await self.client.call_tool(
            "connect_camera",
            {"host": args.host, "username": args.username, "password": args.password},
        )

        if result.get("status") == "connected":
            print_success("Successfully connected to camera")
            self._print_json(result["camera_info"])
            return 0
        print_error(f"Failed to connect: {result.get('message', 'Unknown error')}")
        return 1

    async def _handle_camera(self, args) -> int:
        """Handle camera commands."""
        if args.camera_command == "info":
            info = await self.client.call_tool("get_camera_info", {})
            self._print_json(info.content)
            return 0

        if args.camera_command == "status":
            status = await self.client.call_tool("get_camera_status", {})
            self._print_json(status.content)
            return 0

        if args.camera_command == "ptz":
            if args.action == "move":
                result = await self.client.call_tool(
                    "move_ptz",
                    {"pan": args.pan, "tilt": args.tilt, "speed": args.speed},
                )
                if result.content.get("status") == "success":
                    print_success("PTZ movement completed")
                    return 0
                print_error(f"Failed to move PTZ: {result.content.get('message')}")
                return 1

        elif args.camera_command == "stream":
            if args.action == "start":
                result = await self.client.call_tool("get_stream_url", {"quality": args.quality})
                self._print_json(result.content)
                return 0
            # stop
            print_warning("Stream stop not yet implemented")
            return 0

        elif args.camera_command == "motion":
            if args.action == "enable":
                result = await self.client.call_tool("set_motion_detection", {"enabled": True})
            elif args.action == "disable":
                result = await self.client.call_tool("set_motion_detection", {"enabled": False})
            else:  # status
                status = await self.client.call_tool("get_camera_status", {})
                enabled = status.content.get("motion_detected", False)
                print_info(f"Motion detection is {'enabled' if enabled else 'disabled'}")
                return 0

            if result.content.get("status") == "success":
                state = "enabled" if args.action == "enable" else "disabled"
                print_success(f"Motion detection {state}")
                return 0
            print_error(f"Failed to {args.action} motion detection")
            return 1

        elif args.camera_command == "led":
            if args.action in ["on", "off"]:
                result = await self.client.call_tool(
                    "set_led_enabled", {"enabled": args.action == "on"}
                )
                if result.content.get("status") == "success":
                    print_success(f"LED turned {args.action}")
                    return 0
                print_error(f"Failed to turn LED {args.action}")
                return 1
            # status
            status = await self.client.call_tool("get_camera_status", {})
            enabled = status.content.get("led_enabled", False)
            print_info(f"LED is {'on' if enabled else 'off'}")
            return 0

        elif args.camera_command == "privacy":
            if args.action in ["on", "off"]:
                result = await self.client.call_tool(
                    "set_privacy_mode", {"enabled": args.action == "on"}
                )
                if result.content.get("status") == "success":
                    state = "enabled" if args.action == "on" else "disabled"
                    print_success(f"Privacy mode {state}")
                    return 0
                print_error(f"Failed to {args.action} privacy mode")
                return 1
            # status
            status = await self.client.call_tool("get_camera_status", {})
            enabled = status.content.get("privacy_mode", False)
            print_info(f"Privacy mode is {'on' if enabled else 'off'}")
            return 0

        elif args.camera_command == "reboot":
            confirm = input("Are you sure you want to reboot the camera? (y/N): ")
            if confirm.lower() != "y":
                print_info("Reboot cancelled")
                return 0

            result = await self.client.call_tool("reboot_camera", {})
            if result.content.get("status") == "success":
                print_success("Camera is rebooting...")
                return 0
            print_error("Failed to reboot camera")
            return 1

        else:
            print_error(f"Unknown camera command: {args.camera_command}")
            return 1
        return None

    def _print_json(self, data: Any) -> None:
        """Print data as formatted JSON."""
        if isinstance(data, dict) and "content" in data:
            data = data["content"]


async def main_async():
    """Async entry point for the CLI."""
    cli = TapoCameraCLI()

    # Handle MCP compatibility - if no arguments provided, default to serve
    import sys

    if len(sys.argv) == 1:
        # No arguments provided, run server directly for MCP compatibility
        server = await DevicesMCPServer.get_instance()
        print_info("Starting Devices MCP server (stdio mode)")
        # Run using unified transport
        await run_server_async(server.mcp, server_name="devices-mcp")
        return 0

    try:
        # For standard commands, we need a cli instance (which is not async until run)
        cli = TapoCameraCLI()
        # Use anyio or similar to run the async portion
        import anyio

        return anyio.run(cli.run)
    except SystemExit as e:
        if e.code == 2:
            print_info("No command specified, starting MCP server...")

            async def start_mcp():
                server = await DevicesMCPServer.get_instance()
                await run_server_async(server.mcp, server_name="devices-mcp")

            import anyio

            anyio.run(start_mcp)
            return 0
        raise


def main():
    """Entry point for the CLI."""
    # Special handling for MCP compatibility (no arguments)
    # run_server(FastMCP, server_name="devices-mcp") is synchronous and handles its own event loop
    if len(sys.argv) == 1:
        try:

            async def start_mcp():
                server = await DevicesMCPServer.get_instance()
                print_info("Starting Devices MCP server (stdio mode)")
                await run_server_async(server.mcp, server_name="devices-mcp")

            import anyio

            anyio.run(start_mcp)
            return 0
        except Exception as e:
            print_error(f"Failed to start MCP server: {e}")
            traceback.print_exc(file=sys.stderr)
            return 1

    # For other commands, use the standard async entry point
    return run_server(main_async, server_name="devices-mcp")


if __name__ == "__main__":
    sys.exit(main())
