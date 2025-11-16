from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.keycloak_auth import get_current_user, require_admin
from app.core.limiter import limiter

system_router = APIRouter()


@system_router.get("/ping", tags=["System"])
@limiter.limit("30/minute")  # 30 requests per minute per IP
def ping(request: Request, user: Any = Depends(require_admin)):
    """Protected endpoint - requires admin role for testing authentication."""
    return {"message": "pong", "user": user.username, "roles": user.roles}


@system_router.get("/crash")
async def crash(user: Any = Depends(get_current_user)):
    raise Exception("boom")


# --- Root endpoint ---
@system_router.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to the bookly API!",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


# --- Healthcheck ---
@system_router.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}
