"""CLI interface for Devices MCP."""

import argparse

from .utils.llms_txt import generate_llms_txt


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Devices MCP - Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # LLMs.txt generation command
    llms_parser = subparsers.add_parser("generate-llms", help="Generate LLMs.txt files")
    llms_parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Output directory for the LLMs.txt files (default: current directory)",
    )
    llms_parser.add_argument(
        "--base-url",
        type=str,
        default="https://github.com/yourusername/devices-mcp",
        help="Base URL for documentation links (default: GitHub repo)",
    )

    # Add more subcommands here as needed

    args = parser.parse_args()

    if args.command == "generate-llms":
        generate_llms_txt(output_dir=args.output_dir, base_url=args.base_url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
