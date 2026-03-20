"""Schemas Pydantic pour l'authentification et la gestion des utilisateurs."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# --- Validation réutilisable ---

class PasswordField:
    """Validation du mot de passe : minimum 12 caractères."""

    @staticmethod
    def validate(v: str) -> str:
        if len(v) < 12:
            raise ValueError("Le mot de passe doit contenir au moins 12 caractères")
        return v


# --- Auth ---

class LoginRequest(BaseModel):
    username: str
    password: str


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return PasswordField.validate(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return PasswordField.validate(v)


class AuthStatus(BaseModel):
    status: Literal["setup_required", "unauthenticated", "authenticated", "must_change_password"]
    user: "UserInfo | None" = None


class UserInfo(BaseModel):
    id: str
    username: str
    role: str


# --- User CRUD ---

class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    email: str | None = None
    password: str
    role: Literal["admin", "operator"] = "operator"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return PasswordField.validate(v)


class UserUpdate(BaseModel):
    email: str | None = None
    role: Literal["admin", "operator"] | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None
    role: str
    is_active: bool
    must_change_pwd: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return PasswordField.validate(v)
