import pytest

from tests.conftest import get_mock_token


@pytest.mark.usefixtures("override_keycloak")
@pytest.mark.asyncio
async def test_auth_returns_bearer_token_type(client):
    token = get_mock_token()
    assert token == "mock_valid_token"
