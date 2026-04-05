#!/usr/bin/env python3
"""
Final cleanup script to add logging to all Python files and replace print statements.
"""

import os
import re
from pathlib import Path


def process_file(file_path):
    """Process a single Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        modified = False

        # Skip files that are already processed
        if "import logging" in content and "logger = logging.getLogger(__name__)" in content:
            return False

        # Skip files that don't have print statements
        if "print(" not in content:
            return False

        # Add logging import and logger
        if "import logging" not in content:
            # Find the first import line
            lines = content.split("\n")
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_pos = i + 1
                elif (
                    line.strip()
                    and not line.startswith("#")
                    and not line.startswith('"""')
                    and not line.startswith("'''")
                ):
                    break

            # Insert logging import
            lines.insert(insert_pos, "import logging")
            lines.insert(insert_pos + 1, "")
            lines.insert(insert_pos + 2, "logger = logging.getLogger(__name__)")
            lines.insert(insert_pos + 3, "")

            content = "\n".join(lines)
            modified = True

        # Replace print statements with logger calls
        content = re.sub(r"\bprint\(", "logger.info(", content)
        if content != original_content:
            modified = True

        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    except Exception as e:
        logger.info(f"Error processing {file_path}: {e}")

    return False


def main():
    """Process all Python files in src and scripts directories."""
    repo_root = Path(__file__).parent.parent

    processed = 0
    updated = 0

    # Process src directory
    for root, dirs, files in os.walk(repo_root / "src"):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__"]]
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                processed += 1
                if process_file(file_path):
                    updated += 1
                    logger.info(f"Updated: src/{file_path.relative_to(repo_root / 'src')}")

    # Process scripts directory
    for root, dirs, files in os.walk(repo_root / "scripts"):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__"]]
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                processed += 1
                if process_file(file_path):
                    updated += 1
                    logger.info(f"Updated: scripts/{file_path.relative_to(repo_root / 'scripts')}")

    logger.info(f"\nProcessed {processed} files, updated {updated} files")


if __name__ == "__main__":
    main()
