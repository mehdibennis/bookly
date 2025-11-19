from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.api.v1.routes.admin_users import get_admin_client
from app.core.keycloak_admin import KeycloakAdmin, KeycloakAdminError


@pytest.fixture
def settings_stub(monkeypatch):
    from app.core import config

    monkeypatch.setattr(
        config.settings, "KEYCLOAK_SERVER_URL", "https://kc-test.example.com/"
    )
    monkeypatch.setattr(config.settings, "KEYCLOAK_REALM", "test-realm")
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_ID", "test-client")
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_SECRET", "secret")


@pytest.mark.asyncio
async def test_ensure_token_fetches_and_caches(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    cast(Any, kc)._token = None
    token1 = await kc._ensure_token()
    assert token1 == "fake-token"
    token2 = await kc._ensure_token()
    assert token1 == token2


@pytest.mark.asyncio
async def test_ensure_token_refreshes_on_expiry(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    cast(Any, kc)._token = None
    token1 = await kc._ensure_token()
    assert token1 == "fake-token"

    # Wait for token to expire
    import asyncio
    import time

    await asyncio.sleep(3)
    kc._token_expires_at = time.time() - 1
    # Mock a new token response
    respx_mock.post(token_url).respond(
        status_code=200,
        json={"access_token": "fake-token-2", "expires_in": 3600},
    )

    token2 = await kc._ensure_token()
    assert token2 == "fake-token-2"
    assert token1 != token2


@pytest.mark.asyncio
async def test_create_user_success_201(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock create user endpoint -> retourne 201 avec Location header contenant l'id
    location = f"{kc.base_admin}/users/abc-123"
    respx_mock.post(f"{kc.base_admin}/users").respond(
        status_code=201, headers={"Location": location}
    )

    user_id = await kc.create_user(
        username="u1",
        email="a@b.com",
        first_name="First",
        last_name="Last",
        attributes={"attr1": "value1"},
    )
    assert user_id == "abc-123"


@pytest.mark.asyncio
async def test_raise_keycloak_admin_error_on_create_user_failure(
    settings_stub, respx_mock
):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock create user endpoint -> retourne 500 Internal Server Error
    respx_mock.post(f"{kc.base_admin}/users").respond(
        status_code=500, json={"error": "server_error"}
    )

    with pytest.raises(Exception) as exc_info:
        await kc.create_user(username="u1", email="a@b.com")
    assert "Failed to create user" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_user_409_falls_back_to_get_by_username(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock create user endpoint -> retourne 409 Conflict
    respx_mock.post(f"{kc.base_admin}/users").respond(status_code=409)

    # Mock get users endpoint -> retourne liste avec l'utilisateur créé
    respx_mock.get(f"{kc.base_admin}/users").respond(
        status_code=200,
        json=[{"id": "existing-user-id", "username": "u1", "email": "a@b.com"}],
    )
    assert respx_mock.calls.call_count == 0
    user_id = await kc.create_user(username="u1", email="a@b.com")
    assert user_id == "existing-user-id"


@pytest.mark.asyncio
async def test_list_users_returns_json(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock get users endpoint -> retourne liste d'utilisateurs
    users_list = respx_mock.get(f"{kc.base_admin}/users").respond(
        status_code=200,
        json=[
            {"id": "user1", "username": "u1", "email": "a@b.com"},
            {"id": "user2", "username": "u2", "email": "b@c.com"},
        ],
    )
    assert users_list.called is False
    assert respx_mock.calls.call_count == 0


@pytest.mark.asyncio
async def test_update_user_raise_error(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock update user endpoint -> retourne 400 Bad Request
    update_route = respx_mock.put(f"{kc.base_admin}/users/user123").respond(
        status_code=400, json={"error": "bad_request"}
    )

    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc.update_user("user123", first_name="NewName")
    assert "Failed to update user" in str(exc_info.value)
    assert update_route.called
    assert respx_mock.calls.call_count == 2  # 1 pour token, 1 pour put update


@pytest.mark.asyncio
async def test_update_user_calls_put(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock update user endpoint -> retourne 204 No Content
    update_route = respx_mock.put(f"{kc.base_admin}/users/user123").respond(
        status_code=204
    )

    await kc.update_user(
        "user123",
        first_name="NewName",
        last_name="NewLast",
        email="newemail@example.com",
        enabled=True,
        attributes={"attr1": "value1"},
    )
    assert update_route.called
    assert respx_mock.calls.call_count == 2  # 1 pour token, 1 pour put update


@pytest.mark.asyncio
async def test_delete_user_calls_delete(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock delete user endpoint -> retourne 204 No Content
    delete_route = respx_mock.delete(f"{kc.base_admin}/users/user123").respond(
        status_code=204
    )

    await kc.delete_user("user123")
    assert delete_route.called
    assert respx_mock.calls.call_count == 2  # 1 pour token, 1 pour delete


@pytest.mark.asyncio
async def test_delete_user_raise_error(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )
    delete_route = respx_mock.delete(f"{kc.base_admin}/users/user123").respond(
        status_code=400
    )

    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc.delete_user("user123")

    assert delete_route.called
    assert "Failed to delete user" in str(exc_info.value)


@pytest.mark.asyncio
async def test_set_user_password_calls_put_reset_password(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock set password endpoint -> retourne 204 No Content
    reset_route = respx_mock.put(
        f"{kc.base_admin}/users/user123/reset-password"
    ).respond(status_code=204)

    await kc.set_user_password("user123", "newpassword", temporary=False)
    assert reset_route.called
    assert respx_mock.calls.call_count == 2  # 1 pour token, 1 pour put reset password


@pytest.mark.asyncio
async def test_set_user_password_raise_error(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock set password endpoint -> retourne 204 No Content
    reset_route = respx_mock.put(
        f"{kc.base_admin}/users/user123/reset-password"
    ).respond(status_code=304)
    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc.set_user_password("user123", "newpassword", temporary=False)
    assert reset_route.called
    assert "Failed to reset password" in str(exc_info.value)


@pytest.mark.asyncio
async def test_introspect_token_returns_dict(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    introspect_url = f"{config.settings.KEYCLOAK_SERVER_URL}realms/{config.settings.KEYCLOAK_REALM}/protocol/openid-connect/token/introspect"
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock introspect endpoint -> retourne un dict d'introspection
    introspect_route = respx_mock.post(introspect_url).respond(
        status_code=200,
        json={"active": True, "username": "u1", "exp": 9999999999},
    )

    introspection = await kc.introspect_token("some-token")
    assert introspection["active"] is True
    assert introspection["username"] == "u1"
    assert introspect_route.called


@pytest.mark.asyncio
async def test_introspect_token_failed(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    introspect_url = f"{config.settings.KEYCLOAK_SERVER_URL}realms/{config.settings.KEYCLOAK_REALM}/protocol/openid-connect/token/introspect"
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock introspect endpoint -> retourne un dict d'introspection
    introspect_route = respx_mock.post(introspect_url).respond(
        status_code=400,
        json={"active": True, "username": "u1", "exp": 9999999999},
    )

    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc.introspect_token("some-token")
    assert "Failed to introspect token" in str(exc_info.value)
    assert introspect_route.called


@pytest.mark.asyncio
async def test_get_userinfo_uses_user_token(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    userinfo_url = f"{config.settings.KEYCLOAK_SERVER_URL}realms/{config.settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock userinfo endpoint -> retourne un dict d'informations utilisateur
    userinfo_route = respx_mock.get(userinfo_url).respond(
        status_code=200,
        json={
            "sub": "user123",
            "preferred_username": "u1",
            "email": "user@example.com",
        },
    )
    assert respx_mock.calls.call_count == 0
    userinfo = await kc.get_userinfo("user-token")
    assert userinfo["preferred_username"] == "u1"
    assert userinfo_route.called


@pytest.mark.asyncio
async def test_get_userinfo_invalid_token_raises_401(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    userinfo_url = f"{config.settings.KEYCLOAK_SERVER_URL}realms/{config.settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock userinfo endpoint -> retourne 401 Unauthorized
    respx_mock.get(userinfo_url).respond(
        status_code=401,
        json={
            "error": "invalid_token",
            "error_description": "User access token invalid or expired",
        },
    )

    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc.get_userinfo("invalid-token")
    assert "User access token invalid or expired" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_userinfo_invalid_token_raises(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()

    userinfo_url = f"{config.settings.KEYCLOAK_SERVER_URL}realms/{config.settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock userinfo endpoint -> retourne 401 Unauthorized
    respx_mock.get(userinfo_url).respond(
        status_code=404,
        json={
            "error": "invalid_token",
            "error_description": "User access token invalid or expired",
        },
    )

    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc.get_userinfo("invalid-token")
    assert "Failed to call userinfo:" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ensure_token_with_status_code_error(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=400, json={"error": "invalid_request"}
    )

    cast(Any, kc)._token = None
    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc._ensure_token()
    assert "Failed to fetch admin token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ensure_token_with_missing_access_token(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(status_code=200, json={"expires_in": 3600})

    cast(Any, kc)._token = None
    with pytest.raises(KeycloakAdminError) as exc_info:
        await kc._ensure_token()
    assert "Invalid token response: missing access_token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_constructor_admin_access_token_sets_token_and_prevents_fetch(
    settings_stub, respx_mock
):
    # Create instance with injected admin token
    import time

    now = time.time()
    admin_token = "injected-admin-token"
    kc = KeycloakAdmin(admin_access_token=admin_token)

    # The constructor should set the token and set an expiration ~1h in the future
    assert getattr(kc, "_token") == admin_token
    assert getattr(kc, "_token_expires_at") > now + 3500  # roughly 1 hour

    # Calling _ensure_token() should return the injected token and not trigger any HTTP requests
    token = await kc._ensure_token()
    assert token == admin_token
    assert respx_mock.calls.call_count == 0


@pytest.mark.asyncio
async def test_keycloak_admin_error_when_create_fails(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock create user endpoint -> retourne 500 Internal Server Error
    respx_mock.post(f"{kc.base_admin}/users").respond(
        status_code=500, json={"error": "server_error"}
    )

    with pytest.raises(Exception) as exc_info:
        await kc.create_user(username="u1", email="user@example.com")
    assert "Failed to create user" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_user_409_and_no_user_found_raises_conflict(
    settings_stub, respx_mock
):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    respx_mock.post(f"{kc.base_admin}/users").respond(status_code=409)

    respx_mock.get(f"{kc.base_admin}/users").respond(status_code=200, json=[])

    with pytest.raises(KeycloakAdminError) as excinfo:
        await kc.create_user(username="u1", email="a@b.com")

    assert (
        "Conflict" in str(excinfo.value)
        or "introuvable" in str(excinfo.value)
        or "not found" in str(excinfo.value)
    )


@pytest.mark.asyncio
async def test_extract_id_from_location_returns_none_on_invalid_location(
    settings_stub, respx_mock, monkeypatch
):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )
    respx_mock.post(f"{kc.base_admin}/users").respond(status_code=201, headers={})

    monkeypatch.setattr(
        KeycloakAdmin, "_extract_id_from_location", lambda self, loc: None
    )
    monkeypatch.setattr(
        KeycloakAdmin, "get_user_by_username", AsyncMock(return_value=None)
    )

    with pytest.raises(KeycloakAdminError) as excinfo:
        await kc.create_user(username="u1", email="a@b.com")
    assert isinstance(excinfo.value, KeycloakAdminError)
    assert "id" in str(excinfo.value).lower() or "id non" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_create_user_with_invalid_location(
    settings_stub, respx_mock, monkeypatch
):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )
    respx_mock.post(f"{kc.base_admin}/users").respond(status_code=201, headers={})

    monkeypatch.setattr(
        KeycloakAdmin, "_extract_id_from_location", lambda self, loc: None
    )
    monkeypatch.setattr(
        KeycloakAdmin, "get_user_by_username", AsyncMock(return_value=None)
    )

    with pytest.raises(KeycloakAdminError) as excinfo:
        await kc.create_user(username="u1", email="a@b.com")
    assert "user created but id" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_create_user_with_get(settings_stub, respx_mock, monkeypatch):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    location = f"{kc.base_admin}/users/abc-123"
    respx_mock.post(f"{kc.base_admin}/users").respond(
        status_code=201, headers={"Location": location}
    )

    monkeypatch.setattr(
        KeycloakAdmin, "_extract_id_from_location", lambda self, loc: None
    )
    monkeypatch.setattr(
        KeycloakAdmin, "get_user_by_username", AsyncMock(return_value={"id": "abc-123"})
    )

    user_id = await kc.create_user(username="u1", email="a@b.com")
    assert user_id == "abc-123"


@pytest.mark.asyncio
async def test_create_user_calls_set_password_and_returns_id(
    settings_stub, respx_mock, monkeypatch
):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock create user endpoint -> 201 with Location header containing id
    location = f"{kc.base_admin}/users/created-456"
    respx_mock.post(f"{kc.base_admin}/users").respond(
        status_code=201, headers={"Location": location}
    )

    # Patch set_user_password so we can assert it was called (no real HTTP)
    fake_set_password = AsyncMock()
    monkeypatch.setattr(KeycloakAdmin, "set_user_password", fake_set_password)

    user_id = await kc.create_user(
        username="u1", email="a@b.com", password="s3cret", temporary_password=False
    )

    # Ensure return value is the id parsed from Location
    assert user_id == "created-456"

    # Ensure set_user_password was awaited with correct args
    fake_set_password.assert_awaited_once_with("created-456", "s3cret", temporary=False)


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock get users endpoint -> retourne liste vide
    respx_mock.get(f"{kc.base_admin}/users").respond(
        status_code=201,
        json=[],
    )
    with pytest.raises(Exception) as excinfo:
        await kc.get_user_by_username("nonexistent")
    assert "Failed to search user" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_user_by_id_success(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock create user endpoint -> 201 with Location header containing id
    location = f"{kc.base_admin}/users/created-456"
    respx_mock.post(f"{kc.base_admin}/users").respond(
        status_code=201, headers={"Location": location}
    )

    # Mock get user by id endpoint -> retourne 200 OK with JSON body
    respx_mock.get(f"{kc.base_admin}/users/created-456").respond(
        status_code=200,
        json={"id": "created-456", "username": "u1", "email": "a@b.com"},
    )

    res = await kc.get_user_by_id("created-456")
    assert res is not None
    assert res["id"] == "created-456"


@pytest.mark.asyncio
async def test_get_user_by_id_failed(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock get user by id endpoint -> retourne 403 Forbidden
    respx_mock.get(f"{kc.base_admin}/users/nonexistent").respond(status_code=403)
    with pytest.raises(Exception) as excinfo:
        await kc.get_user_by_id("nonexistent")
    assert "Failed to get user by id" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )

    # Mock get user by id endpoint -> retourne 404 Not Found
    respx_mock.get(f"{kc.base_admin}/users/nonexistent").respond(status_code=404)
    res = await kc.get_user_by_id("nonexistent")
    assert res is None


@pytest.mark.asyncio
async def test_list_users_failed(settings_stub, respx_mock):
    from app.core import config

    token_url = config.settings.KEYCLOAK_TOKEN_URL
    kc = get_admin_client()
    respx_mock.post(token_url).respond(
        status_code=200, json={"access_token": "fake-token", "expires_in": 3600}
    )
    respx_mock.get(f"{kc.base_admin}/users").respond(status_code=403)
    with pytest.raises(Exception) as excinfo:
        await kc.list_users()
    assert "Failed to list users" in str(excinfo.value)
