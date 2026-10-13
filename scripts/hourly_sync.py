#!/usr/bin/env python3
"""
Daily Fleet Synchronization Script.

Kept at the historic ``hourly_sync.py`` path so existing callers
(web-sota/backend/server.py, Task Scheduler jobs) keep working — but the
old every-5-minutes push behaviour is gone.

Policy (2026-10-08):
- At most ONE sync per 24 h (caller-side gate in server.py + file-side
  gate here on ``last_sync``).
- Push ONLY when fleet membership meaningfully changed: node added /
  removed, status (online/offline) flipped, IP or drift_score changed.
  Bare heartbeat timestamp ticks and wall-clock time passing NEVER
  trigger a commit — that was the source of the every-5-minutes churn
  (each run rewrote ``last_sync: now`` so git was always dirty).
- ``--force`` overrides both gates for manual runs.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Setup logging (logger name kept for continuity with historic log files)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hourly_sync")

# Add src to path
repo_root = Path(__file__).parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from devices_mcp.fleet.manager import FleetManager

SYNC_INTERVAL = timedelta(hours=24)


def _fingerprint(nodes: list[dict]) -> list[dict]:
    """Meaningful-change fingerprint: identity + status, not heartbeat ticks.

    ``last_heartbeat`` updates on every heartbeat by design, so it must be
    excluded — otherwise the fingerprint is always dirty and every run
    pushes (the original bug).
    """
    fp = []
    for n in nodes:
        try:
            drift = round(float(n.get("drift_score") or 0.0), 2)
        except (TypeError, ValueError):
            drift = 0.0
        fp.append(
            {
                "node_id": n.get("node_id"),
                "status": n.get("status"),
                "ip_address": n.get("ip_address"),
                "drift_score": drift,
            }
        )
    fp.sort(key=lambda e: str(e["node_id"]))
    return fp


def _load_previous(registry_path: Path) -> tuple[list[dict] | None, datetime | None]:
    """Return (previous nodes, previous last_sync) or (None, None)."""
    if not registry_path.is_file():
        return None, None
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read previous registry ({e}); treating as changed")
        return None, None
    nodes = data.get("nodes")
    last_sync = None
    raw = data.get("last_sync")
    if isinstance(raw, str):
        try:
            last_sync = datetime.fromisoformat(raw)
        except ValueError:
            last_sync = None
    return nodes, last_sync


async def run_sync(force: bool = False) -> None:
    logger.info("Starting daily fleet sync")

    manager = FleetManager()
    nodes = await manager.get_fleet_status()
    now = datetime.now(UTC)

    registry_path = repo_root / "docs" / "fleet" / "fleet_registry.json"
    prev_nodes, prev_sync = _load_previous(registry_path)

    fingerprint_changed = prev_nodes is None or _fingerprint(nodes) != _fingerprint(prev_nodes)
    interval_elapsed = prev_sync is None or (now - prev_sync) >= SYNC_INTERVAL

    if not force and not fingerprint_changed:
        logger.info("No meaningful fleet change (heartbeats only), skipping file rewrite and push")
        return
    if not force and not interval_elapsed and prev_nodes is not None:
        logger.info(f"Daily sync not due (last sync {prev_sync.isoformat()}), skipping push")
        return

    # 1. Generate JSON Registry (only reached when pushing)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_data = {"last_sync": now.isoformat(), "total_nodes": len(nodes), "nodes": nodes}
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f, indent=2)
    logger.info(f"Updated JSON registry at {registry_path}")

    # 2. Generate Markdown Report
    report_path = repo_root / "docs" / "fleet" / "reporting.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Fleet Status Report\n\n")
        f.write(f"**Last Updated:** `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`\n\n")

        f.write("## Summary\n")
        online_count = sum(1 for n in nodes if n["status"] == "online")
        f.write(f"- **Total Nodes:** {len(nodes)}\n")
        f.write(f"- **Online:** {online_count}\n")
        f.write(f"- **Offline:** {len(nodes) - online_count}\n\n")

        f.write("## Node Details\n\n")
        f.write("| Node ID | Status | Last Heartbeat | IP Address | Drift Score |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")

        for node in nodes:
            last_seen = datetime.fromtimestamp(node["last_heartbeat"], tz=UTC)
            rel_time = f"{int((now - last_seen).total_seconds() / 60)}m ago"
            status_emoji = (
                "ONLINE" if node["status"] == "online" else "OFFLINE" if node["status"] == "offline" else "UNKNOWN"
            )

            f.write(
                f"| `{node['node_id']}` | {status_emoji} {node['status']} | {rel_time} | `{node['ip_address']}` | `{node['drift_score']:.2f}` |\n"
            )

        f.write("\n\n---\n*Generated automatically by Projects AG Fleet Hub*")

    logger.info(f"Updated Markdown report at {report_path}")

    # 3. Git Push
    try:
        subprocess.run(["git", "add", "docs/fleet/"], cwd=str(repo_root), check=True)

        # Scope the dirt check to docs/fleet/: unrelated working-tree
        # changes must neither trigger nor break the fleet commit.
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "docs/fleet/"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if status.stdout.strip():
            logger.info("Meaningful fleet change, committing and pushing...")
            subprocess.run(
                ["git", "commit", "-m", f"fleet: daily sync {now.strftime('%Y-%m-%d')}"],
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

    parser = argparse.ArgumentParser(description="Daily fleet registry sync (pushes only on meaningful change)")
    parser.add_argument("--force", action="store_true", help="Ignore the 24h gate and change check")
    args = parser.parse_args()

    asyncio.run(run_sync(force=args.force))
