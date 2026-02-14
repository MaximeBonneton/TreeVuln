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


class AssetImportError(BaseModel):
    """Détail d'une erreur d'import."""

    row: int = Field(description="Numéro de ligne dans le fichier")
    asset_id: str | None = Field(default=None, description="Asset ID si disponible")
    error: str = Field(description="Description de l'erreur")


class AssetColumnMapping(BaseModel):
    """Mapping des colonnes du fichier vers les champs asset."""

    asset_id: str = Field(description="Nom de la colonne pour asset_id")
    name: str | None = Field(default=None, description="Nom de la colonne pour name")
    criticality: str | None = Field(default=None, description="Nom de la colonne pour criticality")


class AssetImportResponse(BaseModel):
    """Réponse détaillée pour l'import fichier."""

    total_rows: int = Field(description="Nombre total de lignes lues")
    created: int = Field(description="Nombre d'assets créés")
    updated: int = Field(description="Nombre d'assets mis à jour")
    errors: int = Field(description="Nombre d'erreurs")
    error_details: list[AssetImportError] = Field(default_factory=list)
