from __future__ import annotations

from typing import Iterable


class DummyUser:
    """Reusable dummy user for tests.

    Supports both shapes used across tests:
    - raw_token and has_client_role(client, role) used by admin keycloak tests
    - username/email/roles/is_admin used by request fixtures
    """

    def __init__(
        self,
        raw_token: str | None = None,
        roles: Iterable[tuple[str, str]] | None = None,
        username: str = "dummy",
        email: str = "test@example.com",
        is_admin: bool = False,
    ) -> None:
        self.raw_token = raw_token
        self.username = username
        self.email = email
        self.is_admin = is_admin
        # support both list-style 'roles' and a has_client_role method
        self._roles: set[tuple[str, str]] = set(roles or [])
        # keep a list-like attribute for tests that inspect .roles
        self.roles = [r for r in self._roles]

    def has_client_role(self, client: str, role: str) -> bool:
        return (client, role) in self._roles
