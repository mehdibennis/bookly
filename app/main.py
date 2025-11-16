from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import Response

from app.api.v1.routes import admin_users as users
from app.api.v1.routes import authors, books
from app.core import config
from app.core.error_handlers import (
    app_exception_handler,
    domain_conflict_handler,
    domain_not_found_handler,
    generic_exception_handler,
    validation_exception_handler,
    value_error_handler,
)
from app.core.exceptions import AppException
from app.core.keycloak_auth import get_current_user, require_admin
from app.core.logging_config import setup_logging
from app.core.middleware import AccessLogMiddleware, RequestIdMiddleware
from app.core.observability import setup_prometheus, setup_tracing
from app.core.sentry_integration import setup_sentry
from app.domain.exceptions import ConflictException as DomainConflictException
from app.domain.exceptions import NotFoundException as DomainNotFoundException

# Centralized logging configuration
setup_logging(
    level=config.settings.LOG_LEVEL,
    to_file=config.settings.LOG_TO_FILE,
    filename=config.settings.LOG_FILE,
    json_logs=config.settings.LOG_JSON,
)

app = FastAPI(
    title="Bookly API",
    version="1.0.0",
    description="""
    **Bookly** is a Rest API is a modern REST API for book management with Keycloak authentication.

    ## Main Features

    * **Secure Authentication**: Keycloak integration for JWT and role management
    * **Full CRUD**: Create, read, update, and delete books
    * **Intelligent Pagination**: Efficient navigation through collections
    * **Redis Cache**: Optimized performance for paginated lists
    * **Rate Limiting**: Protection against abuse (SlowAPI)
    * **Robust Validation**: Pydantic for data validation
    * **Centralized Error Handling**: Custom handlers for all exceptions

    ## Architecture

    * **Domain-Driven Design** : Clear separation between domain, services, repositories
    * **Unit of Work Pattern** : Consistent transactional management
    * **Async/Await** : Maximum performance with async SQLAlchemy
    * **Comprehensive Tests** : 98% code coverage

    ## Quick Start
    1. Obtain a JWT token from your Keycloak server
    2. Use the token in the `Authorization: Bearer <token>` header
    3. Explore the book management endpoints under `/api/v1/books/` and author endpoints under `/api/v1/authors/`
    """,
    contact={"name": "Bookly Team", "email": "support@bookly.example.com"},
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {
            "name": "books",
            "description": "Full management of books (CRUD, pagination, search)",
        },
        {
            "name": "authors",
            "description": "Full management of authors (CRUD, pagination)",
        },
        {
            "name": "System",
            "description": "System endpoints (healthcheck, monitoring)",
        },
    ],
)


# ExaExample of using pyinstrument to profile the app
# To profile, run locally:
#   pyinstrument -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# An HTML or text report will be generated at the end of the run


def rate_limit_key(request: Request) -> str:
    if config.settings.TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    # Fallback to SlowAPI helper (client host)
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
# Throttling
app.state.limiter = limiter
HandlerType = Callable[[Request, Exception], Response | Awaitable[Response]]
app.add_exception_handler(
    RateLimitExceeded, cast(HandlerType, _rate_limit_exceeded_handler)
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIdMiddleware)
if config.settings.LOG_ACCESS:
    app.add_middleware(AccessLogMiddleware)

app.include_router(books.router, prefix="/api/v1", tags=["books"])
app.include_router(authors.router, prefix="/api/v1", tags=["authors"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])

# Observability (optional)
setup_prometheus(
    app,
    enabled=config.settings.ENABLE_METRICS,
    endpoint=config.settings.METRICS_ENDPOINT,
)
setup_tracing(
    app,
    enabled=config.settings.ENABLE_TRACING,
    service_name=config.settings.OTEL_SERVICE_NAME,
    otlp_endpoint=config.settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)

# Sentry (optional)
setup_sentry(
    enabled=config.settings.ENABLE_SENTRY,
    dsn=config.settings.SENTRY_DSN,
    environment=config.settings.SENTRY_ENVIRONMENT,
    traces_sample_rate=config.settings.SENTRY_TRACES_SAMPLE_RATE,
    profiles_sample_rate=config.settings.SENTRY_PROFILES_SAMPLE_RATE,
)

# Global Handlers for consistent error management
app.add_exception_handler(
    RequestValidationError, cast(HandlerType, validation_exception_handler)
)  # 422
app.add_exception_handler(
    AppException, cast(HandlerType, app_exception_handler)
)  # 409, 404
app.add_exception_handler(
    DomainNotFoundException, cast(HandlerType, domain_not_found_handler)
)
app.add_exception_handler(
    DomainConflictException, cast(HandlerType, domain_conflict_handler)
)
app.add_exception_handler(ValueError, cast(HandlerType, value_error_handler))  # 400
app.add_exception_handler(Exception, generic_exception_handler)  # 500

try:
    ExceptionGroup
except NameError:  # pragma: no cover - Python <3.11 fallback

    class ExceptionGroup(Exception):
        pass


app.add_exception_handler(
    ExceptionGroup,
    generic_exception_handler,  # pragma: no cover requires-python = ">= 3.11"
)  # 500 (grouped)


@app.get("/ping", tags=["System"])
@limiter.limit("30/minute")  # 30 requests per minute per IP
def ping(request: Request, user=Depends(require_admin)):
    """Protected endpoint - requires admin role for testing authentication."""
    return {"message": "pong", "user": user.username, "roles": user.roles}


# Test endpoint for the generic exception handler (protected by JWT)
@app.get("/crash")
async def crash(user=Depends(get_current_user)):
    raise Exception("boom")


# --- Root endpoint ---
@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to the bookly API!",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


# --- Healthcheck ---
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}


# --- Entrypoint (for local runs) ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.settings.APP_HOST,
        port=config.settings.APP_PORT,
        reload=config.settings.DEBUG,
    )
