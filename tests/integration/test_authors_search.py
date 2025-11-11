from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.fixture
def mock_keycloak_auth(monkeypatch):
    # Fake Redis cache for authors paging
    from app.core import redis_cache

    class MockRedisCache:
        async def connect(self):
            pass

        async def close(self):
            pass

        async def get_authors_page(self, page, size):
            return None

        async def set_authors_page(self, page, size, data):
            pass

        async def get_authors_page_search(self, page, size, search):
            return None

        async def set_authors_page_search(self, page, size, search, data):
            pass

    monkeypatch.setattr(redis_cache, "RedisCache", lambda url: MockRedisCache())

    from app.core.keycloak_auth import keycloak_auth

    class MockKeycloakOpenID:
        def public_key(self):
            return "fake_public_key"

        def userinfo(self, token):
            return {"email": "test@example.com", "sub": "user123"}

    monkeypatch.setattr(keycloak_auth, "keycloak_openid", MockKeycloakOpenID())

    fake_token_info = {
        "preferred_username": "admin",
        "realm_access": {"roles": ["admin", "user"]},
        "email": "admin@example.com",
        "exp": 9999999999,
    }

    with patch("app.core.keycloak_auth.jwt.decode", return_value=fake_token_info):
        yield


@pytest.mark.asyncio
async def test_list_authors_with_search_filters_results(client: AsyncClient, mock_keycloak_auth):
    # Create a couple of authors
    a1 = {
        "first_name": "Jules",
        "last_name": "Verne",
        "nationality": "French",
    }
    a2 = {
        "first_name": "Victor",
        "last_name": "Hugo",
        "nationality": "French",
    }
    r1 = await client.post("/api/v1/authors/", json=a1, headers={"Authorization": "Bearer fake_token"})
    r2 = await client.post("/api/v1/authors/", json=a2, headers={"Authorization": "Bearer fake_token"})
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)

    # Search by partial last name (case-insensitive)
    resp = await client.get("/api/v1/authors/?page=1&size=10&search=ver")
    assert resp.status_code == 200
    data = resp.json()
    names = {(a["first_name"], a["last_name"]) for a in data["data"]}
    assert ("Jules", "Verne") in names
    assert ("Victor", "Hugo") not in names
