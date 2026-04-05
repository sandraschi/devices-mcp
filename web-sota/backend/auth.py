"""Authentication module for Devices MCP dashboard."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Session storage (in-memory for simplicity, persists across requests)
_sessions: dict[str, dict] = {}

# Config path
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config.yaml"


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash password with salt using SHA-256.

    Returns (hashed_password, salt).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against hash."""
    new_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(new_hash, hashed)


def get_auth_config() -> dict:
    """Get auth configuration from config.yaml."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config.get("auth", {})
    except Exception as e:
        logger.warning(f"Failed to load auth config: {e}")
        return {}


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    auth_config = get_auth_config()
    return auth_config.get("enabled", False)


def get_users() -> dict[str, dict]:
    """Get configured users."""
    auth_config = get_auth_config()
    return auth_config.get("users", {})


def validate_credentials(username: str, password: str) -> bool:
    """Validate username and password."""
    users = get_users()

    if username not in users:
        return False

    user = users[username]
    stored_hash = user.get("password_hash", "")
    salt = user.get("salt", "")

    # If no hash exists, check plain password (for initial setup)
    if not stored_hash and user.get("password"):
        return password == user.get("password")

    return verify_password(password, stored_hash, salt)


def create_session(username: str) -> str:
    """Create a new session for user."""
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {
        "username": username,
        "created": datetime.now(),
        "expires": datetime.now() + timedelta(hours=24),
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Get session by ID."""
    if not session_id:
        return None

    session = _sessions.get(session_id)
    if not session:
        return None

    # Check expiration
    if datetime.now() > session["expires"]:
        del _sessions[session_id]
        return None

    return session


def delete_session(session_id: str) -> None:
    """Delete a session."""
    _sessions.pop(session_id, None)


def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session cookie."""
    session_id = request.cookies.get("session_id")
    session = get_session(session_id)
    return session["username"] if session else None


async def require_auth(request: Request) -> str:
    """Dependency that requires authentication."""
    if not is_auth_enabled():
        return "admin"  # Auth disabled, allow all

    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# Public paths that don't require auth
PUBLIC_PATHS = {
    "/login",
    "/api/auth/login",
    "/api/auth/logout",
    "/static",
    "/favicon.ico",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check authentication on protected routes."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth check if disabled
        if not is_auth_enabled():
            return await call_next(request)

        path = request.url.path

        # Allow public paths
        for public_path in PUBLIC_PATHS:
            if path.startswith(public_path):
                return await call_next(request)

        # Check session
        user = get_current_user(request)

        if not user:
            # Redirect to login for HTML pages
            if request.headers.get("accept", "").startswith("text/html"):
                return RedirectResponse(url="/login", status_code=302)
            # Return 401 for API calls
            return HTTPException(status_code=401, detail="Not authenticated")

        return await call_next(request)


def setup_default_user() -> None:
    """Set up default admin user if none exists."""
    auth_config = get_auth_config()

    if auth_config.get("enabled") and not auth_config.get("users"):
        logger.info("Auth enabled but no users configured. Creating default admin user.")

        # Generate default password
        default_password = secrets.token_urlsafe(12)
        hashed, salt = hash_password(default_password)

        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            if "auth" not in config:
                config["auth"] = {}

            config["auth"]["users"] = {
                "admin": {
                    "password_hash": hashed,
                    "salt": salt,
                    "role": "admin",
                }
            }

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            logger.warning(f"Created default admin user. Password: {default_password}")
            logger.warning("Please change this password immediately!")
            print(f"\n{'=' * 60}")
            print("DEFAULT ADMIN CREDENTIALS")
            print("Username: admin")
            print(f"Password: {default_password}")
            print(f"{'=' * 60}\n")

        except Exception as e:
            logger.exception(f"Failed to create default user: {e}")
