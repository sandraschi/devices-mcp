#!/usr/bin/env python3
import datetime
import logging
import os
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
REPO_ROOT = Path(__file__).parent.parent
BACKUP_DESTINATIONS = [
    Path(os.path.expanduser("~/OneDrive/Backup/repo-backups/devices-mcp")),
    # Add other destinations if needed as per original script
    Path("C:/Users/sandr/OneDrive/Backup/repo-backups/devices-mcp"),
    Path("D:/Backups/repo-backups/devices-mcp"),
]

RULES_FILE = REPO_ROOT / ".backup-rules.md"
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
BACKUP_NAME = f"devices-mcp_backup_{TIMESTAMP}.zip"


def load_exclusions():
    exclusions = []
    # Default exclusions
    exclusions.extend(
        [
            ".git",
            ".vs",
            ".vscode",
            ".idea",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
            "env",
            "*.zip",
            "*.7z",
            "*.rar",
            "*.bak",
            "*.tmp",
            "*.log",
        ]
    )

    if RULES_FILE.exists():
        with open(RULES_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("EXCLUDE:"):
                    rule = line.replace("EXCLUDE:", "").strip()
                    exclusions.append(rule)
    return exclusions


def should_exclude(path, root, exclusions):
    clean_path = str(path.relative_to(root)).replace("\\", "/")
    path_name = path.name

    for excl in exclusions:
        # Normalize exclusion pattern
        pattern = excl.replace("\\", "/")

        # Check basic name match
        if fnmatch_match(path_name, pattern):
            return True

        # Check path match
        if pattern in clean_path:
            return True

        # Check glob match
        if fnmatch_match(clean_path, pattern):
            return True

    return False


import fnmatch


def fnmatch_match(name, pattern):
    return fnmatch.fnmatch(name, pattern)


def get_files_to_backup(exclusions):
    files_to_backup = []

    # Walk top-level separately to Prune bad dirs early
    for root, dirs, files in os.walk(REPO_ROOT):
        root_path = Path(root)

        # Pruning directories in-place
        dirs[:] = [d for d in dirs if not should_exclude(root_path / d, REPO_ROOT, exclusions)]

        for file in files:
            file_path = root_path / file
            if not should_exclude(file_path, REPO_ROOT, exclusions):
                files_to_backup.append(file_path)

    return files_to_backup


def create_backup():
    logger.info(f"START: Starting backup for {REPO_ROOT.name}")
    exclusions = load_exclusions()
    logger.info(f"LIST: Loaded {len(exclusions)} exclusion rules")

    logger.info("SCAN: Scanning files...")
    files = get_files_to_backup(exclusions)
    logger.info(f"SUCCESS: Found {len(files)} files to backup")

    total_size = sum(f.stat().st_size for f in files)
    logger.info(f"SIZE: Total size: {total_size / 1024 / 1024:.2f} MB")

    for dest_dir in BACKUP_DESTINATIONS:
        dest_dir = Path(dest_dir)
        if not dest_dir.exists():
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.info(f"WARNING: Could not create backup dir {dest_dir}: {e}")
                continue

        backup_path = dest_dir / BACKUP_NAME
        logger.info(f"BACKUP: Creating backup at {backup_path}...")

        try:
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in files:
                    arcname = file.relative_to(REPO_ROOT)
                    zf.write(file, arcname)
            logger.info(f"SUCCESS: Backup created successfully: {backup_path}")
        except Exception as e:
            logger.info(f"ERROR: Failed to create backup at {dest_dir}: {e}")


if __name__ == "__main__":
    create_backup()
