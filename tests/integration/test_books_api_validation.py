from uuid import uuid4

import pytest

from app.core.url_helpers import reverse
from app.main import app as fastapi_app
from tests.conftest import get_unique_rate_headers


@pytest.mark.usefixtures("override_keycloak")
@pytest.mark.asyncio
async def test_create_book_empty_title_400(client, test_author_id):
    headers = get_unique_rate_headers(ip_range="203.0.113")
    create_path = reverse(fastapi_app, "books:create")
    data = {"title": "   ", "authors": [test_author_id]}

    # Title empty but authors provided -> 400 (ValueError in service)
    r = await client.post(
        create_path,
        json=data,
        headers=headers,
    )
    assert r.status_code == 400


@pytest.mark.usefixtures("override_keycloak")
@pytest.mark.asyncio
async def test_update_book_no_changes_ok(client, test_author_id):
    headers = get_unique_rate_headers()
    create_path = reverse(fastapi_app, "books:create")
    title = f"NoChange {uuid4()}"
    data = {"title": title, "authors": [test_author_id]}
    # Create
    r = await client.post(
        create_path,
        json=data,
        headers=headers,
    )
    assert r.status_code == 201
    book = r.json()

    # Update with empty body (no fields changed)
    update_path = reverse(fastapi_app, "books:update", book_id=book["id"])
    r = await client.patch(update_path, json={}, headers=headers)
    assert r.status_code == 200
    updated = r.json()
    assert updated["title"].startswith("Nochange ")  # normalized
    assert updated["authors"] == [test_author_id]
