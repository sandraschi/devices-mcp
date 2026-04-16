#!/usr/bin/env python3
"""
Hourly Fleet Synchronization Script.
Generates fleet reports (Markdown) and registries (JSON) and pushes them to Git.
"""

import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hourly_sync")

# Add src to path
repo_root = Path(__file__).parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from devices_mcp.fleet.manager import FleetManager


async def run_sync():
    logger.info("Starting hourly fleet sync")

    manager = FleetManager()
    nodes = await manager.get_fleet_status()
    now = datetime.now(UTC)

    # 1. Generate JSON Registry
    registry_path = repo_root / "docs" / "fleet" / "fleet_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    registry_data = {"last_sync": now.isoformat(), "total_nodes": len(nodes), "nodes": nodes}

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)
    logger.info(f"Updated JSON registry at {registry_path}")

    # 2. Generate Markdown Report
    report_path = repo_root / "docs" / "fleet" / "reporting.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🛰️ Fleet Status Report\n\n")
        f.write(f"**Last Updated:** `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`\n\n")

        f.write("## 📊 Summary\n")
        online_count = sum(1 for n in nodes if n["status"] == "online")
        f.write(f"- **Total Nodes:** {len(nodes)}\n")
        f.write(f"- **Online:** {online_count}\n")
        f.write(f"- **Offline:** {len(nodes) - online_count}\n\n")

        f.write("## 🛡️ Node Details\n\n")
        f.write("| Node ID | Status | Last Heartbeat | IP Address | Drift Score |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")

        for node in nodes:
            last_seen = datetime.fromtimestamp(node["last_heartbeat"], tz=UTC)
            rel_time = f"{int((now - last_seen).total_seconds() / 60)}m ago"
            status_emoji = "🟢" if node["status"] == "online" else "🔴" if node["status"] == "offline" else "🟡"

            f.write(
                f"| `{node['node_id']}` | {status_emoji} {node['status']} | {rel_time} | `{node['ip_address']}` | `{node['drift_score']:.2f}` |\n"
            )

        f.write("\n\n---\n*Generated automatically by Projects AG Fleet Hub*")

    logger.info(f"Updated Markdown report at {report_path}")

    # 3. Git Push
    try:
        # Check if there are changes
        subprocess.run(["git", "add", "docs/fleet/"], cwd=str(repo_root), check=True)

        # Check if there's anything to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_root), capture_output=True, text=True)
        if status.stdout.strip():
            logger.info("Changes detected, committing and pushing...")
            subprocess.run(
                ["git", "commit", "-m", f"fleet: hourly sync {now.strftime('%Y-%m-%d %H:%M')}"],
                cwd=str(repo_root),
                check=True,
            )
            subprocess.run(["git", "push"], cwd=str(repo_root), check=True)
            logger.info("Successfully pushed fleet updates to remote")
        else:
            logger.info("No changes in fleet registry, skipping push")

    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_sync())
