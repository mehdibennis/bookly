import pytest
from fastapi import HTTPException

from app.api.v1.routes import admin_users
from app.core import config


def make_user(has_roles=False, raw_token=None):
    class U:
        def __init__(self, has_roles, raw_token):
            self.username = "bob"
            self.raw_token = raw_token

        def has_client_role(self, client, role):
            return has_roles

    return U(has_roles, raw_token)


def test_get_admin_client_prefers_service_account(monkeypatch):
    # When KEYCLOAK_CLIENT_SECRET is set, service account path is taken
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_SECRET", "secret")
    user = make_user(has_roles=False)
    kc = admin_users.get_admin_client(user)
    assert kc is not None
    # restore secret
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_SECRET", "")


def test_require_realm_mgmt_raises_for_missing_roles(monkeypatch):
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_SECRET", "")
    user = make_user(has_roles=False)
    with pytest.raises(HTTPException):
        admin_users.require_realm_mgmt(user)
