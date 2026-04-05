#!/usr/bin/env python3
"""
Quick script to replace print statements with logger calls.
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def main():
    """Replace print statements in files that already have logging."""
    repo_root = Path(__file__).parent.parent

    # Only process files in src and scripts directories
    for root, dirs, files in os.walk(repo_root / "src"):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                replace_in_file(file_path)

    for root, dirs, files in os.walk(repo_root / "scripts"):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                replace_in_file(file_path)


def replace_in_file(file_path):
    """Replace print statements in a file that has logging."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Only process files that have logging setup
        if "import logging" in content and "logger =" in content:
            # Simple replacement: logger.info( -> logger.info(
            content = re.sub(r"\bprint\(", "logger.info(", content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Updated: {file_path}")

    except Exception as e:
        logger.info(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
