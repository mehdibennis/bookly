import types
from typing import cast

import pytest
from fastapi import HTTPException

from app.api.v1.routes import admin_users
from app.core.config import settings
from app.core.keycloak_admin import KeycloakAdmin, KeycloakAdminError
from app.core.keycloak_auth import KeycloakUser
from app.schemas.user_admin_schema import (
    UserAdminCreate,
    UserAdminUpdate,
    UserPasswordUpdate,
)
from tests.helpers import DummyUser


class DummyKC:
    def __init__(self, admin_access_token: str | None = None):
        self.admin_access_token = admin_access_token


@pytest.fixture(autouse=True)
def reset_overrides(monkeypatch):
    # Ensure we don't leak KEYCLOAK_CLIENT_SECRET changes between tests
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "", raising=False)
    yield


def test_get_admin_client_uses_service_account_when_secret(monkeypatch):
    # Arrange: SA secret configured
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "secret")
    # Patch KeycloakAdmin constructor used inside module
    constructed = {}

    def ctor(admin_access_token=None):
        constructed["token"] = admin_access_token
        return DummyKC(admin_access_token)

    monkeypatch.setattr(admin_users, "KeycloakAdmin", ctor)
    user = cast(
        KeycloakUser,
        DummyUser(raw_token="user-token", roles={("realm-management", "manage-users")}),
    )

    # Act
    kc = admin_users.get_admin_client(user)

    # Assert
    assert isinstance(kc, DummyKC)
    assert constructed["token"] is None  # SA path should not forward user token


def test_get_admin_client_uses_user_token_when_has_realm_mgmt(monkeypatch):
    # Arrange: no SA secret, user has realm-management role and a raw token
    constructed = {}

    def ctor(admin_access_token=None):
        constructed["token"] = admin_access_token
        return DummyKC(admin_access_token)

    monkeypatch.setattr(admin_users, "KeycloakAdmin", ctor)
    user = cast(
        KeycloakUser,
        DummyUser(raw_token="user-token", roles={("realm-management", "view-users")}),
    )

    # Act
    kc = admin_users.get_admin_client(user)

    # Assert
    assert isinstance(kc, DummyKC)
    assert constructed["token"] == "user-token"


def test_get_admin_client_fallback_without_roles(monkeypatch):
    # Arrange: no SA secret, user lacks roles
    constructed = {}

    def ctor(admin_access_token=None):
        # Simulate building a default client (no token)
        constructed.setdefault("calls", 0)
        constructed["calls"] += 1
        constructed["token"] = admin_access_token
        return DummyKC(admin_access_token)

    monkeypatch.setattr(admin_users, "KeycloakAdmin", ctor)
    user = cast(KeycloakUser, DummyUser(raw_token=None, roles=set()))

    # Act
    kc = admin_users.get_admin_client(user)

    # Assert
    assert isinstance(kc, DummyKC)
    assert constructed["token"] is None
    assert constructed["calls"] == 1


def test_require_realm_mgmt_bypasses_when_sa_secret(monkeypatch):
    # Arrange: SA secret configured and a dummy user without the role method
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "secret")
    dummy = cast(KeycloakUser, types.SimpleNamespace(username="x"))

    # Act
    out = admin_users.require_realm_mgmt(dummy)

    # Assert
    assert out is dummy


def test_require_realm_mgmt_passes_with_roles(monkeypatch):
    # Arrange: no SA secret, but user has a realm-management role
    user = cast(KeycloakUser, DummyUser(roles={("realm-management", "manage-users")}))

    # Act / Assert
    assert admin_users.require_realm_mgmt(user) is user


def test_require_realm_mgmt_forbidden_without_roles(monkeypatch):
    # Arrange: no SA secret, user lacks roles
    user = cast(KeycloakUser, DummyUser(roles=set()))

    # Act / Assert
    with pytest.raises(HTTPException) as ei:
        admin_users.require_realm_mgmt(user)
    assert ei.value.status_code == 403


def test_require_realm_mgmt_handles_users_without_method(monkeypatch):
    # Arrange: no SA secret, user object without has_client_role method
    dummy = object()

    # Act / Assert
    with pytest.raises(HTTPException) as ei:
        admin_users.require_realm_mgmt(dummy)  # type: ignore[arg-type]
    assert ei.value.status_code == 403


# --- Route function exception branches -----------------------------------------------------------


class KcErroring:
    async def create_user(self, **kwargs):
        raise KeycloakAdminError("boom")

    async def update_user(self, *args, **kwargs):
        raise KeycloakAdminError("boom")

    async def set_user_password(self, *args, **kwargs):
        raise KeycloakAdminError("boom")

    async def delete_user(self, *args, **kwargs):
        raise KeycloakAdminError("boom")

    async def get_user_by_id(self, *args, **kwargs):
        raise KeycloakAdminError("boom")


@pytest.mark.asyncio
async def test_create_user_raises_502_on_client_error():
    payload = UserAdminCreate(
        username="u",
        email="u@example.com",
        firstName="U",
        lastName="Ser",
        enabled=True,
        password="x",
    )
    with pytest.raises(HTTPException) as ei:
        await admin_users.create_user(payload, None, cast(KeycloakAdmin, KcErroring()))
    assert ei.value.status_code == 502


@pytest.mark.asyncio
async def test_update_user_raises_502_on_client_error():
    payload = UserAdminUpdate(
        email=None, firstName=None, lastName=None, enabled=None, attributes=None
    )
    with pytest.raises(HTTPException) as ei:
        await admin_users.update_user(
            "id", payload, None, cast(KeycloakAdmin, KcErroring())
        )
    assert ei.value.status_code == 502


@pytest.mark.asyncio
async def test_set_password_raises_502_on_client_error():
    payload = UserPasswordUpdate(password="p", temporary=False)
    with pytest.raises(HTTPException) as ei:
        await admin_users.set_password(
            "id", payload, None, cast(KeycloakAdmin, KcErroring())
        )
    assert ei.value.status_code == 502


@pytest.mark.asyncio
async def test_delete_user_raises_502_on_client_error():
    with pytest.raises(HTTPException) as ei:
        await admin_users.delete_user("id", None, cast(KeycloakAdmin, KcErroring()))
    assert ei.value.status_code == 502


class KcGetUserNone:
    async def get_user_by_id(self, user_id: str):
        return None


@pytest.mark.asyncio
async def test_get_user_returns_404_when_missing():
    with pytest.raises(HTTPException) as ei:
        await admin_users.get_user("id", None, cast(KeycloakAdmin, KcGetUserNone()))
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_raises_502_on_client_error():
    with pytest.raises(HTTPException) as ei:
        await admin_users.get_user("id", None, cast(KeycloakAdmin, KcErroring()))
    assert ei.value.status_code == 502
