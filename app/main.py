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
from app.core.exceptions import ConflictException as DomainConflictException
from app.core.exceptions import NotFoundException as DomainNotFoundException
from app.core.keycloak_auth import get_current_user, require_admin
from app.core.logging_config import setup_logging
from app.core.middleware import AccessLogMiddleware, RequestIdMiddleware
from app.core.observability import setup_prometheus, setup_tracing
from app.core.sentry_integration import setup_sentry

# Configuration du logging centralisée
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
    **Bookly** est une API REST moderne pour la gestion de livres avec authentification Keycloak.
    
    ## Fonctionnalités principales
    
    * **Authentification sécurisée** : Intégration Keycloak pour JWT et gestion des rôles
    * **CRUD complet** : Création, lecture, mise à jour et suppression de livres
    * **Pagination intelligente** : Navigation efficace dans les collections
    * **Cache Redis** : Performance optimisée pour les listes paginées
    * **Rate limiting** : Protection contre les abus (SlowAPI)
    * **Validation robuste** : Pydantic pour la validation des données
    * **Gestion d'erreurs centralisée** : Handlers personnalisés pour toutes les exceptions
    
    ## Architecture
    
    * **Domain-Driven Design** : Séparation claire entre domaine, services, repositories
    * **Unit of Work Pattern** : Gestion transactionnelle cohérente
    * **Async/Await** : Performance maximale avec SQLAlchemy async
    * **Tests exhaustifs** : 99% de couverture de code
    
    ## Démarrage rapide
    
    1. Obtenez un token JWT depuis votre serveur Keycloak
    2. Utilisez le token dans le header `Authorization: Bearer <token>`
    3. Explorez les endpoints de gestion des livres sous `/api/v1/books/` et auteurs sous `/api/v1/authors/`
    """,
    contact={"name": "Équipe Bookly", "email": "support@bookly.example.com"},
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {
            "name": "books",
            "description": "Gestion complète des livres (CRUD, pagination, recherche)",
        },
        {
            "name": "authors",
            "description": "Gestion des auteurs (CRUD, pagination)",
        },
        {
            "name": "System",
            "description": "Endpoints système (healthcheck, monitoring)",
        },
    ],
)


# Exemple d'utilisation de pyinstrument pour profiler l'app
# Pour profiler, lance en local :
#   pyinstrument -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Un rapport HTML ou texte sera généré à la fin de l'exécution


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
app.add_exception_handler(RateLimitExceeded, cast(HandlerType, _rate_limit_exceeded_handler))
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIdMiddleware)
if config.settings.LOG_ACCESS:
    app.add_middleware(AccessLogMiddleware)

app.include_router(books.router, prefix="/api/v1", tags=["books"])
app.include_router(authors.router, prefix="/api/v1", tags=["authors"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])

# Observability (optional)
setup_prometheus(app, enabled=config.settings.ENABLE_METRICS, endpoint=config.settings.METRICS_ENDPOINT)
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

# Handlers globaux pour une gestion d'erreurs cohérente
app.add_exception_handler(RequestValidationError, cast(HandlerType, validation_exception_handler))  # 422
app.add_exception_handler(AppException, cast(HandlerType, app_exception_handler))  # 409, 404
app.add_exception_handler(DomainNotFoundException, cast(HandlerType, domain_not_found_handler))
app.add_exception_handler(DomainConflictException, cast(HandlerType, domain_conflict_handler))
app.add_exception_handler(ValueError, cast(HandlerType, value_error_handler))  # 400
app.add_exception_handler(Exception, generic_exception_handler)  # 500

# Python 3.11 ExceptionGroup can bypass standard Exception handlers through middlewares
try:
    ExceptionGroup
except NameError:  # pragma: no cover - Python <3.11 fallback

    class ExceptionGroup(Exception):
        pass


app.add_exception_handler(ExceptionGroup, generic_exception_handler)  # 500 (grouped)


@app.get("/ping", tags=["System"])
@limiter.limit("30/minute")  # 30 requêtes par minute par IP
def ping(request: Request, user=Depends(require_admin)):
    """Protected endpoint - requires admin role for testing authentication."""
    return {"message": "pong", "user": user.username, "roles": user.roles}


# Endpoint de test pour le handler d'exception générique (protégé par JWT)
@app.get("/crash")
async def crash(user=Depends(get_current_user)):
    raise Exception("boom")


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
