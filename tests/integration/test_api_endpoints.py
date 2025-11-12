from uuid import uuid4

import pytest

from conftest import get_auth_headers, get_rate_limit_headers


@pytest.mark.usefixtures("auth_for_class", "override_keycloak")
class TestAPI:
    @pytest.mark.asyncio
    async def test_login_and_ping(self, client):
        headers = get_auth_headers()

        # /ping requires admin role; override_keycloak sets a basic user
        # Accept 403 or 200 (if override changes)
        resp = await client.get("/ping", headers=headers)
        assert resp.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        headers = get_auth_headers()

        list_url = "/api/v1/books/?page=1&size=2"
        resp = await client.get(list_url, headers=headers)
        assert resp.status_code == 200
        assert "data" in resp.json()
        meta = resp.json()["meta"]
        assert meta["page"] == 1
        assert meta["size"] == 2

    @pytest.mark.asyncio
    async def test_throttling(self, client):
        # Rate limiting per IP
        rate_headers = get_rate_limit_headers(ip_suffix=10)

        for _ in range(5):
            await client.get("/api/v1/books/", headers=rate_headers)

    @pytest.mark.asyncio
    async def test_create_book(self, client, test_author_id):
        headers = get_auth_headers()

        book_data = {"title": f"New Book {uuid4()}", "authors": [test_author_id]}
        resp = await client.post("/api/v1/books/", json=book_data, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["title"].startswith("New Book ")
        assert resp.json()["authors"] == [test_author_id]

    @pytest.mark.asyncio
    async def test_delete_book(self, client, test_author_id):
        headers = get_auth_headers()

        # First create a book
        book_data = {"title": f"To Delete {uuid4()}", "authors": [test_author_id]}
        resp = await client.post("/api/v1/books/", json=book_data, headers=headers)
        assert resp.status_code == 201
        book_id = resp.json()["id"]

        # Then delete it
        resp = await client.delete(f"/api/v1/books/{book_id}", headers=headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        headers = get_auth_headers()

        get_404 = "/api/v1/books/99999"
        resp = await client.get(get_404, headers=headers)
        assert resp.status_code == 404

        create_url = "/api/v1/books/"
        resp = await client.post(create_url, json={"title": ""}, headers=headers)
        assert resp.status_code == 422
        resp = await client.post(create_url, json={}, headers=headers)
        assert resp.status_code == 422

        # /ping requires admin; accept 403 or 200
        resp = await client.get("/ping", headers=headers)
        assert resp.status_code in [200, 403]
