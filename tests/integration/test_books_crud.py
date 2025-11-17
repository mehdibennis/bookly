from uuid import uuid4

import pytest

from app.core.url_helpers import reverse
from app.main import app as fastapi_app
from tests.conftest import get_unique_rate_headers


@pytest.mark.usefixtures("override_keycloak")
class TestBooksCrud:

    @pytest.mark.asyncio
    async def test_delete_book_and_404_after(self, client):
        headers = get_unique_rate_headers()
        data = {"first_name": "Jim", "last_name": f"Beam {uuid4()}"}

        author_create_path = reverse(fastapi_app, "authors:create")
        # Create an author for testing
        ar = await client.post(
            author_create_path,
            json=data,
            headers=headers,
        )
        assert ar.status_code == 201
        author_id = ar.json()["id"]

        # Create
        title = f"ToDelete {uuid4()}"
        data = {"title": title, "authors": [author_id]}
        book_create_path = reverse(fastapi_app, "books:create")

        r = await client.post(
            book_create_path,
            json=data,
            headers=headers,
        )
        assert r.status_code == 201
        book_id = r.json()["id"]

        # Delete
        book_delete_path = reverse(fastapi_app, "books:delete", book_id=book_id)
        r = await client.delete(book_delete_path, headers=headers)
        assert r.status_code == 204

        # Ensure it's gone
        book_get_path = reverse(fastapi_app, "books:get", book_id=book_id)
        r = await client.get(book_get_path, headers=headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_book_by_id_success(self, client):
        headers = get_unique_rate_headers()
        data = {"first_name": "Get", "last_name": f"Test {uuid4()}"}
        # Create author and book
        author_create_path = reverse(fastapi_app, "authors:create")
        ar = await client.post(
            author_create_path,
            json=data,
            headers=headers,
        )
        author_id = ar.json()["id"]

        title = f"GetById {uuid4()}"
        book_create_path = reverse(fastapi_app, "books:create")
        data = {"title": title, "authors": [author_id]}
        r = await client.post(
            book_create_path,
            json=data,
            headers=headers,
        )
        assert r.status_code == 201
        book_id = r.json()["id"]

        # Get by ID
        book_get_path = reverse(fastapi_app, "books:get", book_id=book_id)
        r = await client.get(book_get_path, headers=headers)
        assert r.status_code == 200
        book = r.json()
        assert book["id"] == book_id
        assert "title" in book
        assert book["authors"] == [author_id]

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, client):
        headers = get_unique_rate_headers()
        book_get_path = reverse(fastapi_app, "books:get", book_id=999999)
        r = await client.get(book_get_path, headers=headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_book_partial_update(self, client):
        headers = get_unique_rate_headers()

        # Create author and book
        author_create_path = reverse(fastapi_app, "authors:create")
        data = {"first_name": "Patch", "last_name": f"Test {uuid4()}"}
        ar = await client.post(
            author_create_path,
            json=data,
            headers=headers,
        )
        author_id = ar.json()["id"]

        title = f"PatchMe {uuid4()}"
        book_create_path = reverse(fastapi_app, "books:create")
        data = {"title": title, "authors": [author_id]}
        r = await client.post(
            book_create_path,
            json=data,
            headers=headers,
        )
        assert r.status_code == 201
        book_id = r.json()["id"]

        # PATCH only title
        new_title = f"patched {uuid4()}"
        book_patch_path = reverse(fastapi_app, "books:update", book_id=book_id)
        r = await client.patch(
            book_patch_path,
            json={"title": new_title},
            headers=headers,
        )
        assert r.status_code == 200
        updated = r.json()
        assert updated["title"].startswith("Patched")
        assert updated["authors"] == [author_id]

    @pytest.mark.asyncio
    async def test_list_books_paginated(self, client):
        headers = get_unique_rate_headers()
        # Get first page
        params = {"page": 1, "size": 10}
        book_list_path = reverse(fastapi_app, "books:list")
        r = await client.get(book_list_path, params=params, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert data["meta"]["page"] == 1
        assert data["meta"]["size"] == 10

    @pytest.mark.asyncio
    async def test_pagination_navigation_meta(self, client):
        headers = get_unique_rate_headers()
        author_create_path = reverse(fastapi_app, "authors:create")
        data = {"first_name": "Pag", "last_name": f"Ination {uuid4()}"}
        # Create an author for testing
        ar = await client.post(
            author_create_path,
            json=data,
            headers=headers,
        )
        assert ar.status_code == 201
        author_id = ar.json()["id"]

        # Ensure enough books to paginate (create 3 new)
        books_create_path = reverse(fastapi_app, "books:create")
        for _ in range(3):
            await client.post(
                books_create_path,
                json={"title": f"Page {uuid4()}", "authors": [author_id]},
                headers=headers,
            )

        # Ask page 2 with size 2
        params = {"page": 2, "size": 2}
        book_list_path = reverse(fastapi_app, "books:list")
        r = await client.get(book_list_path, params=params, headers=headers)
        assert r.status_code == 200
        meta = r.json()["meta"]
        assert meta["page"] == 2
        assert meta["size"] == 2
        assert meta["previous_page"] == 1
        assert meta["next_page"] is None
        assert meta["last_page"] == 2
        assert meta["total"] == 3

    @pytest.mark.asyncio
    async def test_unauthorized_create_book(self, client):
        # No token
        path = reverse(fastapi_app, "books:create")
        r = await client.post(path, json={"title": f"NoAuth {uuid4()}"})
        assert r.status_code == 422
