"""
Integration tests for Author routes.
Tests all CRUD operations with authentication.
"""

import pytest
from httpx import AsyncClient

from app.core.url_helpers import reverse
from app.main import app
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_list_authors_public_access(client: AsyncClient):
    """Test listing authors without authentication (public endpoint)."""
    path = reverse(app, "authors:list")
    params = {"page": 1, "size": 10}
    response = await client.get(path, params=params)
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
    headers = get_auth_headers()
    new_author = {
        "first_name": "TestJane",
        "last_name": "TestAusten",
        "birth_date": "1775-12-16",
        "death_date": "1817-07-18",
        "nationality": "British",
        "bio": "English novelist known for romantic fiction",
        "photo_url": "https://example.com/austen.jpg",
    }
    path = reverse(app, "authors:create")

    response = await client.post(
        path,
        json=new_author,
        headers=headers,
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
    path = reverse(app, "authors:create")

    response = await client.post(path, json=new_author)
    assert response.status_code == 401
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_create_author_duplicate(client: AsyncClient, mock_keycloak_auth):
    """Test creating duplicate author returns conflict."""
    author_data = {
        "first_name": "Duplicate",
        "last_name": "Author",
    }
    headers = get_auth_headers()
    create_path = reverse(app, "authors:create")

    # Create first author

    response1 = await client.post(
        create_path,
        json=author_data,
        headers=headers,
    )
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = await client.post(
        create_path,
        json=author_data,
        headers=headers,
    )
    assert response2.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_get_author_by_id(client: AsyncClient, mock_keycloak_auth):
    """Test retrieving a specific author by ID."""
    # Create an author first
    headers = get_auth_headers()
    new_author = {
        "first_name": "Charles",
        "last_name": "Dickens",
    }
    create_path = reverse(app, "authors:create")
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Get the author
    get_path = reverse(app, "authors:get", author_id=author_id)
    response = await client.get(get_path, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["first_name"] == "Charles"
    assert data["last_name"] == "Dickens"


@pytest.mark.asyncio
async def test_get_author_not_found(client: AsyncClient, mock_keycloak_auth):
    """Test getting non-existent author returns 404."""
    headers = get_auth_headers()
    path = reverse(app, "authors:get", author_id=99999)
    response = await client.get(path, headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_author_unauthorized(client: AsyncClient):
    """Test getting author without authentication fails."""
    from app.core.exceptions import UnauthorizedException
    from app.core.keycloak_auth import get_current_user

    async def _raise_401():
        raise UnauthorizedException("Non authentifié")

    path = reverse(app, "authors:get", author_id=1)

    app.dependency_overrides[get_current_user] = _raise_401
    response = await client.get(path)
    assert response.status_code == 401
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_partial_update_author(client: AsyncClient, mock_keycloak_auth):
    """Test partial update (PATCH) of author with only some fields."""
    headers = get_auth_headers()
    # Create an author
    new_author = {"first_name": "Mark", "last_name": "Twain", "nationality": "American"}
    create_path = reverse(app, "authors:create")
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Partial update - only nationality
    update_data = {"nationality": "United States"}
    update_path = reverse(app, "authors:update", author_id=author_id)
    response = await client.patch(
        update_path,
        json=update_data,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nationality"] == "United States"
    assert data["first_name"] == "Mark"  # Should remain unchanged
    assert data["last_name"] == "Twain"  # Should remain unchanged


@pytest.mark.asyncio
async def test_partial_update_author_not_found(client: AsyncClient, mock_keycloak_auth):
    """Test partial update of non-existent author."""
    headers = get_auth_headers()
    path = reverse(app, "authors:update", author_id=99999)
    response = await client.patch(
        path,
        json={"nationality": "Test"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_partial_update_empty_name(client: AsyncClient, mock_keycloak_auth):
    """Test partial update with empty name fields fails validation."""

    headers = get_auth_headers()
    create_path = reverse(app, "authors:create")
    # Create an author
    new_author = {
        "first_name": "Test",
        "last_name": "Author",
    }
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Try to update with empty first_name
    update_path = reverse(app, "authors:update", author_id=author_id)
    response = await client.patch(
        update_path,
        json={"first_name": "   "},
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_author(client: AsyncClient, mock_keycloak_auth):
    """Test deleting an author."""
    headers = get_auth_headers()
    # Create an author
    create_path = reverse(app, "authors:create")
    new_author = {
        "first_name": "Delete",
        "last_name": "Me",
    }
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Delete the author
    update_path = reverse(app, "authors:update", author_id=author_id)
    response = await client.delete(update_path, headers=headers)
    assert response.status_code == 204

    # Verify it's deleted
    get_path = reverse(app, "authors:get", author_id=author_id)
    get_response = await client.get(get_path, headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_author_not_found(client: AsyncClient, mock_keycloak_auth):
    """Test deleting non-existent author."""
    headers = get_auth_headers()
    delete_path = reverse(app, "authors:update", author_id=99999)
    response = await client.delete(delete_path, headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_author_unauthorized(client: AsyncClient):
    """Test deleting author without authentication fails."""
    from app.core.exceptions import UnauthorizedException
    from app.core.keycloak_auth import get_current_user

    async def _raise_401():
        raise UnauthorizedException("Non authentifié")

    app.dependency_overrides[get_current_user] = _raise_401
    delete_path = reverse(app, "authors:update", author_id=1)
    response = await client.delete(delete_path)
    assert response.status_code == 401
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_authors_pagination(client: AsyncClient, mock_keycloak_auth):
    """Test pagination works correctly for listing authors."""
    # Create multiple authors
    headers = get_auth_headers()
    create_path = reverse(app, "authors:create")
    for i in range(5):
        await client.post(
            create_path,
            json={"first_name": f"Author{i}", "last_name": f"Test{i}"},
            headers=headers,
        )

    # Get page 1 with size 2
    list_path = reverse(app, "authors:list")
    params = {"page": 1, "size": 2}
    response = await client.get(list_path, params=params)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["size"] == 2
    assert data["meta"]["total"] >= 5


@pytest.mark.asyncio
async def test_partial_update_with_no_fields(client: AsyncClient, mock_keycloak_auth):
    """Test partial update with no fields returns existing author."""
    headers = get_auth_headers()
    # Create an author
    create_path = reverse(app, "authors:create")
    new_author = {
        "first_name": "NoUpdate",
        "last_name": "Test",
    }
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Update with empty object
    update_path = reverse(app, "authors:update", author_id=author_id)
    response = await client.patch(
        update_path,
        json={},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Noupdate"  # Normalized
    assert data["last_name"] == "Test"


@pytest.mark.asyncio
async def test_get_author_by_id_success(client: AsyncClient, mock_keycloak_auth):
    """Test getting an author by ID."""
    headers = get_auth_headers()
    create_path = reverse(app, "authors:create")
    # Create an author
    new_author = {"first_name": "GetTest", "last_name": "Author"}
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Get by ID
    get_path = reverse(app, "authors:get", author_id=author_id)
    response = await client.get(get_path, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == author_id
    assert data["first_name"] == "Gettest"
    assert data["last_name"] == "Author"


@pytest.mark.asyncio
async def test_get_author_by_id_not_found(client: AsyncClient):
    """Test getting non-existent author returns 404."""
    path = reverse(app, "authors:get", author_id=999999)
    response = await client.get(path)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_author_partial_fields(client: AsyncClient, mock_keycloak_auth):
    """Test PATCH with partial fields updates only specified fields."""
    headers = get_auth_headers()
    # Create an author
    create_path = reverse(app, "authors:create")
    new_author = {
        "first_name": "Original",
        "last_name": "Name",
        "nationality": "USA",
    }
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # PATCH only first_name
    update_path = reverse(app, "authors:update", author_id=author_id)
    response = await client.patch(
        update_path,
        json={"first_name": "Updated"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"  # Unchanged
    assert data["nationality"] == "USA"  # Unchanged


@pytest.mark.asyncio
async def test_delete_author_success(client: AsyncClient, mock_keycloak_auth):
    """Test deleting an author."""
    headers = get_auth_headers()
    # Create an author
    create_path = reverse(app, "authors:create")
    new_author = {"first_name": "Delete", "last_name": "Me"}
    create_response = await client.post(
        create_path,
        json=new_author,
        headers=headers,
    )
    author_id = create_response.json()["id"]

    # Delete
    delete_path = reverse(app, "authors:delete", author_id=author_id)
    response = await client.delete(
        delete_path,
        headers=headers,
    )
    assert response.status_code == 204

    # Verify deleted
    get_path = reverse(app, "authors:get", author_id=author_id)
    response = await client.get(get_path, headers=headers)
    assert response.status_code == 404
