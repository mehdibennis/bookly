from unittest.mock import patch

import pytest

from app.core.keycloak_auth import get_current_user, keycloak_auth


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch):
    """Test successful JWT verification and user extraction."""

    class Dummy:
        def public_key(self):
            return "fake_public_key"

        def userinfo(self, token):
            return {"email": "demo@example.com", "sub": "user123"}

    monkeypatch.setattr(keycloak_auth, "keycloak_openid", Dummy())

    # Mock JWT decode to return valid token info
    fake_token_info = {
        "preferred_username": "demo",
        "realm_access": {"roles": ["user"]},
        "email": "demo@example.com",
        "exp": 9999999999,  # Far future expiration
    }

    with patch("app.core.keycloak_auth.jwt.decode", return_value=fake_token_info):
        # Simulate credentials object
        class Creds:
            credentials = "token123"

        user = await get_current_user(Creds())
        assert user.username == "demo"
        assert user.email == "demo@example.com"


@pytest.mark.asyncio
async def test_get_current_user_verify_failure(monkeypatch):
    """Test JWT verification failure (invalid signature)."""
    from jose import JWTError

    from app.core.exceptions import UnauthorizedException

    class Dummy:
        def public_key(self):
            return "fake_public_key"

    monkeypatch.setattr(keycloak_auth, "keycloak_openid", Dummy())

    # Mock JWT decode to raise JWTError (invalid signature)
    with patch("app.core.keycloak_auth.jwt.decode", side_effect=JWTError("Invalid signature")):

        class Creds:
            credentials = "bad_token"

        with pytest.raises(UnauthorizedException) as exc:
            await get_current_user(Creds())
        assert exc.value.status_code == 401
        assert "invalide" in str(exc.value.message).lower()


@pytest.mark.asyncio
async def test_get_current_user_userinfo_failure(monkeypatch):
    """Test when userinfo call fails but token is valid."""

    class Dummy:
        def public_key(self):
            return "fake_public_key"

        def userinfo(self, token):
            raise Exception("Keycloak userinfo endpoint unavailable")

    monkeypatch.setattr(keycloak_auth, "keycloak_openid", Dummy())

    # Mock JWT decode to return valid token info
    fake_token_info = {
        "preferred_username": "demo2",
        "realm_access": {"roles": []},
        "exp": 9999999999,
    }

    with patch("app.core.keycloak_auth.jwt.decode", return_value=fake_token_info):

        class Creds:
            credentials = "tok"

        user = await get_current_user(Creds())
        assert user.username == "demo2"
        # email absent in token_info -> property returns None
        assert user.email is None
