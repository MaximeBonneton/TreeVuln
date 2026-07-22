"""Schemas Pydantic des SBOM (méta + composants)."""
from datetime import datetime

from pydantic import BaseModel, Field


class SbomComponentResponse(BaseModel):
    purl: str | None
    name: str
    version: str | None
    component_type: str | None

    model_config = {"from_attributes": True}


class SbomResponse(BaseModel):
    """Méta d'un SBOM importé (+ warnings du dernier parsing à l'upload)."""

    format: str
    spec_version: str
    filename: str | None
    component_count: int
    imported_at: datetime
    warnings: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SbomDetailResponse(SbomResponse):
    """Méta + page de composants."""

    components: list[SbomComponentResponse] = Field(default_factory=list)
    total_components: int = 0


class SbomSummaryItem(BaseModel):
    """Entrée du résumé SBOM d'un arbre (assets ayant un SBOM)."""

    asset_id: str
    format: str
    component_count: int
    imported_at: datetime
