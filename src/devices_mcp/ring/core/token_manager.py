"""
Token Manager for Ring MCP.

This module provides secure token storage and refresh functionality for Ring API tokens.
It handles encryption, decryption, and automatic token refresh.
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages secure storage and refresh of Ring API tokens."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
        encryption_key: bytes | None = None,
        salt: bytes | None = None,
    ):
        """Initialize the TokenManager.

        Args:
            storage_path: Path to store the encrypted tokens
            encryption_key: Optional encryption key (if None, will be derived from environment)
            salt: Optional salt for key derivation (if None, will be generated)
        """
        # Set up storage path
        if storage_path is None:
            self.storage_path = Path.home() / ".ring-mcp" / "tokens.enc"
        else:
            self.storage_path = Path(storage_path)

        # Ensure the directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        self.fernet = self._init_encryption(encryption_key, salt)
        self._tokens: dict[str, dict[str, Any]] = {}
        self._refresh_lock = asyncio.Lock()

    def _init_encryption(self, encryption_key: bytes | None = None, salt: bytes | None = None) -> Fernet:
        """Initialize the encryption system.

        Args:
            encryption_key: Optional encryption key
            salt: Optional salt for key derivation

        Returns:
            Configured Fernet instance for encryption/decryption
        """
        # Get or generate encryption key
        if encryption_key is None:
            # Try to get from environment
            env_key = os.getenv("RING_MCP_ENCRYPTION_KEY")
            if env_key:
                encryption_key = env_key.encode()
            else:
                # Generate a key and store it in the key file
                key_file = self.storage_path.parent / ".encryption_key"
                if key_file.exists():
                    with open(key_file, "rb") as f:
                        encryption_key = f.read()
                else:
                    encryption_key = Fernet.generate_key()
                    with open(key_file, "wb") as f:
                        f.write(encryption_key)
                    # Set restrictive permissions
                    key_file.chmod(0o600)

        # Generate salt for key derivation
        if salt is None:
            # Try to get from environment
            env_salt = os.getenv("RING_MCP_ENCRYPTION_SALT")
            if env_salt:
                salt = base64.urlsafe_b64decode(env_salt)
            else:
                # Generate a salt and store it in the salt file
                salt_file = self.storage_path.parent / ".encryption_salt"
                if salt_file.exists():
                    with open(salt_file, "rb") as f:
                        salt = f.read()
                else:
                    salt = os.urandom(16)
                    with open(salt_file, "wb") as f:
                        f.write(salt)
                    # Set restrictive permissions
                    salt_file.chmod(0o600)

        # Derive the key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_key))

        return Fernet(key)

    async def load_tokens(self) -> bool:
        """Load tokens from the encrypted storage.

        Returns:
            bool: True if tokens were loaded successfully, False otherwise
        """
        if not self.storage_path.exists():
            logger.info("No token storage found, starting with empty token store")
            self._tokens = {}
            return True

        try:
            async with aiofiles.open(self.storage_path, "rb") as f:
                encrypted_data = await f.read()

            if not encrypted_data:
                logger.warning("Token storage is empty")
                self._tokens = {}
                return True

            # Decrypt the data
            try:
                decrypted_data = self.fernet.decrypt(encrypted_data)
                self._tokens = json.loads(decrypted_data.decode())
                logger.info("Successfully loaded tokens from storage")
                return True
            except (InvalidToken, json.JSONDecodeError) as e:
                logger.exception("Failed to decrypt or parse token storage: %s", str(e))
                # Create a backup of the corrupted file
                backup_path = f"{self.storage_path}.corrupted.{int(datetime.now().timestamp())}"
                async with aiofiles.open(backup_path, "wb") as f:
                    await f.write(encrypted_data)
                logger.warning("Created backup of corrupted token file at %s", backup_path)
                self._tokens = {}
                return False

        except Exception as e:
            logger.exception("Error loading tokens: %s", str(e))
            self._tokens = {}
            return False

    async def save_tokens(self) -> bool:
        """Save tokens to the encrypted storage.

        Returns:
            bool: True if tokens were saved successfully, False otherwise
        """
        if not self._tokens:
            logger.debug("No tokens to save")
            return True

        try:
            # Create a temporary file first
            temp_path = f"{self.storage_path}.tmp"

            # Serialize and encrypt the tokens
            serialized = json.dumps(self._tokens).encode()
            encrypted_data = self.fernet.encrypt(serialized)

            # Write to temporary file
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(encrypted_data)

            # Atomically replace the old file
            if os.name == "nt":  # Windows
                # On Windows, we need to remove the destination file first
                if os.path.exists(self.storage_path):
                    os.replace(temp_path, self.storage_path)
                else:
                    os.rename(temp_path, self.storage_path)
            else:
                # On Unix-like systems, os.replace is atomic
                os.replace(temp_path, self.storage_path)

            # Set restrictive permissions
            self.storage_path.chmod(0o600)

            logger.debug("Successfully saved tokens to storage")
            return True

        except Exception as e:
            logger.exception("Error saving tokens: %s", str(e))
            # Clean up the temporary file if it exists
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
            return False

    async def get_token(self, username: str) -> dict[str, Any] | None:
        """Get a token for the specified username.

        Args:
            username: The username to get the token for

        Returns:
            The token dictionary if found, None otherwise
        """
        token_data = self._tokens.get(username)
        if not token_data:
            return None

        # Check if the token is expired or about to expire
        expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))
        refresh_token = token_data.get("refresh_token")

        # If the token is expired or will expire in the next 5 minutes, try to refresh it
        if expires_at < (datetime.utcnow() + timedelta(minutes=5)) and refresh_token:
            async with self._refresh_lock:
                # Check again in case another coroutine refreshed it
                token_data = self._tokens.get(username, {})
                expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))

                if expires_at < (datetime.utcnow() + timedelta(minutes=5)):
                    logger.info("Token for %s is expired or about to expire, refreshing...", username)
                    try:
                        # Import here to avoid circular imports
                        from .ring_client_modern import RingClient

                        # Create a temporary client to refresh the token
                        client = RingClient(token=token_data["access_token"])
                        await client.connect()

                        # Get the new token from the client
                        if client.token and client.token != token_data["access_token"]:
                            # Update the token data
                            token_data["access_token"] = client.token
                            token_data["expires_at"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()

                            # Save the updated tokens
                            self._tokens[username] = token_data
                            await self.save_tokens()

                            logger.info("Successfully refreshed token for %s", username)
                    except Exception as e:
                        logger.exception("Failed to refresh token for %s: %s", username, str(e))
                        # If refresh fails, we'll return None to force re-authentication
                        return None

        return token_data

    async def save_token(
        self,
        username: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int = 3600,
    ) -> bool:
        """Save a token for the specified username.

        Args:
            username: The username to save the token for
            access_token: The access token
            refresh_token: Optional refresh token
            expires_in: Time until token expiration in seconds (default: 1 hour)

        Returns:
            bool: True if the token was saved successfully, False otherwise
        """
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

        self._tokens[username] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "username": username,
            "created_at": datetime.utcnow().isoformat(),
        }

        return await self.save_tokens()

    async def delete_token(self, username: str) -> bool:
        """Delete a token for the specified username.

        Args:
            username: The username to delete the token for

        Returns:
            bool: True if the token was deleted successfully, False otherwise
        """
        if username in self._tokens:
            del self._tokens[username]
            return await self.save_tokens()
        return True

    async def get_all_tokens(self) -> dict[str, dict[str, Any]]:
        """Get all stored tokens.

        Returns:
            Dictionary mapping usernames to their token data
        """
        return self._tokens.copy()

    async def clear_tokens(self) -> bool:
        """Clear all stored tokens.

        Returns:
            bool: True if the tokens were cleared successfully, False otherwise
        """
        self._tokens = {}
        return await self.save_tokens()
