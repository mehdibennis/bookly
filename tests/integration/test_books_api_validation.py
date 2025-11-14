from uuid import uuid4

import pytest

from tests.conftest import get_unique_rate_headers


@pytest.mark.usefixtures("override_keycloak")
@pytest.mark.asyncio
async def test_create_book_empty_title_400(client, test_author_id):
    headers = get_unique_rate_headers(ip_range="203.0.113")

    # Title empty but authors provided -> 400 (ValueError in service)
    r = await client.post(
        "/api/v1/books/",
        json={"title": "   ", "authors": [test_author_id]},
        headers=headers,
    )
    assert r.status_code == 400


@pytest.mark.usefixtures("override_keycloak")
@pytest.mark.asyncio
async def test_update_book_no_changes_ok(client, test_author_id):
    headers = get_unique_rate_headers()

    # Create
    title = f"NoChange {uuid4()}"
    r = await client.post(
        "/api/v1/books/",
        json={"title": title, "authors": [test_author_id]},
        headers=headers,
    )
    assert r.status_code == 201
    book = r.json()

    # Update with empty body (no fields changed)
    r = await client.patch(f"/api/v1/books/{book['id']}", json={}, headers=headers)
    assert r.status_code == 200
    updated = r.json()
    assert updated["title"].startswith("Nochange ")  # normalized
    assert updated["authors"] == [test_author_id]
