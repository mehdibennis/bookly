from unittest.mock import patch

import pytest

from app.core.exceptions import UnauthorizedException
from app.core.keycloak_auth import KeycloakAuth, KeycloakUser, get_current_user


@pytest.fixture
def keycloak_auth_instance(monkeypatch):
    class FakeKeycloakOpenID:
        def public_key(self):
            return "fake_key_content"

        def userinfo(self, token):
            return {"email": "user@example.com", "sub": "user123"}

    kc = KeycloakAuth()
    monkeypatch.setattr(kc, "keycloak_openid", FakeKeycloakOpenID())
    return kc


@pytest.mark.asyncio
async def test_verify_token_success(keycloak_auth_instance):
    fake_token_payload = {
        "preferred_username": "alice",
        "realm_access": {"roles": ["user"]},
        "email": "alice@example.com",
        "exp": 9999999999,
    }
    with patch("app.core.keycloak_auth.jwt.decode", return_value=fake_token_payload):
        result = await keycloak_auth_instance.verify_token("valid_token")
        assert result["preferred_username"] == "alice"


@pytest.mark.asyncio
async def test_verify_token_expired_raises_unauthorized(keycloak_auth_instance):
    from jose.exceptions import ExpiredSignatureError

    with patch("app.core.keycloak_auth.jwt.decode", side_effect=ExpiredSignatureError("Expired")):
        with pytest.raises(UnauthorizedException, match="expiré"):
            await keycloak_auth_instance.verify_token("expired_token")


@pytest.mark.asyncio
async def test_verify_token_invalid_raises_unauthorized(keycloak_auth_instance):
    from jose.exceptions import JWTError

    with patch("app.core.keycloak_auth.jwt.decode", side_effect=JWTError("Invalid")):
        with pytest.raises(UnauthorizedException, match="invalide"):
            await keycloak_auth_instance.verify_token("bad_token")


@pytest.mark.asyncio
async def test_get_user_info_returns_dict(keycloak_auth_instance):
    info = await keycloak_auth_instance.get_user_info("some_token")
    assert "email" in info
    assert info["sub"] == "user123"


def test_keycloak_user_extracts_username_and_roles():
    token_info = {
        "preferred_username": "bob",
        "realm_access": {"roles": ["admin", "user"]},
        "email": "bob@test.com",
    }
    user = KeycloakUser(token_info)
    assert user.username == "bob"
    assert user.email == "bob@test.com"
    assert user.roles == ["admin", "user"]


def test_keycloak_user_is_admin():
    token_info = {"preferred_username": "admin_user", "realm_access": {"roles": ["admin"]}}
    user = KeycloakUser(token_info)
    assert user.is_admin is True


def test_keycloak_user_not_admin():
    token_info = {"preferred_username": "normal_user", "realm_access": {"roles": ["user"]}}
    user = KeycloakUser(token_info)
    assert user.is_admin is False


def test_keycloak_user_has_role():
    token_info = {"preferred_username": "u", "realm_access": {"roles": ["developer", "tester"]}}
    user = KeycloakUser(token_info)
    assert user.has_role("developer") is True
    assert user.has_role("admin") is False


def test_keycloak_user_client_roles():
    token_info = {
        "preferred_username": "u",
        "resource_access": {
            "realm-management": {"roles": ["view-users", "manage-users"]},
        },
    }
    user = KeycloakUser(token_info)
    rm_roles = user.client_roles("realm-management")
    assert "view-users" in rm_roles
    assert "manage-users" in rm_roles


def test_keycloak_user_has_client_role():
    token_info = {
        "preferred_username": "u",
        "resource_access": {"realm-management": {"roles": ["view-users"]}},
    }
    user = KeycloakUser(token_info)
    assert user.has_client_role("realm-management", "view-users") is True
    assert user.has_client_role("realm-management", "manage-users") is False


def test_keycloak_user_realm_management_roles():
    token_info = {
        "preferred_username": "u",
        "resource_access": {"realm-management": {"roles": ["view-users"]}},
    }
    user = KeycloakUser(token_info)
    assert user.realm_management_roles == ["view-users"]


def test_keycloak_user_raw_token():
    token_info = {"preferred_username": "u", "realm_access": {"roles": []}}
    user = KeycloakUser(token_info, raw_token="raw_access_token")
    assert user.raw_token == "raw_access_token"


@pytest.mark.asyncio
async def test_get_current_user_dependency(monkeypatch):
    from fastapi.security import HTTPAuthorizationCredentials

    from app.core import keycloak_auth as ka_module

    fake_token_payload = {
        "preferred_username": "dep_user",
        "realm_access": {"roles": ["user"]},
        "email": "dep@example.com",
        "exp": 9999999999,
    }

    class FakeKeycloakAuth:
        async def verify_token(self, token):
            return fake_token_payload

        async def get_user_info(self, token):
            return {"email": "dep@example.com"}

    monkeypatch.setattr(ka_module, "keycloak_auth", FakeKeycloakAuth())
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    user = await get_current_user(creds)
    assert user.username == "dep_user"
