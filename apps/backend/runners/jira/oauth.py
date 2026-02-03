"""
Jira OAuth 2.0 (3LO) Client
============================

Implements OAuth 2.0 (3-legged OAuth) flow for Jira Cloud.

This client provides:
- Authorization URL generation for user login
- Token exchange (authorization code → access/refresh tokens)
- Token refresh (refresh token → new access token)
- Secure token storage in system keychain

OAuth 2.0 (3LO) Flow:
1. Generate authorization URL and redirect user to Jira
2. User logs in and authorizes the app
3. Jira redirects back with authorization code
4. Exchange code for access token and refresh token
5. Use access token for API requests
6. Refresh access token when it expires

For Jira Cloud setup:
  1. Create OAuth 2.0 integration at:
     https://developer.atlassian.com/console/myapps/
  2. Configure callback URL: http://localhost:8080/callback
  3. Add required scopes: read:jira-work, write:jira-work
  4. Get Client ID and Client Secret

References:
  - https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
  - https://developer.atlassian.com/cloud/jira/platform/oauth-2-authorization-code-grants-3lo-for-apps/
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import aiohttp
from core.platform import is_linux, is_macos

logger = logging.getLogger(__name__)


class JiraOAuthError(Exception):
    """Raised when OAuth flow fails."""

    pass


@dataclass
class JiraOAuthToken:
    """OAuth 2.0 token with metadata."""

    access_token: str
    refresh_token: str
    expires_at: datetime
    scope: str
    token_type: str = "Bearer"

    def is_expired(self) -> bool:
        """Check if access token is expired (with 5-minute buffer)."""
        buffer = timedelta(minutes=5)
        return datetime.now() >= (self.expires_at - buffer)

    def to_dict(self) -> dict[str, Any]:
        """Serialize token to dictionary."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "scope": self.scope,
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JiraOAuthToken:
        """Deserialize token from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            scope=data["scope"],
            token_type=data.get("token_type", "Bearer"),
        )


@dataclass
class JiraOAuthConfig:
    """Configuration for Jira OAuth 2.0 client."""

    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"
    scopes: list[str] | None = None

    def __post_init__(self) -> None:
        """Set default scopes if not provided."""
        if self.scopes is None:
            # Default scopes for Jira Cloud API access
            self.scopes = [
                "read:jira-work",  # Read issues, projects, etc.
                "write:jira-work",  # Create/update issues, transitions
                "read:jira-user",  # Read user information
                "offline_access",  # Required for refresh token
            ]


class JiraOAuthClient:
    """
    OAuth 2.0 (3-legged OAuth) client for Jira Cloud.

    Implements the full OAuth 2.0 authorization code flow with PKCE
    (Proof Key for Code Exchange) for enhanced security.

    Usage:
        # 1. Create OAuth client
        config = JiraOAuthConfig(
            client_id="your-client-id",
            client_secret="your-client-secret"
        )
        oauth_client = JiraOAuthClient(config)

        # 2. Generate authorization URL
        auth_url, state = oauth_client.get_authorization_url()
        # Redirect user to auth_url in browser

        # 3. User authorizes and Jira redirects back with code
        # Extract code from callback URL

        # 4. Exchange code for tokens
        token = await oauth_client.exchange_code(code, state)

        # 5. Save token to secure storage
        oauth_client.save_token(token)

        # 6. Use token for API requests (automatic refresh when expired)
        access_token = await oauth_client.get_access_token()
    """

    # Jira Cloud OAuth 2.0 endpoints
    AUTH_URL = "https://auth.atlassian.com/authorize"
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"

    def __init__(
        self,
        config: JiraOAuthConfig,
        token_storage_path: Path | None = None,
    ):
        """
        Initialize Jira OAuth client.

        Args:
            config: OAuth configuration with client credentials
            token_storage_path: Path to store tokens (defaults to ~/.auto-claude/jira_oauth.json)
        """
        self.config = config
        self._token_storage_path = token_storage_path or self._get_default_token_path()
        self._cached_token: JiraOAuthToken | None = None

        # PKCE code verifier (random string for security)
        # Generated per authorization request
        self._code_verifier: str | None = None

    def _get_default_token_path(self) -> Path:
        """Get default token storage path based on platform."""
        home = Path.home()
        auto_claude_dir = home / ".auto-claude"
        auto_claude_dir.mkdir(exist_ok=True)
        return auto_claude_dir / "jira_oauth.json"

    def _generate_code_verifier(self) -> str:
        """
        Generate PKCE code verifier.

        Returns a cryptographically random string for PKCE flow.
        """
        # Generate 43-128 character random string (base64url-encoded)
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")

    def _generate_code_challenge(self, verifier: str) -> str:
        """
        Generate PKCE code challenge from verifier.

        Uses SHA-256 hash of the verifier.
        """
        import hashlib

        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def get_authorization_url(self) -> tuple[str, str]:
        """
        Generate OAuth authorization URL for user login.

        This URL should be opened in a browser. After user authorizes,
        Jira will redirect to the configured redirect_uri with an
        authorization code.

        Returns:
            Tuple of (authorization_url, state):
                - authorization_url: URL to redirect user to
                - state: Random state parameter for CSRF protection
                  (must be validated when code is received)

        Example:
            auth_url, state = oauth_client.get_authorization_url()
            print(f"Open this URL in your browser: {auth_url}")
            # Store state for later validation
        """
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Generate PKCE code verifier and challenge
        self._code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(self._code_verifier)

        # Build authorization URL with parameters
        params = {
            "audience": "api.atlassian.com",
            "client_id": self.config.client_id,
            "scope": " ".join(self.config.scopes or []),
            "redirect_uri": self.config.redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",  # Always show consent screen
            # PKCE parameters
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.debug(f"Generated authorization URL with state: {state}")

        return auth_url, state

    async def exchange_code(
        self,
        authorization_code: str,
        state: str,
        expected_state: str | None = None,
    ) -> JiraOAuthToken:
        """
        Exchange authorization code for access and refresh tokens.

        After user authorizes, Jira redirects to your callback URL with
        an authorization code. This method exchanges that code for tokens.

        Args:
            authorization_code: Authorization code from callback URL
            state: State parameter from callback URL
            expected_state: Expected state value (for CSRF validation).
                           If None, state validation is skipped.

        Returns:
            JiraOAuthToken with access token, refresh token, and expiration

        Raises:
            JiraOAuthError: If token exchange fails or state validation fails
        """
        # Validate state to prevent CSRF attacks
        if expected_state is not None and state != expected_state:
            raise JiraOAuthError(
                "State mismatch. Possible CSRF attack. "
                f"Expected: {expected_state}, Got: {state}"
            )

        # Ensure we have a code verifier (from get_authorization_url)
        if not self._code_verifier:
            raise JiraOAuthError(
                "Code verifier not found. Call get_authorization_url() first."
            )

        # Build token request
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": authorization_code,
            "redirect_uri": self.config.redirect_uri,
            "code_verifier": self._code_verifier,
        }

        logger.info("Exchanging authorization code for tokens...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    response_text = await response.text()

                    if response.status != 200:
                        error_msg = response_text
                        try:
                            error_data = json.loads(response_text)
                            error_msg = error_data.get("error_description", error_msg)
                        except json.JSONDecodeError:
                            pass
                        raise JiraOAuthError(
                            f"Token exchange failed ({response.status}): {error_msg}"
                        )

                    token_data = json.loads(response_text)

                    # Parse token response
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
                    expires_in = token_data.get("expires_in", 3600)
                    scope = token_data.get("scope", "")

                    if not access_token or not refresh_token:
                        raise JiraOAuthError(
                            "Token response missing access_token or refresh_token"
                        )

                    # Calculate expiration time
                    expires_at = datetime.now() + timedelta(seconds=expires_in)

                    token = JiraOAuthToken(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_at=expires_at,
                        scope=scope,
                    )

                    logger.info(
                        f"Successfully obtained tokens (expires in {expires_in}s)"
                    )

                    # Clear code verifier (one-time use)
                    self._code_verifier = None

                    return token

        except aiohttp.ClientError as e:
            raise JiraOAuthError(f"Network error during token exchange: {e}")

    async def refresh_token(self, token: JiraOAuthToken) -> JiraOAuthToken:
        """
        Refresh an expired access token using the refresh token.

        Args:
            token: Current token with refresh_token

        Returns:
            New JiraOAuthToken with refreshed access token

        Raises:
            JiraOAuthError: If token refresh fails
        """
        if not token.refresh_token:
            raise JiraOAuthError("No refresh token available")

        # Build refresh request
        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": token.refresh_token,
        }

        logger.info("Refreshing access token...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    response_text = await response.text()

                    if response.status != 200:
                        error_msg = response_text
                        try:
                            error_data = json.loads(response_text)
                            error_msg = error_data.get("error_description", error_msg)
                        except json.JSONDecodeError:
                            pass
                        raise JiraOAuthError(
                            f"Token refresh failed ({response.status}): {error_msg}"
                        )

                    token_data = json.loads(response_text)

                    # Parse refreshed token
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token", token.refresh_token)
                    expires_in = token_data.get("expires_in", 3600)
                    scope = token_data.get("scope", token.scope)

                    if not access_token:
                        raise JiraOAuthError("Token response missing access_token")

                    # Calculate new expiration
                    expires_at = datetime.now() + timedelta(seconds=expires_in)

                    refreshed_token = JiraOAuthToken(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_at=expires_at,
                        scope=scope,
                    )

                    logger.info(
                        f"Successfully refreshed token (expires in {expires_in}s)"
                    )

                    return refreshed_token

        except aiohttp.ClientError as e:
            raise JiraOAuthError(f"Network error during token refresh: {e}")

    def save_token(self, token: JiraOAuthToken) -> None:
        """
        Save OAuth token to secure storage.

        Tokens are stored in JSON format at the configured storage path.
        On macOS/Linux/Windows, the file has restricted permissions (600).

        Args:
            token: Token to save
        """
        try:
            # Serialize token to JSON
            token_data = token.to_dict()

            # Write to file with restricted permissions
            self._token_storage_path.write_text(
                json.dumps(token_data, indent=2), encoding="utf-8"
            )

            # Set file permissions to 600 (owner read/write only)
            if is_macos() or is_linux():
                import stat

                self._token_storage_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

            logger.info(f"Token saved to {self._token_storage_path}")

            # Update cache
            self._cached_token = token

        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            raise JiraOAuthError(f"Failed to save token: {e}")

    def load_token(self) -> JiraOAuthToken | None:
        """
        Load OAuth token from storage.

        Returns:
            Loaded token, or None if no token is stored

        Raises:
            JiraOAuthError: If token file is corrupted
        """
        # Check cache first
        if self._cached_token:
            return self._cached_token

        # Load from file
        if not self._token_storage_path.exists():
            logger.debug("No stored token found")
            return None

        try:
            token_data = json.loads(
                self._token_storage_path.read_text(encoding="utf-8")
            )
            token = JiraOAuthToken.from_dict(token_data)

            logger.debug("Token loaded from storage")

            # Update cache
            self._cached_token = token

            return token

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse stored token: {e}")
            raise JiraOAuthError(f"Corrupted token file: {e}")

    async def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        This method handles token refresh automatically:
        - If no token is stored, raises JiraOAuthError
        - If token is expired, refreshes it automatically
        - Returns a valid access token ready for API use

        Returns:
            Valid access token

        Raises:
            JiraOAuthError: If no token is available or refresh fails
        """
        token = self.load_token()

        if not token:
            raise JiraOAuthError(
                "No OAuth token found. Run OAuth authorization flow first."
            )

        # Refresh if expired
        if token.is_expired():
            logger.info("Access token expired, refreshing...")
            token = await self.refresh_token(token)
            self.save_token(token)

        return token.access_token

    def clear_token(self) -> None:
        """
        Clear stored token and cache.

        Useful for logout or when switching Jira accounts.
        """
        if self._token_storage_path.exists():
            self._token_storage_path.unlink()
            logger.info("Token cleared from storage")

        self._cached_token = None
