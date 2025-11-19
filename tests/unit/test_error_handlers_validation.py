import json

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.core.error_handlers import validation_exception_handler


@pytest.mark.asyncio
async def test_validation_exception_handler_string_type_branch(monkeypatch):
    # Force DEBUG to include validation_details path (also covers that block)
    monkeypatch.setattr("app.core.config.settings.DEBUG", True)

    # Build a minimal ASGI scope for Request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/books",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "query_string": b"",
    }
    req = Request(scope)

    # Create a RequestValidationError that hits the 'string_type' branch
    errors = [
        {
            "loc": ("body", "title"),
            "type": "string_type",
            "msg": "Input should be a valid string",
            "input": 123,
        }
    ]
    exc = RequestValidationError(errors)

    resp = await validation_exception_handler(req, exc)
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert "The field" in body["error"]["message"]
    # And debug validation details were attached
    assert "validation_details" in body["error"]


@pytest.mark.asyncio
async def test_validation_exception_handler_int_type_branch(monkeypatch):
    # Force DEBUG to include validation_details path (also covers that block)
    monkeypatch.setattr("app.core.config.settings.DEBUG", True)

    # Build a minimal ASGI scope for Request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/books",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "query_string": b"",
    }
    req = Request(scope)

    # Create a RequestValidationError that hits the 'int_parsing' branch
    errors = [
        {
            "loc": ("body", "title"),
            "type": "int_parsing",
            "msg": "Input should be a valid integer",
            "input": 123,
        }
    ]
    exc = RequestValidationError(errors)

    resp = await validation_exception_handler(req, exc)
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert "The field" in body["error"]["message"]
    # And debug validation details were attached
    assert "validation_details" in body["error"]


@pytest.mark.asyncio
async def test_validation_exception_handler_other_type_branch(monkeypatch):
    # Force DEBUG to include validation_details path (also covers that block)
    monkeypatch.setattr("app.core.config.settings.DEBUG", True)

    # Build a minimal ASGI scope for Request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/books",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "query_string": b"",
    }
    req = Request(scope)

    # Create a RequestValidationError that hits an 'other' branch
    errors = [
        {
            "loc": ("body", "title"),
            "type": "value_error",
            "msg": "Some other validation error",
            "input": "invalid",
        }
    ]
    exc = RequestValidationError(errors)

    resp = await validation_exception_handler(req, exc)
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert "Validation error on field" in body["error"]["message"]
    # And debug validation details were attached
    assert "validation_details" in body["error"]
