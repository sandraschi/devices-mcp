#!/usr/bin/env python3
"""
Script to replace print() statements with logger calls across the repository.
"""

import os
import re
from pathlib import Path


def replace_prints_in_file(file_path):
    """Replace print statements with logger calls in a single file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Replace print statements with logger calls
    # Pattern: logger.info("...") -> logger.info("...")
    # Pattern: logger.info(f"...") -> logger.info(f"...")

    # Handle various print statement formats
    patterns = [
        # logger.info("message")
        (r'print\("([^"]*)"\)', r'logger.info("\1")'),
        # logger.info('message')
        (r"print\('([^']*)'\)", r"logger.info('\1')"),
        # logger.info(f"message")
        (r'print\(f"([^"]*)"\)', r'logger.info(f"\1")'),
        # logger.info(f'message')
        (r"print\(f'([^']*)'\)", r"logger.info(f'\1')"),
        # logger.info(variable)
        (r"print\((\w+)\)", r"logger.info(\1)"),
        # logger.info(f"format {var}")
        (r'print\((f["\'].*["\'])\)', r"logger.info(\1)"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

        # If we made changes, ensure logging is imported
    if content != original_content:
        # Check if logging is already imported
        if "import logging" not in content:
            # Find the import section
            import_match = re.search(r"^import|^from.*import", content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.end()
                content = content[:insert_pos] + "\nimport logging\n" + content[insert_pos:]
            else:
                # Add at top if no imports found
                content = "import logging\n\n" + content

        # Check if logger is defined
        if "logger = logging.getLogger(__name__)" not in content:
            # Find where to add it after imports
            lines = content.split("\n")
            insert_pos = 0

            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from ") or line.strip() == "":
                    continue
                insert_pos = i
                break

            lines.insert(insert_pos, "")
            lines.insert(insert_pos, "logger = logging.getLogger(__name__)")
            lines.insert(insert_pos, "")
            content = "\n".join(lines)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    """Main function to replace print statements across the repository."""
    import logging

    logger = logging.getLogger(__name__)
    repo_root = Path(__file__).parent.parent

    # File extensions to process
    extensions = [".py"]

    # Directories to skip
    skip_dirs = ["__pycache__", ".git", "node_modules", "dist", ".next"]

    processed_files = 0
    changed_files = 0

    for root, dirs, files in os.walk(repo_root):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                processed_files += 1

                if replace_prints_in_file(file_path):
                    changed_files += 1
                    logger.info(f"Updated: {file_path}")

    logger.info(f"\nProcessed {processed_files} files, updated {changed_files} files")


if __name__ == "__main__":
    main()
