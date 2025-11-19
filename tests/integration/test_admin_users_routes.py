import pytest

from app.api.v1.routes.admin_users import get_admin_client
from app.core.config import settings
from app.core.keycloak_admin import KeycloakAdminError
from app.core.url_helpers import reverse
from app.main import app as fastapi_app


class FakeKC:
    def __init__(self):
        self._users = {}
        self._counter = 0

    async def list_users(self):
        return list(self._users.values())

    async def create_user(self, **kwargs):
        self._counter += 1
        uid = f"u{self._counter}"
        user = {
            "id": uid,
            "username": kwargs.get("username"),
            "email": kwargs.get("email"),
        }
        self._users[uid] = user
        return uid

    async def get_user_by_id(self, user_id: str):
        return self._users.get(user_id)

    async def update_user(self, user_id: str, **kwargs):
        if user_id in self._users:
            self._users[user_id].update(
                {k: v for k, v in kwargs.items() if v is not None}
            )

    async def set_user_password(
        self, user_id: str, password: str, *, temporary: bool = False
    ):
        # no-op in fake
        return None

    async def delete_user(self, user_id: str):
        self._users.pop(user_id, None)


@pytest.mark.asyncio
async def test_admin_users_list_raise_keycloakadminerror(client, monkeypatch):
    # Ensure service-account gate passes
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "dummy")

    class FailingFakeKC:
        async def list_users(self):
            raise KeycloakAdminError("Keycloak error")

    # Override dependency to use failing fake client
    from app.main import app

    app.dependency_overrides[get_admin_client] = lambda: FailingFakeKC()
    list_path = reverse(fastapi_app, "admin_users:list")
    r = await client.get(list_path)
    assert r.status_code == 502
    # cleanup override
    app.dependency_overrides.pop(get_admin_client, None)


@pytest.mark.asyncio
async def test_admin_users_crud(client, monkeypatch):
    # Ensure service-account gate passes
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "dummy")

    fake = FakeKC()
    # Override dependency to use fake client
    from app.main import app

    app.dependency_overrides[get_admin_client] = lambda: fake

    # List empty
    list_path = reverse(fastapi_app, "admin_users:list")
    r = await client.get(list_path)
    assert r.status_code == 200
    assert r.json() == []

    # Create
    payload = {
        "username": "tuser",
        "email": "t@example.com",
        "firstName": "T",
        "lastName": "User",
        "password": "Passw0rd!",
        "enabled": True,
    }
    create_path = reverse(fastapi_app, "admin_users:create")
    r = await client.post(create_path, json=payload)
    assert r.status_code == 201
    uid = r.json()["id"]

    # Get by id
    get_path = reverse(fastapi_app, "admin_users:get", user_id=uid)
    r = await client.get(get_path)
    assert r.status_code == 200
    assert r.json()["id"] == uid

    # Update
    update_path = reverse(fastapi_app, "admin_users:update", user_id=uid)
    r = await client.put(update_path, json={"email": "new@example.com"})
    assert r.status_code == 204
    get_path = reverse(fastapi_app, "admin_users:get", user_id=uid)
    r = await client.get(get_path)
    assert r.json()["email"] == "new@example.com"

    # Set password
    password_path = reverse(fastapi_app, "admin_users:set_password", user_id=uid)
    r = await client.put(password_path, json={"password": "NewP@ss1"})
    assert r.status_code == 204

    # Delete
    delete_path = reverse(fastapi_app, "admin_users:delete", user_id=uid)
    r = await client.delete(delete_path)
    assert r.status_code == 204

    # Not found after delete
    get_path = reverse(fastapi_app, "admin_users:get", user_id=uid)
    r = await client.get(get_path)
    assert r.status_code == 404

    # cleanup override
    app.dependency_overrides.pop(get_admin_client, None)
