from uuid import uuid4

import pytest

from app.core.url_helpers import reverse
from app.main import app as fastapi_app
from tests.conftest import get_auth_headers, get_rate_limit_headers


@pytest.mark.usefixtures("auth_for_class", "override_keycloak")
class TestAPI:
    @pytest.mark.asyncio
    async def test_login_and_ping(self, client):
        headers = get_auth_headers()
        path = reverse(fastapi_app, "ping")

        resp = await client.get(path, headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        headers = get_auth_headers()
        params = {"page": 1, "size": 2}
        path = reverse(fastapi_app, "books:list")

        resp = await client.get(path, params=params, headers=headers)
        assert resp.status_code == 200
        assert "data" in resp.json()
        meta = resp.json()["meta"]
        assert meta["page"] == 1
        assert meta["size"] == 2

    @pytest.mark.asyncio
    async def test_throttling(self, client):
        # Rate limiting per IP
        rate_headers = get_rate_limit_headers(ip_suffix=10)
        path = reverse(fastapi_app, "books:list")

        for _ in range(5):
            await client.get(path, headers=rate_headers)

    @pytest.mark.asyncio
    async def test_create_book(self, client, test_author_id):
        headers = get_auth_headers()
        path = reverse(fastapi_app, "books:create")

        book_data = {"title": f"New Book {uuid4()}", "authors": [test_author_id]}
        resp = await client.post(path, json=book_data, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["title"].startswith("New Book ")
        assert resp.json()["authors"] == [test_author_id]

    @pytest.mark.asyncio
    async def test_delete_book(self, client, test_author_id):
        headers = get_auth_headers()
        create_path = reverse(fastapi_app, "books:create")

        # First create a book
        book_data = {"title": f"To Delete {uuid4()}", "authors": [test_author_id]}
        resp = await client.post(create_path, json=book_data, headers=headers)
        assert resp.status_code == 201
        book_id = resp.json()["id"]

        # Then delete it
        delete_path = reverse(fastapi_app, "books:delete", book_id=book_id)
        resp = await client.delete(delete_path, headers=headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        headers = get_auth_headers()
        get_404 = reverse(fastapi_app, "books:get", book_id=99999)

        resp = await client.get(get_404, headers=headers)
        assert resp.status_code == 404

        create_path = reverse(fastapi_app, "books:create")
        resp = await client.post(create_path, json={"title": ""}, headers=headers)
        assert resp.status_code == 422

        resp = await client.post(create_path, json={}, headers=headers)
        assert resp.status_code == 422

        path = reverse(fastapi_app, "ping")

        resp = await client.get(path, headers=headers)
        assert resp.status_code == 200
