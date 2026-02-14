from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WebhookCreate(BaseModel):
    """Schéma pour la création d'un webhook."""

    name: str = Field(max_length=255, description="Nom du webhook")
    url: str = Field(max_length=2048, description="URL de destination")
    secret: str | None = Field(default=None, max_length=255, description="Secret pour signature HMAC")
    headers: dict[str, str] = Field(default_factory=dict, description="Headers HTTP custom")
    events: list[str] = Field(
        description="Événements déclencheurs (on_act, on_attend, on_track_star, on_track, on_batch_complete)",
    )
    is_active: bool = Field(default=True)


class WebhookUpdate(BaseModel):
    """Schéma pour la mise à jour d'un webhook."""

    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    secret: str | None = None
    headers: dict[str, str] | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    """Schéma de réponse pour un webhook."""

    id: int
    tree_id: int
    name: str
    url: str
    secret: str | None
    headers: dict[str, str]
    events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
