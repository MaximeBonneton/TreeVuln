from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestEndpointCreate(BaseModel):
    """Schema for creating an ingestion endpoint."""

    name: str = Field(max_length=255, description="Endpoint name")
    slug: str = Field(max_length=100, description="Slug for the URL")
    field_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping source -> TreeVuln (ex: {'vuln_id': 'cve_id', 'score': 'cvss_score'})",
    )
    is_active: bool = Field(default=True)
    auto_evaluate: bool = Field(default=True, description="Automatically evaluate received vulnerabilities")


class IngestEndpointUpdate(BaseModel):
    """Schema for updating an ingestion endpoint."""

    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    field_mapping: dict[str, str] | None = None
    is_active: bool | None = None
    auto_evaluate: bool | None = None


class IngestEndpointResponse(BaseModel):
    """Response schema for an ingestion endpoint (API key not exposed)."""

    id: int
    tree_id: int
    name: str
    slug: str
    has_api_key: bool
    field_mapping: dict[str, str]
    is_active: bool
    auto_evaluate: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_endpoint(cls, endpoint: object) -> "IngestEndpointResponse":
        """Build the response indicating the presence of an API key."""
        api_key = getattr(endpoint, "api_key", None)
        return cls(
            id=endpoint.id,  # type: ignore[union-attr]
            tree_id=endpoint.tree_id,  # type: ignore[union-attr]
            name=endpoint.name,  # type: ignore[union-attr]
            slug=endpoint.slug,  # type: ignore[union-attr]
            has_api_key=bool(api_key),
            field_mapping=endpoint.field_mapping,  # type: ignore[union-attr]
            is_active=endpoint.is_active,  # type: ignore[union-attr]
            auto_evaluate=endpoint.auto_evaluate,  # type: ignore[union-attr]
            created_at=endpoint.created_at,  # type: ignore[union-attr]
            updated_at=endpoint.updated_at,  # type: ignore[union-attr]
        )


class IngestEndpointWithKeyResponse(BaseModel):
    """Response schema with full API key (creation/regeneration)."""

    id: int
    tree_id: int
    name: str
    slug: str
    api_key: str
    field_mapping: dict[str, str]
    is_active: bool
    auto_evaluate: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestLogResponse(BaseModel):
    """Response schema for an ingestion log."""

    id: int
    endpoint_id: int
    source_ip: str | None
    payload_size: int | None
    vuln_count: int
    success_count: int
    error_count: int
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestResult(BaseModel):
    """Result of an ingestion."""

    received: int = Field(description="Number of vulnerabilities received")
    evaluated: int = Field(description="Number of vulnerabilities evaluated")
    errors: int = Field(description="Number of errors")
    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Evaluation results (if auto_evaluate=true)",
    )
