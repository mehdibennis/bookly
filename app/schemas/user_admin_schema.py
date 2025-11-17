from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserAdminBase(BaseModel):
    email: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    enabled: bool | None = True
    attributes: dict[str, Any] | None = None


class UserAdminCreate(UserAdminBase):
    username: str
    password: str | None = None
    temporary_password: bool = Field(default=False, alias="temporaryPassword")


class UserAdminUpdate(UserAdminBase):
    pass


class UserPasswordUpdate(BaseModel):
    password: str
    temporary: bool = False
