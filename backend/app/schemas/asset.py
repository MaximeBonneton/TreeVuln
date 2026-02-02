from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """Champs communs pour les assets."""

    asset_id: str = Field(max_length=255, description="Identifiant unique de l'asset")
    name: str | None = Field(default=None, max_length=255)
    criticality: str = Field(
        default="Medium",
        max_length=50,
        description="Criticité: Low, Medium, High, Critical",
    )
    tags: dict[str, Any] = Field(default_factory=dict)
    extra_data: dict[str, Any] = Field(default_factory=dict)


class AssetCreate(AssetBase):
    """Schéma pour la création d'un asset."""

    tree_id: int | None = Field(
        default=None,
        description="ID de l'arbre propriétaire. Si non fourni, utilise l'arbre par défaut.",
    )


class AssetUpdate(BaseModel):
    """Schéma pour la mise à jour d'un asset."""

    name: str | None = Field(default=None, max_length=255)
    criticality: str | None = Field(default=None, max_length=50)
    tags: dict[str, Any] | None = None
    extra_data: dict[str, Any] | None = None


class AssetResponse(AssetBase):
    """Schéma de réponse pour un asset."""

    id: int
    tree_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetBulkCreate(BaseModel):
    """Schéma pour l'import bulk d'assets."""

    tree_id: int | None = Field(
        default=None,
        description="ID de l'arbre propriétaire. Si non fourni, utilise l'arbre par défaut.",
    )
    assets: list[AssetCreate]


class AssetBulkResponse(BaseModel):
    """Réponse pour l'import bulk."""

    created: int
    updated: int
    errors: list[str] = Field(default_factory=list)
