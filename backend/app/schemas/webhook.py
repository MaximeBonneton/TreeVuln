import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.url_validation import validate_webhook_url

VALID_EVENTS = {"on_act", "on_attend", "on_track_star", "on_track", "on_batch_complete", "*"}

# Forbidden headers: cannot be overridden by custom user headers
_FORBIDDEN_HEADERS = {
    "host", "content-length", "transfer-encoding",
    "content-type", "x-treevuln-event", "x-treevuln-signature",
}
_HEADER_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*$")


def _validate_webhook_headers(headers: dict[str, str]) -> dict[str, str]:
    """Validate custom webhook headers (CRLF injection protection + header override)."""
    for name, value in headers.items():
        if name.lower() in _FORBIDDEN_HEADERS:
            raise ValueError(f"Header '{name}' cannot be overridden")
        if not _HEADER_NAME_RE.match(name):
            raise ValueError(f"Header name '{name}' contains invalid characters")
        if "\r" in value or "\n" in value or "\r" in name or "\n" in name:
            raise ValueError(f"Header '{name}' contains forbidden CRLF characters")
    return headers


class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""

    name: str = Field(max_length=255, description="Webhook name")
    url: str = Field(max_length=2048, description="Destination URL")
    secret: str | None = Field(default=None, max_length=255, description="Secret pour signature HMAC")
    headers: dict[str, str] = Field(default_factory=dict, description="Headers HTTP custom")
    events: list[str] = Field(
        description="Trigger events (on_act, on_attend, on_track_star, on_track, on_batch_complete, *)",
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
            raise ValueError("At least one event required")
        invalid = set(v) - VALID_EVENTS
        if invalid:
            raise ValueError(f"Invalid events: {invalid}. Valid: {VALID_EVENTS}")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str]) -> dict[str, str]:
        return _validate_webhook_headers(v)


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""

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
                raise ValueError(f"Invalid events: {invalid}. Valid: {VALID_EVENTS}")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is not None:
            return _validate_webhook_headers(v)
        return v


class WebhookResponse(BaseModel):
    """Response schema for a webhook. The secret is never exposed."""

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
    """Response schema for a webhook log."""

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
    """Result of a webhook test."""

    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
