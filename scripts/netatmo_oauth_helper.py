import logging
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logger = logging.getLogger(__name__)


def build_authorize_url(client_id: str, redirect_uri: str, scope: str = "read_station", state: str = "xyz") -> str:
    base = "https://api.netatmo.com/oauth2/authorize"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": "code",
        "state": state,
    }
    return f"{base}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    url = "https://api.netatmo.com/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    resp = requests.post(url, data=data, timeout=20)
    if resp.status_code != 200:
        error_text = resp.text
        try:
            error_json = resp.json()
            error_msg = error_json.get("error", "Unknown error")
            error_desc = error_json.get("error_description", error_text)
            logger.info(f"ERROR: Error {resp.status_code}: {error_msg}")
            logger.info(f"   Description: {error_desc}")
        except:
            logger.info(f"ERROR: Error {resp.status_code}: {error_text}")
        resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    url = "https://api.netatmo.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    resp = requests.post(url, data=data, timeout=20)
    resp.raise_for_status()
    return resp.json()


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to catch OAuth callback."""

    code = None
    error = None

    def do_GET(self):
        """Handle GET request from OAuth redirect."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            CallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">Authorization Successful!</h1>
                <p>You can close this window.</p>
                <p>The authorization code has been captured.</p>
            </body>
            </html>
            """)
        elif "error" in params:
            CallbackHandler.error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"""
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authorization Failed</h1>
                <p>Error: {CallbackHandler.error}</p>
            </body>
            </html>
            """.encode()
            )
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Not found")

    def log_message(self, format, *args):
        """Suppress default logging."""


def wait_for_callback(port: int = 8080, timeout: int = 300) -> str:
    """Start a local HTTP server to catch OAuth callback."""
    server = HTTPServer(("localhost", port), CallbackHandler)
    server.timeout = timeout

    logger.info(f"🌐 Starting callback server on http://localhost:{port}/callback")
    logger.info(f"⏳ Waiting for authorization (timeout: {timeout}s)...")
    logger.info("   (After you authorize, the code will be captured automatically)\n")

    start_time = time.time()
    while CallbackHandler.code is None and CallbackHandler.error is None:
        server.handle_request()
        if time.time() - start_time > timeout:
            logger.info("❌ Timeout waiting for callback")
            return None

    server.server_close()

    if CallbackHandler.error:
        logger.info(f"❌ Authorization error: {CallbackHandler.error}")
        return None

    if CallbackHandler.code:
        logger.info(f"✅ Authorization code captured: {CallbackHandler.code[:20]}...")
        return CallbackHandler.code

    return None


def main():
    if len(sys.argv) < 2:
        logger.info(
            "Usage:\n"
            "  python scripts/netatmo_oauth_helper.py auth-url <CLIENT_ID> <REDIRECT_URI>\n"
            "  python scripts/netatmo_oauth_helper.py auth-flow <CLIENT_ID> <CLIENT_SECRET> [REDIRECT_URI] [PORT]\n"
            "  python scripts/netatmo_oauth_helper.py exchange <CLIENT_ID> <CLIENT_SECRET> <CODE> <REDIRECT_URI>\n"
            "  python scripts/netatmo_oauth_helper.py refresh <CLIENT_ID> <CLIENT_SECRET> <REFRESH_TOKEN>"
        )
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "auth-url":
        client_id, redirect_uri = sys.argv[2], sys.argv[3]
        url = build_authorize_url(client_id, redirect_uri)
        logger.info(url)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    elif cmd == "auth-flow":
        # Complete OAuth flow with automatic callback capture
        client_id = sys.argv[2]
        client_secret = sys.argv[3]
        redirect_uri = sys.argv[4] if len(sys.argv) > 4 else "http://localhost:8080/callback"
        port = int(sys.argv[5]) if len(sys.argv) > 5 else 8080

        # Extract port from redirect_uri if specified
        if redirect_uri.startswith("http://localhost:"):
            try:
                port = int(redirect_uri.split(":")[2].split("/")[0])
            except:
                pass

        # Update redirect_uri to use the port we'll listen on
        if "localhost" in redirect_uri:
            redirect_uri = f"http://localhost:{port}/callback"

        logger.info("\nSTARTING OAuth Flow")
        logger.info(f"   Client ID: {client_id}")
        logger.info(f"   Redirect URI: {redirect_uri}\n")

        # Start callback server in background
        code = None

        def run_server():
            nonlocal code
            code = wait_for_callback(port=port)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # Give server time to start

        # Build and open auth URL
        url = build_authorize_url(client_id, redirect_uri)
        logger.info("🔗 Opening authorization URL...\n")
        logger.info(f"   {url}\n")
        try:
            webbrowser.open(url)
        except Exception:
            logger.info("WARNING: Could not open browser automatically. Copy the URL above and open it manually.\n")

        # Wait for callback
        server_thread.join(timeout=300)

        if code:
            logger.info("\n🔄 Exchanging code for tokens...\n")
            try:
                tokens = exchange_code_for_tokens(client_id, client_secret, code, redirect_uri)
                logger.info("\n✅ Success! Tokens received:\n")
                logger.info(f"Refresh Token: {tokens.get('refresh_token', 'NOT PROVIDED')}\n")
                logger.info("Full response:")
                import json

                logger.info(json.dumps(tokens, indent=2))
                logger.info("\n📝 Copy the 'refresh_token' value above and update config.yaml")
            except Exception as e:
                logger.info(f"\n❌ Failed to exchange code: {e}")
        else:
            logger.info("\n❌ No authorization code received")
    elif cmd == "exchange":
        client_id, client_secret, code, redirect_uri = (
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5],
        )
        tokens = exchange_code_for_tokens(client_id, client_secret, code, redirect_uri)
        logger.info(tokens)
    elif cmd == "refresh":
        client_id, client_secret, refresh_token = sys.argv[2], sys.argv[3], sys.argv[4]
        tokens = refresh_access_token(client_id, client_secret, refresh_token)
        logger.info(tokens)
    else:
        logger.info("Unknown command")
        sys.exit(1)


if __name__ == "__main__":
    main()
