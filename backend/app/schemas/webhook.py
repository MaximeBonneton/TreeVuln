import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.url_validation import validate_webhook_url

VALID_EVENTS = {"on_act", "on_attend", "on_track_star", "on_track", "on_batch_complete", "*"}

# Headers interdits : ne peuvent pas être surchargés par les headers custom utilisateur
_FORBIDDEN_HEADERS = {
    "host", "content-length", "transfer-encoding",
    "content-type", "x-treevuln-event", "x-treevuln-signature",
}
_HEADER_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*$")


def _validate_webhook_headers(headers: dict[str, str]) -> dict[str, str]:
    """Valide les headers custom d'un webhook (protection CRLF injection + header override)."""
    for name, value in headers.items():
        if name.lower() in _FORBIDDEN_HEADERS:
            raise ValueError(f"Le header '{name}' ne peut pas être surchargé")
        if not _HEADER_NAME_RE.match(name):
            raise ValueError(f"Le nom de header '{name}' contient des caractères invalides")
        if "\r" in value or "\n" in value or "\r" in name or "\n" in name:
            raise ValueError(f"Le header '{name}' contient des caractères CRLF interdits")
    return headers


class WebhookCreate(BaseModel):
    """Schéma pour la création d'un webhook."""

    name: str = Field(max_length=255, description="Nom du webhook")
    url: str = Field(max_length=2048, description="URL de destination")
    secret: str | None = Field(default=None, max_length=255, description="Secret pour signature HMAC")
    headers: dict[str, str] = Field(default_factory=dict, description="Headers HTTP custom")
    events: list[str] = Field(
        description="Événements déclencheurs (on_act, on_attend, on_track_star, on_track, on_batch_complete, *)",
    )
    is_active: bool = Field(default=True)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_webhook_url(v)

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Au moins un événement requis")
        invalid = set(v) - VALID_EVENTS
        if invalid:
            raise ValueError(f"Événements invalides : {invalid}. Valides : {VALID_EVENTS}")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        return _validate_webhook_headers(v)


class WebhookUpdate(BaseModel):
    """Schéma pour la mise à jour d'un webhook."""

    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    secret: str | None = None
    headers: dict[str, str] | None = None
    events: list[str] | None = None
    is_active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_webhook_url(v)
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            invalid = set(v) - VALID_EVENTS
            if invalid:
                raise ValueError(f"Événements invalides : {invalid}. Valides : {VALID_EVENTS}")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is not None:
            return _validate_webhook_headers(v)
        return v


class WebhookResponse(BaseModel):
    """Schéma de réponse pour un webhook. Le secret n'est jamais exposé."""

    id: int
    tree_id: int
    name: str
    url: str
    has_secret: bool
    headers: dict[str, str]
    events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookLogResponse(BaseModel):
    """Schéma de réponse pour un log de webhook."""

    id: int
    webhook_id: int
    event: str
    status_code: int | None
    request_body: dict[str, Any]
    response_body: str | None
    success: bool
    error_message: str | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestResult(BaseModel):
    """Résultat d'un test de webhook."""

    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
