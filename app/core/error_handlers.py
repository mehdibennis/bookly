import logging
import traceback
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.exceptions import ConflictException as DomainConflictException
from app.core.exceptions import NotFoundException as DomainNotFoundException
from app.core.logging_config import request_id_var

# Configuration du logger
logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException):
    """Handler pour toutes les exceptions métier de l'application."""
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
    """Handler pour les erreurs de validation Pydantic (422)."""
    # Extraire les erreurs de validation
    errors = exc.errors()

    # Construire un message lisible
    if len(errors) == 1:
        error = errors[0]
        if error["type"] == "missing":
            message = f"Le champ '{error['loc'][-1]}' est requis."
        elif error["type"] == "string_type":  # pragma: no cover - rarely hit exactly
            message = f"Le champ '{error['loc'][-1]}' doit être une chaîne de caractères."
        elif error["type"] == "int_parsing":
            message = f"Le champ '{error['loc'][-1]}' doit être un nombre entier."
        else:
            message = f"Erreur de validation sur le champ '{error['loc'][-1]}': {error['msg']}"
    else:
        message = f"Erreurs de validation sur {len(errors)} champ(s)."

    error_content = {
        "error": {
            "message": message,
            "status_code": 422,
            "path": str(request.url),
            "request_id": request_id_var.get(),
        }
    }

    # En mode debug, ajouter les détails de validation (en convertissant tout en JSON-serializable)
    if settings.DEBUG:  # pragma: no cover - debug-only payload
        # Nettoyer les erreurs pour les rendre JSON-serializable
        serializable_errors = []
        for error in errors:
            clean_error = {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "input": str(error.get("input")) if error.get("input") is not None else None,
            }
            # Ajouter ctx seulement si disponible et convertir les valeurs non-serializable
            if "ctx" in error and error["ctx"]:
                clean_error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
            serializable_errors.append(clean_error)

        error_content["error"]["validation_details"] = serializable_errors

    return JSONResponse(
        status_code=422,
        content=error_content,
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handler pour les erreurs de validation (ValueError)."""
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
    """Catch-all fallback pour éviter les stacktraces brutes en prod."""
    # Générer un ID unique pour tracer l'erreur
    error_id = str(uuid.uuid4())[:8]

    # Logger TOUT en backend (pour traçabilité)
    logger.error(
        f"Erreur interne [{error_id}] - {type(exc).__name__}: {str(exc)}\n"
        f"URL: {request.url}\n"
        f"Method: {request.method}\n"
        f"Traceback: {traceback.format_exc()}"
    )

    # Réponse client (sécurisée)
    error_content = {
        "error": {
            "message": "Erreur interne du serveur.",
            "status_code": 500,
            "path": str(request.url),
            "error_id": error_id,  # Pour corréler avec les logs
            "request_id": request_id_var.get(),
        }
    }

    # En mode debug, ajouter les détails pour le développement
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
                "message": str(exc) or "Ressource non trouvée.",
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
                "message": str(exc) or "Conflit : ressource déjà existante.",
                "status_code": 409,
                "path": str(request.url),
                "request_id": request_id_var.get(),
            }
        },
    )
