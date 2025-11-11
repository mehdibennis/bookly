import pytest

from app.api.v1.routes.admin_users import get_admin_client
from app.core.config import settings


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
async def test_admin_users_crud(client, monkeypatch):
    # Ensure service-account gate passes
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "dummy")

    fake = FakeKC()
    # Override dependency to use fake client
    from app.main import app

    app.dependency_overrides[get_admin_client] = lambda: fake

    # List empty
    r = await client.get("/api/v1/users")
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
    r = await client.post("/api/v1/users", json=payload)
    assert r.status_code == 201
    uid = r.json()["id"]

    # Get by id
    r = await client.get(f"/api/v1/users/{uid}")
    assert r.status_code == 200
    assert r.json()["id"] == uid

    # Update
    r = await client.put(f"/api/v1/users/{uid}", json={"email": "new@example.com"})
    assert r.status_code == 204
    r = await client.get(f"/api/v1/users/{uid}")
    assert r.json()["email"] == "new@example.com"

    # Set password
    r = await client.put(f"/api/v1/users/{uid}/password", json={"password": "NewP@ss1"})
    assert r.status_code == 204

    # Delete
    r = await client.delete(f"/api/v1/users/{uid}")
    assert r.status_code == 204

    # Not found after delete
    r = await client.get(f"/api/v1/users/{uid}")
    assert r.status_code == 404

    # cleanup override
    app.dependency_overrides.pop(get_admin_client, None)
