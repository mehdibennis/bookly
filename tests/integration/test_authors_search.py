import pytest
from httpx import AsyncClient

from app.core.url_helpers import reverse
from app.main import app as fastapi_app
from tests.conftest import get_auth_headers


@pytest.mark.asyncio
async def test_list_authors_with_search_filters_results(
    client: AsyncClient, mock_keycloak_auth
):
    headers = get_auth_headers()
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
    create_path = reverse(fastapi_app, "authors:create")
    r1 = await client.post(create_path, json=a1, headers=headers)
    r2 = await client.post(create_path, json=a2, headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201

    search_path = reverse(fastapi_app, "authors:list")
    params = {"page": 1, "size": 10, "search": "ver"}
    # Search by partial last name (case-insensitive)
    resp = await client.get(search_path, params=params, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    names = {(a["first_name"], a["last_name"]) for a in data["data"]}
    assert ("Jules", "Verne") in names
    assert ("Victor", "Hugo") not in names
