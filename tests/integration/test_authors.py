# moved from tests/test_integration_authors.py
# See git history for original authors

"""
Integration tests for Author routes.
Tests all CRUD operations with authentication.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
def mock_keycloak_auth(monkeypatch):
    """Mock Keycloak authentication for all author tests (also mocks Redis)."""
    # Ensure Redis cache does not perform real calls
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

    monkeypatch.setattr(redis_cache, "RedisCache", lambda url: MockRedisCache())

    from app.core.keycloak_auth import keycloak_auth

    class MockKeycloakOpenID:
        def public_key(self):
            return "fake_public_key"

        def userinfo(self, token):
            return {"email": "test@example.com", "sub": "user123"}

    monkeypatch.setattr(keycloak_auth, "keycloak_openid", MockKeycloakOpenID())

    # Mock JWT decode to return valid admin token
    fake_token_info = {
        "preferred_username": "admin",
        "realm_access": {"roles": ["admin", "user"]},
        "email": "admin@example.com",
        "exp": 9999999999,
    }

    with patch("app.core.keycloak_auth.jwt.decode", return_value=fake_token_info):
        yield


@pytest.mark.asyncio
async def test_list_authors_public_access(client: AsyncClient):
    """Test listing authors without authentication (public endpoint)."""
    response = await client.get("/api/v1/authors/?page=1&size=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)
    assert data["meta"]["page"] == 1
    assert data["meta"]["size"] == 10


@pytest.mark.asyncio
async def test_create_author_success(client: AsyncClient, mock_keycloak_auth):
    """Test creating a new author with authentication."""
    new_author = {
        "first_name": "TestJane",
        "last_name": "TestAusten",
        "birth_date": "1775-12-16",
        "death_date": "1817-07-18",
        "nationality": "British",
        "bio": "English novelist known for romantic fiction",
        "photo_url": "https://example.com/austen.jpg",
    }

    response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Testjane"
    assert data["last_name"] == "Testausten"
    assert data["nationality"] == "British"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_author_unauthorized(client: AsyncClient):
    """Test creating author without authentication fails."""
    # Force auth dependency to raise 401 for this test
    from app.core.exceptions import UnauthorizedException
    from app.core.keycloak_auth import get_current_user

    async def _raise_401():
        raise UnauthorizedException("Non authentifié")

    app.dependency_overrides[get_current_user] = _raise_401
    new_author = {
        "first_name": "Test",
        "last_name": "Author",
    }

    response = await client.post("/api/v1/authors/", json=new_author)
    assert response.status_code == 401
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_author_duplicate(client: AsyncClient, mock_keycloak_auth):
    """Test creating duplicate author returns conflict."""
    author_data = {
        "first_name": "Duplicate",
        "last_name": "Author",
    }

    # Create first author
    response1 = await client.post(
        "/api/v1/authors/",
        json=author_data,
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await client.post(
        "/api/v1/authors/",
        json=author_data,
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response2.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_get_author_by_id(client: AsyncClient, mock_keycloak_auth):
    """Test retrieving a specific author by ID."""
    # Create an author first
    new_author = {
        "first_name": "Charles",
        "last_name": "Dickens",
    }
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Get the author
    response = await client.get(f"/api/v1/authors/{author_id}", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["first_name"] == "Charles"
    assert data["last_name"] == "Dickens"


@pytest.mark.asyncio
async def test_get_author_not_found(client: AsyncClient, mock_keycloak_auth):
    """Test getting non-existent author returns 404."""
    response = await client.get("/api/v1/authors/99999", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_author_unauthorized(client: AsyncClient):
    """Test getting author without authentication fails."""
    from app.core.exceptions import UnauthorizedException
    from app.core.keycloak_auth import get_current_user

    async def _raise_401():
        raise UnauthorizedException("Non authentifié")

    app.dependency_overrides[get_current_user] = _raise_401
    response = await client.get("/api/v1/authors/1")
    assert response.status_code == 401
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_partial_update_author(client: AsyncClient, mock_keycloak_auth):
    """Test partial update (PATCH) of author with only some fields."""
    # Create an author
    new_author = {"first_name": "Mark", "last_name": "Twain", "nationality": "American"}
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Partial update - only nationality
    update_data = {"nationality": "United States"}
    response = await client.patch(
        f"/api/v1/authors/{author_id}",
        json=update_data,
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nationality"] == "United States"
    assert data["first_name"] == "Mark"  # Should remain unchanged
    assert data["last_name"] == "Twain"  # Should remain unchanged


@pytest.mark.asyncio
async def test_partial_update_author_not_found(client: AsyncClient, mock_keycloak_auth):
    """Test partial update of non-existent author."""
    response = await client.patch(
        "/api/v1/authors/99999",
        json={"nationality": "Test"},
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_partial_update_empty_name(client: AsyncClient, mock_keycloak_auth):
    """Test partial update with empty name fields fails validation."""
    # Create an author
    new_author = {
        "first_name": "Test",
        "last_name": "Author",
    }
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Try to update with empty first_name
    response = await client.patch(
        f"/api/v1/authors/{author_id}",
        json={"first_name": "   "},
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_author(client: AsyncClient, mock_keycloak_auth):
    """Test deleting an author."""
    # Create an author
    new_author = {
        "first_name": "Delete",
        "last_name": "Me",
    }
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Delete the author
    response = await client.delete(f"/api/v1/authors/{author_id}", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/authors/{author_id}", headers={"Authorization": "Bearer fake_token"})
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_author_not_found(client: AsyncClient, mock_keycloak_auth):
    """Test deleting non-existent author."""
    response = await client.delete("/api/v1/authors/99999", headers={"Authorization": "Bearer fake_token"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_author_unauthorized(client: AsyncClient):
    """Test deleting author without authentication fails."""
    from app.core.exceptions import UnauthorizedException
    from app.core.keycloak_auth import get_current_user

    async def _raise_401():
        raise UnauthorizedException("Non authentifié")

    app.dependency_overrides[get_current_user] = _raise_401
    response = await client.delete("/api/v1/authors/1")
    assert response.status_code == 401
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_authors_pagination(client: AsyncClient, mock_keycloak_auth):
    """Test pagination works correctly for listing authors."""
    # Create multiple authors
    for i in range(5):
        await client.post(
            "/api/v1/authors/",
            json={"first_name": f"Author{i}", "last_name": f"Test{i}"},
            headers={"Authorization": "Bearer fake_token"},
        )

    # Get page 1 with size 2
    response = await client.get("/api/v1/authors/?page=1&size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["size"] == 2
    assert data["meta"]["total"] >= 5


@pytest.mark.asyncio
async def test_partial_update_with_no_fields(client: AsyncClient, mock_keycloak_auth):
    """Test partial update with no fields returns existing author."""
    # Create an author
    new_author = {
        "first_name": "NoUpdate",
        "last_name": "Test",
    }
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Update with empty object
    response = await client.patch(
        f"/api/v1/authors/{author_id}",
        json={},
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Noupdate"  # Normalized
    assert data["last_name"] == "Test"


@pytest.mark.asyncio
async def test_get_author_by_id_success(client: AsyncClient, mock_keycloak_auth):
    """Test getting an author by ID."""
    # Create an author
    new_author = {"first_name": "GetTest", "last_name": "Author"}
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Get by ID
    response = await client.get(f"/api/v1/authors/{author_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["first_name"] == "Gettest"
    assert data["last_name"] == "Author"


@pytest.mark.asyncio
async def test_get_author_by_id_not_found(client: AsyncClient):
    """Test getting non-existent author returns 404."""
    response = await client.get("/api/v1/authors/999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_author_partial_fields(client: AsyncClient, mock_keycloak_auth):
    """Test PATCH with partial fields updates only specified fields."""
    # Create an author
    new_author = {
        "first_name": "Original",
        "last_name": "Name",
        "nationality": "USA",
    }
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # PATCH only first_name
    response = await client.patch(
        f"/api/v1/authors/{author_id}",
        json={"first_name": "Updated"},
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"  # Unchanged
    assert data["nationality"] == "USA"  # Unchanged


@pytest.mark.asyncio
async def test_delete_author_success(client: AsyncClient, mock_keycloak_auth):
    """Test deleting an author."""
    # Create an author
    new_author = {"first_name": "Delete", "last_name": "Me"}
    create_response = await client.post(
        "/api/v1/authors/",
        json=new_author,
        headers={"Authorization": "Bearer fake_token"},
    )
    author_id = create_response.json()["id"]

    # Delete
    response = await client.delete(
        f"/api/v1/authors/{author_id}",
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 204

    # Verify deleted
    response = await client.get(f"/api/v1/authors/{author_id}")
    assert response.status_code == 404
