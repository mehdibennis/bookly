import logging
import traceback
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_config import request_id_var
from app.domain.exceptions import ConflictException as DomainConflictException
from app.domain.exceptions import NotFoundException as DomainNotFoundException

# Logger configuration
logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException):
    """Handler for all business exceptions in the application."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "status_code": exc.status_code,
                "path": str(request.url),
                "request_id": request_id_var.get(),
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for Pydantic validation errors (422)."""
    # Extract validation errors
    errors = exc.errors()

    # Build a readable message
    if len(errors) == 1:
        error = errors[0]
        if error["type"] == "missing":
            message = f"The field '{error['loc'][-1]}' is required."
        elif error["type"] == "string_type":  # pragma: no cover - rarely hit exactly
            message = f"The field '{error['loc'][-1]}' must be a string."
        elif error["type"] == "int_parsing":
            message = f"The field '{error['loc'][-1]}' must be an integer."
        else:
            message = f"Validation error on field '{error['loc'][-1]}': {error['msg']}"
    else:
        message = f"Validation errors on {len(errors)} field(s)."

    error_content = {
        "error": {
            "message": message,
            "status_code": 422,
            "path": str(request.url),
            "request_id": request_id_var.get(),
        }
    }

    # In debug mode, add validation details (converting everything to JSON-serializable)
    if settings.DEBUG:  # pragma: no cover - debug-only payload
        # Clean errors to make them JSON-serializable
        serializable_errors = []
        for error in errors:
            clean_error = {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "input": (
                    str(error.get("input")) if error.get("input") is not None else None
                ),
            }
            # Add ctx only if available and convert non-serializable values
            if "ctx" in error and error["ctx"]:
                clean_error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
            serializable_errors.append(clean_error)

        error_content["error"]["validation_details"] = serializable_errors

    return JSONResponse(
        status_code=422,
        content=error_content,
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handler for validation errors (ValueError)."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "message": str(exc),
                "status_code": 400,
                "path": str(request.url),
                "request_id": request_id_var.get(),
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all fallback to avoid raw stack traces in production."""
    # Generate a unique ID to trace the error
    error_id = str(uuid.uuid4())[:8]

    # Log EVERYTHING on the backend (for traceability)
    logger.error(
        f"Internal error [{error_id}] - {type(exc).__name__}: {str(exc)}\n"
        f"URL: {request.url}\n"
        f"Method: {request.method}\n"
        f"Traceback: {traceback.format_exc()}"
    )

    # Réponse client (sécurisée)
    error_content = {
        "error": {
            "message": "Internal server error.",
            "status_code": 500,
            "path": str(request.url),
            "error_id": error_id,  # To correlate with logs
            "request_id": request_id_var.get(),
        }
    }

    # In debug mode, add details for development
    if settings.DEBUG:  # pragma: no cover - debug-only payload
        error_content["error"]["debug_details"] = str(exc)
        error_content["error"]["traceback"] = traceback.format_exc()

    return JSONResponse(
        status_code=500,
        content=error_content,
    )


async def domain_not_found_handler(request: Request, exc: DomainNotFoundException):
    """Map domain NotFoundException to an HTTP 404 response."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "message": str(exc) or "Resource not found.",
                "status_code": 404,
                "path": str(request.url),
                "request_id": request_id_var.get(),
            }
        },
    )


async def domain_conflict_handler(request: Request, exc: DomainConflictException):
    """Map domain ConflictException to an HTTP 409 response."""
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "message": str(exc) or "Conflict: resource already exists.",
                "status_code": 409,
                "path": str(request.url),
                "request_id": request_id_var.get(),
            }
        },
    )
