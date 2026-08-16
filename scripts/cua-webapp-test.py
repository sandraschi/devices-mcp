#!/usr/bin/env python3
"""CUA webapp test — pre-Tauri / no-Tauri webapp smoke test.

Same idea as cua-smoke.py but WITHOUT the NSIS install/uninstall phases:
spins up backend + frontend (via the repo's start.ps1), waits for the
"Connected" badge (webapps show "Connecting..." for a few seconds while the
backend comes up), then walks the sidebar with title-matching UIA clicks.

CUA_WEBAPP_TEST_VERSION = 1

Phases:
    1. Kill stale processes (backend/frontend ports)
    2. Start stack (start.ps1 -Headless if supported, else direct spawn)
    3. Wait for backend health (config backend_port / health_path)
    4. Wait for frontend (config frontend_port) HTTP 200
    5. Open browser to frontend URL
    6. Wait for "Connected" badge (OCR, retry w/ timeout — the wrinkle)
    7. Nav walk: title-matching sidebar clicks, per-page screenshots
    8. Diagnostics check (if backend exposes /api/v1/diagnostics)
    9. Cleanup: kill spawned processes
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CUA_WEBAPP_TEST_VERSION = 1
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cua-nsis-config.json")
_CONFIG = {}

CONNECTED_KEYWORDS = ["connected", "system online", "online", "ready"]
CONNECTING_KEYWORDS = ["connecting", "waiting for backend", "connecting..."]
FAIL_KEYWORDS = [
    "404",
    "not found",
    "error",
    "timeout",
    "internal server error",
    "failed to fetch",
    "cannot connect",
    "connection refused",
]


def load_config(path=None):
    p = path or DEFAULT_CONFIG
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cfg(key, default=""):
    return _CONFIG.get(key, default)


_CONFIG = load_config()

BACKEND_PORT = int(cfg("backend_port", 10700))
FRONTEND_PORT = int(cfg("frontend_port", 0))
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
HEALTH_PATH = cfg("health_path") or cfg("backend_health_path", "/api/v1/health")
PRODUCT_NAME = cfg("product_name", "App")
WINDOW_TITLE_RE = cfg("window_title_re") or cfg("window_title", PRODUCT_NAME)
CONNECTED_TEXT = cfg("connected_badge_text", "connected")
CONNECTED_TIMEOUT = int(cfg("connected_timeout", 60))
PROCESS_NAMES = cfg("backend_process_names", [])
SERVICE_NAME = cfg("service_name", "")
_SERVICE_WAS_RUNNING = False


def log(msg):
    print(f"  [cua-webapp] {msg}", flush=True)


def fatal(msg):
    print(f"  [cua-webapp] FATAL: {msg}", flush=True)
    sys.exit(1)


def _service_state(name):
    """Query service state via sc.exe (never kill NSSM children directly)."""
    try:
        out = subprocess.run(["sc.exe", "query", name], capture_output=True, text=True, timeout=10).stdout
        if "RUNNING" in out:
            return "running"
        if "STOPPED" in out:
            return "stopped"
        if "STOP_PENDING" in out or "START_PENDING" in out:
            return "pending"
        return "unknown"
    except Exception:
        return "unknown"


def _service_wait(name, target, timeout=60):
    """Wait until the service reaches target state (running|stopped)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _service_state(name) == target:
            return True
        time.sleep(2)
    return False


def _service_stop(name):
    """Stop an NSSM service via the service manager (never taskkill)."""
    if _service_state(name) != "running":
        return True
    log(f"Stopping service '{name}' (sc.exe stop — never kill the child)")
    subprocess.run(["sc.exe", "stop", name], capture_output=True, timeout=30)
    if not _service_wait(name, "stopped"):
        log(f"WARNING: service '{name}' did not reach STOPPED in time")
        return False
    return True


def _service_start(name):
    """Restore an NSSM service via the service manager."""
    if _service_state(name) == "running":
        return True
    log(f"Restoring service '{name}' (sc.exe start)")
    subprocess.run(["sc.exe", "start", name], capture_output=True, timeout=30)
    if not _service_wait(name, "running"):
        log(f"WARNING: service '{name}' did not reach RUNNING in time")
        return False
    return True


def kill_stale():
    """Kill processes holding backend/frontend ports (via temp PS script).

    NSSM rule: if the port is owned by an NSSM-managed service, stop the
    service via sc.exe instead — killing the child makes NSSM respawn it
    instantly and re-bind the port, racing the test stack.

    Uses netstat -ano instead of Get-NetTCPConnection: the NetTCPIP module
    takes ~30s to load on some Windows hosts (Windows PowerShell 5.1),
    which blew the 15s timeout in CI and on this machine.
    """
    if SERVICE_NAME:
        _service_stop(SERVICE_NAME)
    ports = [str(p) for p in (BACKEND_PORT, FRONTEND_PORT) if p]
    if not ports:
        return
    if os.environ.get("DEVICES_MCP_SKIP_PSKILL") == "1":
        log("PS kill skipped (DEVICES_MCP_SKIP_PSKILL=1)")
        time.sleep(2)
        return True
    port_re = "|".join(":" + p + r"\s.*LISTENING" for p in ports)
    ps = (
        "$pids = netstat -ano | Select-String -Pattern '"
        + port_re
        + "' | ForEach-Object { $f = ($_ -split '\\s+'); $f[$f.Count - 1] } | Sort-Object -Unique\n"
        "foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }\n"
        "exit 0\n"
    )
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".ps1")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ps)
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path],
            capture_output=True,
            timeout=15,
        )
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    log(f"Cleared ports {', '.join(ports)}")
    time.sleep(2)
    return True


def _shell_host():
    """Prefer pwsh 7: powershell.exe 5.1 + Start-Job in a no-console
    (CREATE_NO_WINDOW) context crashes the host and takes the parent
    process down (observed on this machine: test python killed with
    exit -1 right after Popen)."""
    for cand in (r"C:\Program Files\PowerShell\7\pwsh.exe", "pwsh.exe", "powershell.exe"):
        try:
            subprocess.run([cand, "-NoProfile", "-Command", "exit 0"], capture_output=True, timeout=10)
            return cand
        except Exception:
            continue
    return "powershell.exe"


def start_stack():
    """Start backend + frontend via start.ps1 (prefer -Headless), else direct spawn."""
    repo_root = Path(__file__).resolve().parent.parent
    start_ps1 = repo_root / "start.ps1"
    shell = _shell_host()

    # Try start.ps1 -Headless first (fleet standard has this switch)
    if start_ps1.exists():
        try:
            log("Starting stack via start.ps1 -Headless...")
            # Pre-set the headless guard: the test already runs detached
            # (CREATE_NO_WINDOW), so start.ps1 must NOT re-spawn itself into a
            # hidden window - Start-Process -WindowStyle Hidden from a
            # console-less host crashes the console group (observed: this
            # python killed with exit -1 right after Popen).
            env = dict(os.environ)
            env["DEVICES_MCP_HEADLESS_REENTERED"] = "1"
            subprocess.Popen(
                [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(start_ps1), "-Headless"],
                cwd=str(repo_root),
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=env,
            )
            return True
        except Exception as e:
            log(f"start.ps1 -Headless failed ({e}), falling back to direct spawn")

    # Fallback: direct spawn of backend via uv + python module (config: backend_module)
    module = cfg("backend_module", "")
    if not module:
        log("No backend_module in config — cannot direct-spawn backend")
        return False
    log(f"Direct spawn fallback: python -m {module}")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"Set-Location '{repo_root}'; $env:BACKEND_PORT='{BACKEND_PORT}'; uv run python -m {module}",
        ],
        cwd=str(repo_root),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return True


def wait_backend():
    """Poll backend health endpoint until 200 or timeout."""
    url = f"{BACKEND_URL}{HEALTH_PATH}"
    deadline = time.time() + int(cfg("backend_timeout", 30))
    while time.time() < deadline:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            if r.status == 200:
                log(f"Backend ready ({url})")
                return True
        except Exception:
            pass
        time.sleep(2)
    log(f"Backend not reachable at {url}")
    return False


def wait_frontend():
    """Poll frontend port until HTTP 200 or timeout."""
    if not FRONTEND_PORT:
        log("No frontend_port in config — skipping frontend wait")
        return True
    url = f"http://127.0.0.1:{FRONTEND_PORT}"
    deadline = time.time() + int(cfg("frontend_timeout", 30))
    while time.time() < deadline:
        try:
            r = urllib.request.urlopen(url, timeout=3)
            if r.status == 200:
                log(f"Frontend ready ({url})")
                return True
        except Exception:
            pass
        time.sleep(2)
    log(f"Frontend not reachable at {url}")
    return False


def open_browser():
    """Open the webapp in the default browser."""
    if not FRONTEND_PORT:
        return True
    url = f"http://127.0.0.1:{FRONTEND_PORT}"
    try:
        subprocess.Popen(["cmd", "/c", "start", "", url])
        log(f"Opened browser: {url}")
        return True
    except Exception as e:
        log(f"Browser open failed: {e}")
        return False


def find_webapp_window():
    """Find the browser window showing the webapp (by title regex).

    NOTE: no descendants() preference scan - Chrome exposes huge UIA trees
    and descendants(control_type=...) can take minutes per window, blowing
    the connected-badge deadline (observed on this machine). The title
    match is sufficient: the tab title contains the app name.
    """
    try:
        from pywinauto import Desktop

        desktop = Desktop(backend="uia")
        candidates = []
        for w in desktop.windows():
            title = (w.window_text() or "").lower()
            if re.search(WINDOW_TITLE_RE.lower(), title):
                candidates.append(w)
        if not candidates:
            return None
        return candidates[0]
    except Exception:
        return None


def wait_connected_badge(timeout=None):
    """Wait for the Connected badge via OCR. The wrinkle: webapps show
    'Connecting...' for a few seconds while the backend comes up."""
    timeout = timeout or CONNECTED_TIMEOUT
    deadline = time.time() + timeout
    win = None
    text = ""
    connected_kw = CONNECTED_TEXT.lower()
    while time.time() < deadline:
        if win is None:
            win = find_webapp_window()
        if win:
            try:
                win.set_focus()
                time.sleep(0.5)
                img = win.capture_as_image()
                # OCR via tesseract
                try:
                    import pytesseract

                    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    text = (pytesseract.image_to_string(img) or "").lower()
                except Exception:
                    text = ""
                if connected_kw in text or any(k in text for k in CONNECTED_KEYWORDS):
                    log(f"Connected badge found after {int(time.time() - (deadline - timeout))}s")
                    return win, text
                # If we see connecting text, keep waiting (not an error)
                if any(k in text for k in CONNECTING_KEYWORDS):
                    log("  Still connecting...")
            except Exception:
                pass
        time.sleep(2)
    if win is None:
        log(f"No window matching '{WINDOW_TITLE_RE}' found in {timeout}s")
    else:
        log(f"Connected badge not found in {timeout}s (last OCR: '{text[:80]}')")
    return win, text


def nav_click_through(output_dir, win):
    """Title-matching sidebar walk (same strategy as cua-smoke template v3)."""
    nav_routes = cfg("nav_routes", [])
    if not isinstance(nav_routes, list) or not nav_routes:
        log("No nav_routes in config — nav walk skipped")
        return True
    os.makedirs(output_dir, exist_ok=True)
    try:
        win.maximize()
        time.sleep(1)
    except Exception:
        pass

    nav_failures = []
    for label, _expected in nav_routes:
        try:
            link = win.descendants(title=label)
            if link:
                link[0].click_input()
            else:
                elements = win.descendants(control_type="Hyperlink")
                el = [e for e in elements if label.lower() in (e.window_text() or "").lower()]
                if el:
                    el[0].click_input()
                else:
                    nav_failures.append((label, "no link found"))
                    log(f"Nav '{label}': no link found — skipped")
                    continue
            time.sleep(2)
            path = os.path.join(output_dir, f"webapp-{label.lower().replace(' ', '-')}.png")
            win.capture_as_image().save(path)
            log(f"Nav '{label}': clicked + screenshot ({os.path.getsize(path)} bytes)")
        except Exception as e:
            nav_failures.append((label, str(e)))
            log(f"Nav '{label}' failed (non-fatal): {e}")
    if nav_failures:
        log(f"Nav failures: {nav_failures}")
        return False
    log(f"All {len(nav_routes)} pages navigated")
    return True


def check_diagnostics():
    try:
        r = urllib.request.urlopen(f"{BACKEND_URL}/api/v1/diagnostics", timeout=5)
        data = json.loads(r.read())
        log(f"Diagnostics: HTTP {r.status}, tools={len(data.get('tools', [])) if isinstance(data, dict) else '?'}")
        return True
    except Exception as e:
        log(f"Diagnostics check skipped: {e}")
        return False


def cleanup():
    kill_stale()
    if SERVICE_NAME:
        _service_start(SERVICE_NAME)
    log("Cleanup done")
    return True


_webapp_window = None  # module-level cache for the found window


def phase_nav_walk(output_dir=None):
    """Reuse the connected window from phase 6 if still alive, else re-find."""
    win, _ = wait_connected_badge(timeout=10)
    if not win:
        log("No webapp window for nav walk")
        return False
    return nav_click_through(output_dir or "cua-reports", win)


def main():
    parser = argparse.ArgumentParser(description="CUA webapp test (pre-Tauri)")
    parser.add_argument("--config")
    parser.add_argument("--output-dir", default="cua-reports")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--timeout", type=int, default=0)
    args = parser.parse_args()
    if args.config:
        _CONFIG.update(load_config(args.config))
    if args.timeout:
        global CONNECTED_TIMEOUT
        CONNECTED_TIMEOUT = args.timeout

    global BACKEND_PORT, FRONTEND_PORT, BACKEND_URL
    BACKEND_PORT = int(cfg("backend_port", 10700))
    FRONTEND_PORT = int(cfg("frontend_port", 0))
    BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

    print(f"=== CUA Webapp Test v{CUA_WEBAPP_TEST_VERSION} ===")
    print(f"Product: {PRODUCT_NAME}  Backend: {BACKEND_PORT}  Frontend: {FRONTEND_PORT or 'n/a'}")

    phases = [
        ("1-kill-stale", kill_stale, True),
        ("2-start-stack", start_stack, True),
        ("3-backend-health", wait_backend, True),
        ("4-frontend-ready", wait_frontend, False),
        ("5-browser", lambda: None if args.no_browser else open_browser(), False),
        ("6-connected-badge", lambda: bool(wait_connected_badge()[0]), False),
        ("7-nav-walk", phase_nav_walk, False),
        ("8-diagnostics", check_diagnostics, False),
        ("9-cleanup", cleanup, False),
    ]

    passed = failed = 0
    for name, fn, critical in phases:
        try:
            ok = fn()
            if ok:
                passed += 1
                log(f"V {name}")
            else:
                failed += 1
                log(f"X {name}")
                if critical:
                    log(f"CRITICAL — aborting ({name})")
                    break
        except Exception as e:
            failed += 1
            log(f"X {name}: {e}")
            if critical:
                log(f"CRITICAL — aborting ({name})")
                break

    log(f"Result: {passed}/{passed + failed}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
