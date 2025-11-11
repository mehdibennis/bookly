"""
Keycloak authentication module for FastAPI.
Handles token validation and user info extraction with proper signature verification.
"""

import logging
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from keycloak import KeycloakOpenID

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class KeycloakAuth:
    def __init__(self):
        # Initialize Keycloak OpenID client
        self.keycloak_openid = KeycloakOpenID(
            server_url=settings.KEYCLOAK_SERVER_URL,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            realm_name=settings.KEYCLOAK_REALM,
            client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
            verify=True,
        )
        self._public_key = None

    def get_public_key(self) -> str:
        """Get and cache the Keycloak public key for JWT verification."""
        if self._public_key is None:
            try:
                # Fetch the public key from Keycloak
                public_key = self.keycloak_openid.public_key()
                self._public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
                logger.info("Keycloak public key loaded successfully")
            except Exception as e:  # pragma: no cover - network/config env dependent
                logger.error(f"Failed to load Keycloak public key: {e}")
                raise
        return self._public_key

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify token with Keycloak public key and return user info."""
        try:
            # Get the public key from Keycloak
            public_key = self.get_public_key()

            # Decode and verify the token with signature verification
            token_info = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],  # Keycloak uses RS256 by default
                options={
                    "verify_signature": True,  # Verify signature in production
                    "verify_exp": True,  # Verify expiration
                    "verify_aud": False,  # Audience check disabled (can be enabled if needed)
                },
            )

            logger.info(
                f"Token verified successfully for user: {token_info.get('preferred_username')}"
            )
            return token_info

        except ExpiredSignatureError:
            logger.warning("Token has expired")
            raise UnauthorizedException("Le token a expiré")
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise UnauthorizedException("Token d'authentification invalide")
        except Exception as e:  # pragma: no cover - catch-all safety
            logger.error(f"Unexpected error during token validation: {e}")
            raise UnauthorizedException("Erreur lors de la validation du token")

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """Get user info from Keycloak using the token."""
        try:
            user_info = self.keycloak_openid.userinfo(token)
            return user_info
        except Exception as e:  # pragma: no cover - external dependency failure
            logger.warning(f"Failed to get user info: {e}")
            raise UnauthorizedException(
                "Impossible de récupérer les informations utilisateur"
            )


# Global instance
keycloak_auth = KeycloakAuth()


class KeycloakUser:
    """User information from Keycloak token."""

    def __init__(
        self,
        token_info: dict[str, Any],
        user_info: dict[str, Any] | None = None,
        raw_token: str | None = None,
    ):
        self.token_info = token_info
        self.user_info = user_info or {}
        # Conserver le token brut pour des appels privilégiés (ex: API admin Keycloak)
        self._raw_token = raw_token

    @property
    def username(self) -> str:
        return self.token_info.get("preferred_username", "unknown")

    @property
    def email(self) -> str | None:
        return self.user_info.get("email") or self.token_info.get("email")

    @property
    def roles(self) -> list:
        """Extract roles from token."""
        realm_access = self.token_info.get("realm_access", {})
        return realm_access.get("roles", [])

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles or "realm-admin" in self.roles

    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def client_roles(self, client: str) -> list:
        ra = self.token_info.get("resource_access", {}) or {}
        return (ra.get(client, {}) or {}).get("roles", []) or []

    def has_client_role(self, client: str, role: str) -> bool:
        return role in self.client_roles(client)

    @property
    def realm_management_roles(self) -> list:
        return self.client_roles("realm-management")

    @property
    def raw_token(self) -> str | None:
        return self._raw_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> KeycloakUser:
    """FastAPI dependency to get current authenticated user from Keycloak."""
    token = credentials.credentials

    # Verify token and get user info
    token_info = await keycloak_auth.verify_token(token)

    # Optionally get additional user info
    try:
        user_info = await keycloak_auth.get_user_info(token)
    except UnauthorizedException:
        user_info = None

    return KeycloakUser(token_info, user_info, raw_token=token)


async def require_admin(user: KeycloakUser = Depends(get_current_user)) -> KeycloakUser:
    """FastAPI dependency that requires admin role."""
    if not user.is_admin:
        raise ForbiddenException("Accès administrateur requis")
    return user
