from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.core.config import settings


class KeycloakAdminError(Exception):
    """Error raised when a Keycloak Admin operation fails."""


class KeycloakAdmin:
    """
    Minimal asynchronous Keycloak Admin client for user management.

    - Uses the client_credentials flow to call the Admin API
      (requires a confidential client with service account + realm-management roles).
    - Never uses the admin token for /userinfo (requires a user access token).
    """

    def __init__(self, *, timeout: float = 10.0, admin_access_token: str | None = None):
        self.server_url = settings.KEYCLOAK_SERVER_URL.rstrip("/")
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
        self.timeout = timeout
        # Use empty string for 'no token' to satisfy static typing; runtime checks
        # treat falsy string as missing token.
        self._token: str = ""
        self._token_expires_at: float = 0.0

        # Optional: allow injection of an access token (e.g., an admin user's token)
        # Useful for tests when client_credentials cannot be used
        if admin_access_token:
            self._token = admin_access_token
            # set a reasonable expiration (1h) to avoid immediate refresh
            self._token_expires_at = time.time() + 3600

    # URLs
    @property
    def base_admin(self) -> str:
        return f"{self.server_url}/admin/realms/{self.realm}"

    @property
    def token_url(self) -> str:
        return settings.KEYCLOAK_TOKEN_URL

    @property
    def userinfo_url(self) -> str:
        return settings.KEYCLOAK_USERINFO_URL

    @property
    def introspect_url(self) -> str:
        return settings.KEYCLOAK_INTROSPECT_URL

    # Auth admin (client_credentials)
    async def _ensure_token(self) -> str:
        """Return a valid admin token (with cache and expiration margin)."""
        now = time.time()
        if self._token and now < (self._token_expires_at - 10):
            return self._token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            resp = await client.post(self.token_url, data=data)
            if resp.status_code != 200:
                raise KeycloakAdminError(
                    f"Failed to fetch admin token: {resp.status_code} {resp.text}"
                )
            body = resp.json()
            access_token = body.get("access_token")
            expires_in = int(body.get("expires_in", 0))
            if not access_token:
                raise KeycloakAdminError("Invalid token response: missing access_token")
            self._token = access_token
            self._token_expires_at = now + max(expires_in, 60)
            return access_token

    async def _headers(self) -> dict[str, str]:
        token = await self._ensure_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Helpers
    @staticmethod
    def _extract_id_from_location(location: str) -> str | None:
        m = re.search(r"/users/([^/]+)$", location)
        return m.group(1) if m else None

    # User operations (Admin API)
    async def create_user(
        self,
        *,
        username: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        enabled: bool = True,
        password: str | None = None,
        temporary_password: bool = False,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {"username": username, "enabled": enabled}
        if email is not None:
            payload["email"] = email
        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if attributes:
            payload["attributes"] = attributes

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_admin}/users", headers=await self._headers(), json=payload
            )
            if resp.status_code not in (201, 409):
                raise KeycloakAdminError(
                    f"Failed to create user: {resp.status_code} {resp.text}"
                )
            if resp.status_code == 409:
                user = await self.get_user_by_username(username)
                if not user:
                    raise KeycloakAdminError(
                        "Conflict: user exists but not found by username"
                    )
                user_id = user["id"]
            else:
                location = resp.headers.get("Location", "")
                user_id = self._extract_id_from_location(location)
                if not user_id:
                    user = await self.get_user_by_username(username)
                    if not user:
                        raise KeycloakAdminError(
                            "User created but ID could not be determined"
                        )
                    user_id = user["id"]

            if password:
                await self.set_user_password(
                    user_id, password, temporary=temporary_password
                )

            return user_id

    async def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_admin}/users",
                headers=await self._headers(),
                params={"username": username, "exact": "true"},
            )
            if resp.status_code != 200:
                raise KeycloakAdminError(
                    f"Failed to search user: {resp.status_code} {resp.text}"
                )
            items = resp.json()
            if not items:
                return None
            return items[0]

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_admin}/users/{user_id}", headers=await self._headers()
            )
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise KeycloakAdminError(
                    f"Failed to get user by id: {resp.status_code} {resp.text}"
                )
            return resp.json()

    async def list_users(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_admin}/users", headers=await self._headers()
            )
            if resp.status_code != 200:
                raise KeycloakAdminError(
                    f"Failed to list users: {resp.status_code} {resp.text}"
                )
            return resp.json()

    async def update_user(
        self,
        user_id: str,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        enabled: bool | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {}
        if email is not None:
            payload["email"] = email
        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if enabled is not None:
            payload["enabled"] = enabled
        if attributes is not None:
            payload["attributes"] = attributes

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.put(
                f"{self.base_admin}/users/{user_id}",
                headers=await self._headers(),
                json=payload,
            )
            if resp.status_code not in (204, 200):
                raise KeycloakAdminError(
                    f"Failed to update user: {resp.status_code} {resp.text}"
                )

    async def delete_user(self, user_id: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(
                f"{self.base_admin}/users/{user_id}", headers=await self._headers()
            )
            if resp.status_code not in (204, 200):
                raise KeycloakAdminError(
                    f"Failed to delete user: {resp.status_code} {resp.text}"
                )

    async def set_user_password(
        self, user_id: str, password: str, *, temporary: bool = False
    ) -> None:
        payload = {"type": "password", "value": password, "temporary": temporary}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.put(
                f"{self.base_admin}/users/{user_id}/reset-password",
                headers=await self._headers(),
                json=payload,
            )
            if resp.status_code not in (204, 200):
                raise KeycloakAdminError(
                    f"Failed to reset password: {resp.status_code} {resp.text}"
                )

    # Introspection Token (with admin credentials)
    async def introspect_token(self, token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            data = {
                "token": token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            resp = await client.post(self.introspect_url, data=data)
            if resp.status_code != 200:
                raise KeycloakAdminError(
                    f"Failed to introspect token: {resp.status_code} {resp.text}"
                )
            return resp.json()

    # /userinfo (with access token of a user)
    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self.userinfo_url, headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code == 401:
                raise KeycloakAdminError("User access token invalid or expired")
            if resp.status_code != 200:
                raise KeycloakAdminError(
                    f"Failed to call userinfo: {resp.status_code} {resp.text}"
                )
            return resp.json()
