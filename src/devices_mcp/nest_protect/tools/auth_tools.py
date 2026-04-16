"""Authentication tools for Nest Protect MCP."""

import webbrowser
from typing import Any
from urllib.parse import urlencode

from pydantic import BaseModel, Field


class OAuthFlowParams(BaseModel):
    """Parameters for OAuth flow initiation."""

    redirect_uri: str = Field("http://localhost:8000/auth/callback", description="Redirect URI for auth code")
    state: str | None = Field(None, description="CSRF protection state")
    open_browser: bool = Field(True, description="Open auth URL in browser")


class OAuthCallbackParams(BaseModel):
    """Parameters for OAuth callback handling."""

    code: str = Field(..., description="Auth code from OAuth callback")
    state: str = Field(..., description="State param from OAuth")
    expected_state: str | None = Field(None, description="Expected CSRF state")
    redirect_uri: str = Field(
        "http://localhost:8000/auth/callback",
        description="Redirect URI used in auth request",
    )


class RefreshTokenParams(BaseModel):
    """Parameters for token refresh."""

    force: bool = Field(False, description="Force refresh even if token not expired")


async def initiate_oauth_flow(
    redirect_uri: str = "http://localhost:8000/auth/callback",
    state: str | None = None,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Initiate OAuth 2.0 flow for Nest API."""
    from ..state_manager import get_app_state

    if not state:
        import secrets

        state = secrets.token_urlsafe(16)

    app_state = get_app_state()
    app_state.oauth_state = state

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": app_state.config.client_id,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/sdm.service",
        "redirect_uri": redirect_uri,
        "state": state,
    }

    url = f"{auth_url}?{urlencode(params)}"

    if open_browser:
        webbrowser.open(url)

    return {
        "status": "success",
        "message": "OAuth flow initiated",
        "auth_url": url,
        "state": state,
    }


async def handle_oauth_callback(
    code: str,
    state: str,
    expected_state: str | None = None,
    redirect_uri: str = "http://localhost:8000/auth/callback",
) -> dict[str, Any]:
    """Handle OAuth 2.0 callback from Nest API."""
    import aiohttp

    from ..state_manager import get_app_state

    if expected_state and state != expected_state:
        return {
            "status": "error",
            "message": "Invalid state parameter",
            "error": "state_mismatch",
        }

    try:
        app_state = get_app_state()
        token_url = "https://www.googleapis.com/oauth2/v4/token"
        data = {
            "client_id": app_state.config.client_id,
            "client_secret": app_state.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                token_data = await response.json()

                if response.status != 200:
                    return {
                        "status": "error",
                        "message": "Failed to exchange authorization code",
                        "error": token_data.get("error"),
                        "error_description": token_data.get("error_description"),
                    }

                app_state.access_token = token_data["access_token"]
                app_state.refresh_token = token_data.get("refresh_token")
                app_state.token_expires_in = token_data.get("expires_in")

                return {
                    "status": "success",
                    "message": "Successfully authenticated with Nest API",
                    "access_token": "****" + (app_state.access_token[-4:] if app_state.access_token else ""),
                    "token_type": token_data.get("token_type"),
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope"),
                    "refresh_token": "****" if "refresh_token" in token_data else None,
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to complete OAuth flow: {e!s}",
            "error": "oauth_error",
        }


async def refresh_access_token(force: bool = False) -> dict[str, Any]:
    """Refresh OAuth 2.0 access token using refresh token."""
    import aiohttp

    from ..state_manager import get_app_state

    app_state = get_app_state()

    if not app_state.refresh_token:
        return {
            "status": "error",
            "message": "No refresh token available",
            "error": "no_refresh_token",
        }

    if not force and not getattr(app_state, "token_expires_in", 0) < 300:  # 5 minutes
        return {"status": "success", "message": "Token not expired, refresh not needed"}

    try:
        token_url = "https://www.googleapis.com/oauth2/v4/token"
        data = {
            "client_id": app_state.config.client_id,
            "client_secret": app_state.config.client_secret,
            "refresh_token": app_state.refresh_token,
            "grant_type": "refresh_token",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                token_data = await response.json()

                if response.status != 200:
                    return {
                        "status": "error",
                        "message": "Failed to refresh access token",
                        "error": token_data.get("error"),
                        "error_description": token_data.get("error_description"),
                    }

                app_state.access_token = token_data["access_token"]
                app_state.token_expires_in = token_data.get("expires_in")

                return {
                    "status": "success",
                    "message": "Access token refreshed",
                    "access_token": "****" + (app_state.access_token[-4:] if app_state.access_token else ""),
                    "token_type": token_data.get("token_type"),
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope"),
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to refresh access token: {e!s}",
            "error": "refresh_failed",
        }
