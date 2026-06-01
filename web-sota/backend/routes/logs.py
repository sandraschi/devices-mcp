import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_log_line(line: str) -> dict[str, str] | None:
    """Parse one line: standard 'ts - logger - LEVEL - message', or JSON, or raw."""
    line = line.strip()
    if not line:
        return None

    if line.startswith("{"):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and "message" in obj:
            return {
                "timestamp": str(obj.get("timestamp", "")),
                "level": str(obj.get("level", "INFO")).upper(),
                "logger": str(obj.get("logger", obj.get("name", ""))),
                "message": str(obj.get("message", "")),
            }

    parts = line.split(" - ", 3)
    if len(parts) >= 4:
        ts, logger_name, l_level, message = parts[0], parts[1], parts[2], parts[3]
        return {
            "timestamp": ts.strip(),
            "level": l_level.strip().upper(),
            "logger": logger_name.strip(),
            "message": message,
        }

    # Traceback continuation, print(), or non-standard lines
    return {
        "timestamp": "",
        "level": "INFO",
        "logger": "—",
        "message": line,
    }


_LEVEL_IN_LINE = re.compile(r" - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - ", re.I)


def _effective_level(entry: dict[str, str]) -> str:
    lv = (entry.get("level") or "INFO").upper()
    if lv != "INFO" or not entry.get("message"):
        return lv
    msg = entry["message"]
    m = _LEVEL_IN_LINE.search(msg)
    if m:
        return m.group(1).upper()
    return "INFO"


@router.get("/api/logs")
async def get_logs(
    level: str | None = Query(None, description="Filter by log level"),
    lines: int = Query(100, ge=1, le=1000, description="Log lines to retrieve"),
    search: str | None = Query(None, description="Search term (message / full line)"),
):
    """Tail the configured application log file (same file as devices_mcp file logging)."""
    try:
        from devices_mcp.config import get_config
        from devices_mcp.config.log_paths import touch_log_file

        config = get_config()
        log_file = touch_log_file(config=config)
        log_path_str = str(log_file)

        if not log_file.exists():
            return {
                "logs": [],
                "total": 0,
                "message": "Log file not found",
                "log_path": log_path_str,
                "path_exists": False,
                "hint": "Open Settings → Logging to change the path. Default: %USERPROFILE%\\.local\\share\\devices-mcp\\devices-mcp.log",
            }

        log_entries: list[dict[str, str]] = []
        with open(log_file, encoding="utf-8", errors="replace") as f:
            file_lines = f.readlines()
            recent_lines = file_lines[-lines:] if len(file_lines) > lines else file_lines

            for raw in recent_lines:
                entry = _parse_log_line(raw)
                if entry is None:
                    continue
                eff = _effective_level(entry)
                entry["level"] = eff
                if level and eff != level.upper():
                    continue
                hay = f"{entry.get('message', '')} {entry.get('logger', '')} {entry.get('timestamp', '')}"
                if search and search.lower() not in hay.lower():
                    continue
                log_entries.append(entry)

        log_entries.reverse()
        return {
            "logs": log_entries,
            "total": len(log_entries),
            "log_path": log_path_str,
            "path_exists": True,
        }
    except Exception as e:
        logger.exception("Error fetching logs")
        return {"logs": [], "total": 0, "error": str(e), "path_exists": False}


@router.post("/api/logs/analyze")
async def analyze_logs(
    logs: list[dict],
    enable_clustering: bool = False,
    enable_anomaly_detection: bool = False,
    enable_ai_synopsis: bool = False,
):
    """Analyze logs with clustering, anomaly detection, and AI synopsis."""
    try:
        result: dict[str, Any] = {
            "clustered": logs,
            "anomalies": [],
            "synopsis": None,
        }

        # Clustering: Group similar log messages
        if enable_clustering:
            clusters: dict[str, list] = {}
            for log_entry in logs:
                message = log_entry.get("message", "")
                # Create a normalized key (remove timestamps, IDs, etc.)
                normalized = message.lower()
                # Remove common variable parts
                normalized = re.sub(r"\d+", "N", normalized)
                normalized = re.sub(
                    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
                    "UUID",
                    normalized,
                )
                normalized = re.sub(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", "IP", normalized)

                if normalized not in clusters:
                    clusters[normalized] = []
                clusters[normalized].append(log_entry)

            # Convert clusters to grouped format
            clustered_logs: list[Any] = []
            for _cluster_key, cluster_entries in clusters.items():
                if len(cluster_entries) > 1:
                    clustered_logs.append(
                        {
                            "type": "cluster",
                            "count": len(cluster_entries),
                            "pattern": cluster_entries[0].get("message", ""),
                            "entries": cluster_entries,
                        }
                    )
                else:
                    clustered_logs.extend(cluster_entries)

            result["clustered"] = clustered_logs

        # Anomaly detection: Find unusual patterns
        if enable_anomaly_detection:
            anomalies: list[dict[str, Any]] = []

            # Count log levels
            level_counts: dict[str, int] = {}
            for log_entry in logs:
                lev = log_entry.get("level", "INFO")
                level_counts[lev] = level_counts.get(lev, 0) + 1

            # Detect high error rate
            total_logs = len(logs)
            if total_logs > 0:
                error_rate = level_counts.get("ERROR", 0) / total_logs
                if error_rate > 0.1:  # More than 10% errors
                    anomalies.append(
                        {
                            "type": "high_error_rate",
                            "severity": "high",
                            "message": f"High error rate detected: {error_rate * 100:.1f}% of logs are errors",
                            "count": level_counts.get("ERROR", 0),
                        }
                    )

                # Detect sudden spike in warnings
                if level_counts.get("WARNING", 0) > total_logs * 0.2:
                    anomalies.append(
                        {
                            "type": "warning_spike",
                            "severity": "medium",
                            "message": f"Warning spike detected: {level_counts.get('WARNING', 0)} warnings in recent logs",
                            "count": level_counts.get("WARNING", 0),
                        }
                    )

            # Detect repeated errors (same message multiple times)
            error_messages: dict[str, int] = {}
            for log_entry in logs:
                if log_entry.get("level") == "ERROR":
                    msg = log_entry.get("message", "")
                    error_messages[msg] = error_messages.get(msg, 0) + 1

            for msg, count in error_messages.items():
                if count >= 5:  # Same error 5+ times
                    anomalies.append(
                        {
                            "type": "repeated_error",
                            "severity": "high",
                            "message": f"Repeated error detected: '{msg[:50]}...' ({count} occurrences)",
                            "count": count,
                            "pattern": msg,
                        }
                    )

            result["anomalies"] = anomalies

        # AI Synopsis: Generate summary using LLM
        if enable_ai_synopsis:
            try:
                from devices_mcp.llm.manager import get_llm_manager

                # Prepare log summary for LLM
                log_summary = f"Recent log entries ({len(logs)} total):\n\n"
                for log_entry in logs[:50]:  # Limit to first 50 for context
                    log_summary += f"[{log_entry.get('level', 'INFO')}] {log_entry.get('message', '')}\n"

                prompt = f"""Analyze these application logs and provide a brief synopsis (2-3 sentences):

{log_summary}

Focus on:
- Key issues or errors
- System health status
- Notable patterns or trends

Provide a concise summary:"""

                manager = get_llm_manager()
                messages = [{"role": "user", "content": prompt}]

                try:
                    synopsis = await manager.chat(messages, stream=False)
                    if isinstance(synopsis, str):
                        result["synopsis"] = synopsis
                    elif isinstance(synopsis, dict) and "content" in synopsis:
                        result["synopsis"] = synopsis["content"]
                    else:
                        result["synopsis"] = "AI synopsis unavailable - LLM provider not configured"
                except Exception as e:
                    logger.warning(f"AI synopsis generation failed: {e}")
                    result["synopsis"] = f"AI synopsis unavailable: {e!s}"
            except ImportError:
                result["synopsis"] = "AI synopsis unavailable - LLM module not available"
            except Exception as e:
                logger.exception("Error generating AI synopsis")
                result["synopsis"] = f"AI synopsis error: {e!s}"

        return result
    except Exception as e:
        logger.exception("Error analyzing logs")
        return {
            "clustered": logs,
            "anomalies": [],
            "synopsis": None,
            "error": str(e),
        }


@router.get("/api/logs/stats")
async def get_log_stats():
    """Log file size and rotated siblings (same basename prefix)."""
    try:
        from devices_mcp.config import get_config
        from devices_mcp.config.log_paths import touch_log_file

        config = get_config()
        log_file = touch_log_file(config=config)
        log_path_str = str(log_file)

        stats: dict[str, Any] = {
            "enabled": True,
            "log_path": log_path_str,
            "path_exists": log_file.exists(),
            "total_files": 0,
            "total_size_mb": 0.0,
        }

        if log_file.exists():
            parent = log_file.parent
            base = log_file.name
            related = sorted(parent.glob(base + "*"))
            total_bytes = sum(p.stat().st_size for p in related if p.is_file())
            stats["total_files"] = len(related)
            stats["total_size_mb"] = total_bytes / (1024 * 1024)
        return stats
    except Exception as e:
        return {"enabled": False, "error": str(e), "path_exists": False}
