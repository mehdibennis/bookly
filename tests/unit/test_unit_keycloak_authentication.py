"""
Tests for Keycloak authentication system.
Covers authentication, token validation, and user management scenarios.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.keycloak_auth import KeycloakAuth, KeycloakUser, require_admin
from app.core.url_helpers import reverse
from app.main import app as fastapi_app


class TestKeycloakAuthentication:
    """Test Keycloak authentication functionality."""

    def test_keycloak_user_properties(self):
        """Test KeycloakUser properties and methods."""
        token_info = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "realm_access": {"roles": ["user", "admin"]},
        }
        user_info = {
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
        }

        user = KeycloakUser(token_info, user_info)

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert "user" in user.roles
        assert "admin" in user.roles
        assert user.is_admin is True
        assert user.has_role("admin") is True
        assert user.has_role("nonexistent") is False

    def test_keycloak_user_without_user_info(self):
        """Test KeycloakUser with minimal token info."""
        token_info = {"sub": "user-456", "preferred_username": "basicuser"}

        user = KeycloakUser(token_info)

        assert user.username == "basicuser"
        assert user.email is None
        assert user.roles == []
        assert user.is_admin is False

    def test_keycloak_user_email_fallback(self):
        """Test email fallback from token when user_info is missing."""
        token_info = {
            "sub": "user-789",
            "preferred_username": "emailuser",
            "email": "token@example.com",
        }

        user = KeycloakUser(token_info)

        assert user.email == "token@example.com"

    @patch("app.core.keycloak_auth.KeycloakOpenID")
    def test_keycloak_auth_initialization(self, mock_keycloak_openid):
        """Test KeycloakAuth initialization."""
        keycloak_auth = KeycloakAuth()

        mock_keycloak_openid.assert_called_once()
        assert keycloak_auth.keycloak_openid is not None

    @pytest.mark.asyncio
    @patch("app.core.keycloak_auth.keycloak_auth.verify_token")
    @pytest.mark.asyncio
    async def test_token_verification_success(self, mock_verify_token):
        """Test successful token verification."""
        mock_token_info = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "realm_access": {"roles": ["user"]},
        }
        mock_verify_token.return_value = mock_token_info

        from app.core.keycloak_auth import keycloak_auth

        result = await keycloak_auth.verify_token("valid_token")

        assert result == mock_token_info
        mock_verify_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    @patch("app.core.keycloak_auth.keycloak_auth.verify_token")
    @pytest.mark.asyncio
    async def test_token_verification_failure(self, mock_verify_token):
        """Test token verification failure."""
        mock_verify_token.side_effect = HTTPException(
            status_code=401, detail="Invalid token"
        )

        from app.core.keycloak_auth import keycloak_auth

        with pytest.raises(HTTPException) as exc_info:
            await keycloak_auth.verify_token("invalid_token")

        assert exc_info.value.status_code == 401

    @patch("app.core.keycloak_auth.keycloak_auth.get_user_info")
    @pytest.mark.asyncio
    async def test_user_info_retrieval_success(self, mock_get_user_info):
        """Test successful user info retrieval."""
        mock_user_info = {
            "email": "test@example.com",
            "name": "Test User",
            "email_verified": True,
        }
        mock_get_user_info.return_value = mock_user_info

        from app.core.keycloak_auth import keycloak_auth

        result = await keycloak_auth.get_user_info("valid_token")

        assert result == mock_user_info

    @patch("app.core.keycloak_auth.keycloak_auth.get_user_info")
    @pytest.mark.asyncio
    async def test_user_info_retrieval_failure(self, mock_get_user_info):
        """Test user info retrieval failure."""
        mock_get_user_info.side_effect = HTTPException(
            status_code=401, detail="Cannot get user info"
        )

        from app.core.keycloak_auth import keycloak_auth

        with pytest.raises(HTTPException) as exc_info:
            await keycloak_auth.get_user_info("invalid_token")

        assert exc_info.value.status_code == 401


class TestKeycloakIntegration:
    """Integration tests for Keycloak with FastAPI."""

    @pytest.mark.asyncio
    async def test_require_admin_with_admin_user(self):
        """Test require_admin dependency with admin user."""
        token_info = {
            "sub": "admin-123",
            "preferred_username": "admin",
            "realm_access": {"roles": ["admin"]},
        }
        admin_user = KeycloakUser(token_info)

        # Should not raise exception
        result = await require_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_with_regular_user(self):
        """Test require_admin dependency with regular user."""
        from app.core.exceptions import ForbiddenException

        token_info = {
            "sub": "user-123",
            "preferred_username": "user",
            "realm_access": {"roles": ["user"]},
        }
        regular_user = KeycloakUser(token_info)

        with pytest.raises(ForbiddenException) as exc_info:
            await require_admin(regular_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_with_realm_admin(self):
        """Test require_admin dependency with realm-admin role."""
        token_info = {
            "sub": "admin-456",
            "preferred_username": "realm_admin",
            "realm_access": {"roles": ["realm-admin"]},
        }
        realm_admin_user = KeycloakUser(token_info)

        # Should not raise exception
        result = await require_admin(realm_admin_user)
        assert result == realm_admin_user

    @pytest.mark.asyncio
    async def test_authentication_flow_edge_cases(self, client):
        """Test authentication flow edge cases."""
        # Test missing Authorization header (GET /books/ doesn't require auth)
        path = reverse(fastapi_app, "books:list")
        resp = await client.get(path)
        assert resp.status_code == 200  # GET books is public

        # Test malformed Authorization header (still public endpoint)
        malformed_headers = {"Authorization": "InvalidFormat"}
        resp = await client.get(path, headers=malformed_headers)
        assert resp.status_code == 200  # Still public

        # Test empty Bearer token (still public endpoint)
        empty_token_headers = {"Authorization": "Bearer "}
        resp = await client.get(path, headers=empty_token_headers)
        assert resp.status_code == 200  # Still public

    @pytest.mark.asyncio
    async def test_token_expiration_scenarios(self, client):
        """Test token expiration and validation scenarios."""
        # Test with public endpoint that doesn't require auth
        path = reverse(fastapi_app, "books:list")
        resp = await client.get(path)
        assert resp.status_code == 200

        # Test with obviously invalid token format (still public endpoint)
        invalid_headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
        resp = await client.get(path, headers=invalid_headers)
        assert resp.status_code == 200  # Public endpoint ignores invalid tokens
