import pytest
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.exceptions import UnauthorizedException
from app.core.keycloak_auth import KeycloakAuth, keycloak_auth


@pytest.mark.asyncio
async def test_verify_token_expired_signature(monkeypatch):
    # Bypass network call for public key
    monkeypatch.setattr(KeycloakAuth, "get_public_key", lambda self: "PEM")
    # Force ExpiredSignatureError from jose.jwt.decode
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *a, **k: (_ for _ in ()).throw(ExpiredSignatureError("exp")),
    )

    with pytest.raises(UnauthorizedException):
        await keycloak_auth.verify_token("token")


@pytest.mark.asyncio
async def test_verify_token_jwt_error(monkeypatch):
    monkeypatch.setattr(KeycloakAuth, "get_public_key", lambda self: "PEM")
    monkeypatch.setattr(
        jwt, "decode", lambda *a, **k: (_ for _ in ()).throw(JWTError("bad"))
    )

    with pytest.raises(UnauthorizedException):
        await keycloak_auth.verify_token("token")
