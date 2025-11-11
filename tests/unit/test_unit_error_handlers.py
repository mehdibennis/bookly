import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError

from app.core.error_handlers import (
    app_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
    value_error_handler,
)
from app.core.exceptions import AppException
from app.main import app


class DummyRequest:
    def __init__(self, url="http://test/api/v1/books/1", method="GET"):
        self.url = url
        self.method = method


@pytest.mark.asyncio
async def test_app_exception_handler_direct():
    req = DummyRequest()
    exc = AppException("Custom error", status_code=418)
    resp = await app_exception_handler(req, exc)
    assert resp.status_code == 418
    assert "Custom error" in resp.body.decode()


@pytest.mark.asyncio
async def test_validation_exception_handler_single_missing():
    req = DummyRequest()
    exc = RequestValidationError(
        [{"loc": ["body", "title"], "type": "missing", "msg": "field required"}]
    )
    resp = await validation_exception_handler(req, exc)
    assert resp.status_code == 422
    assert b"requis" in resp.body


@pytest.mark.asyncio
async def test_validation_exception_handler_multiple():
    req = DummyRequest()
    exc = RequestValidationError(
        [
            {"loc": ["body", "title"], "type": "missing", "msg": "field required"},
            {"loc": ["body", "author"], "type": "missing", "msg": "field required"},
        ]
    )
    resp = await validation_exception_handler(req, exc)
    assert resp.status_code == 422
    assert b"Erreurs de validation" in resp.body


@pytest.mark.asyncio
async def test_value_error_handler_direct():
    req = DummyRequest()
    exc = ValueError("Invalid value!")
    resp = await value_error_handler(req, exc)
    assert resp.status_code == 400
    assert b"Invalid value!" in resp.body


@pytest.mark.asyncio
async def test_generic_exception_handler_debug(monkeypatch):
    req = DummyRequest()
    exc = RuntimeError("Something went wrong!")
    # Force debug mode
    monkeypatch.setattr("app.core.config.settings.DEBUG", True)
    resp = await generic_exception_handler(req, exc)
    assert resp.status_code == 500
    assert b"Erreur interne du serveur" in resp.body
    assert b"debug_details" in resp.body


@pytest.mark.asyncio
async def test_generic_exception_handler_prod(monkeypatch):
    req = DummyRequest()
    exc = RuntimeError("Something went wrong!")
    # Force prod mode
    monkeypatch.setattr("app.core.config.settings.DEBUG", False)
    resp = await generic_exception_handler(req, exc)
    assert resp.status_code == 500
    assert b"Erreur interne du serveur" in resp.body
    assert b"debug_details" not in resp.body


@pytest.mark.asyncio
async def test_app_exception_handler(client):
    # Dynamically add a route that raises AppException
    @app.get("/_raise_app")
    async def raise_app():  # pragma: no cover - dynamic wiring
        raise AppException("Custom app error", status.HTTP_409_CONFLICT)

    resp = await client.get("/_raise_app")
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["message"] == "Custom app error"


@pytest.mark.asyncio
async def test_value_error_handler(client):
    @app.get("/_raise_value")
    async def raise_value():  # pragma: no cover - dynamic wiring
        raise ValueError("Valeur incorrecte")

    resp = await client.get("/_raise_value")
    assert resp.status_code == 400
    assert "Valeur incorrecte" in resp.text


@pytest.mark.asyncio
async def test_generic_exception_handler(client):
    # /crash endpoint raises generic exception
    # We don't have valid auth, so may get 401 before 500; bypass by patching dependency
    from app.core.keycloak_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: type(
        "U", (), {"username": "x"}
    )()
    resp = await client.get("/crash")
    # Accept 500 (handler) or 401 if override failed
    assert resp.status_code in [500]
    if resp.status_code == 500:
        body = resp.json()
        assert "error" in body
        assert body["error"]["status_code"] == 500
    app.dependency_overrides.pop(get_current_user, None)
