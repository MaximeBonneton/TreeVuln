from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """Common fields for assets."""

    asset_id: str = Field(max_length=255, description="Unique asset identifier")
    name: str | None = Field(default=None, max_length=255)
    criticality: str = Field(
        default="Medium",
        max_length=50,
        description="Criticality: Low, Medium, High, Critical",
    )
    tags: dict[str, Any] = Field(default_factory=dict)
    extra_data: dict[str, Any] = Field(default_factory=dict)


class AssetCreate(AssetBase):
    """Schema for creating an asset."""

    tree_id: int | None = Field(
        default=None,
        description="Owner tree ID. If not provided, uses the default tree.",
    )


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    name: str | None = Field(default=None, max_length=255)
    criticality: str | None = Field(default=None, max_length=50)
    tags: dict[str, Any] | None = None
    extra_data: dict[str, Any] | None = None


class AssetResponse(AssetBase):
    """Response schema for an asset."""

    id: int
    tree_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetBulkCreate(BaseModel):
    """Schema for bulk asset import."""

    tree_id: int | None = Field(
        default=None,
        description="Owner tree ID. If not provided, uses the default tree.",
    )
    assets: list[AssetCreate]


class AssetBulkResponse(BaseModel):
    """Response for bulk import."""

    created: int
    updated: int
    errors: list[str] = Field(default_factory=list)


class AssetImportError(BaseModel):
    """Import error detail."""

    row: int = Field(description="Row number in the file")
    asset_id: str | None = Field(default=None, description="Asset ID si disponible")
    error: str = Field(description="Error description")


class AssetColumnMapping(BaseModel):
    """Mapping of file columns to asset fields."""

    asset_id: str = Field(description="Column name for asset_id")
    name: str | None = Field(default=None, description="Column name for name")
    criticality: str | None = Field(default=None, description="Column name for criticality")


class AssetImportResponse(BaseModel):
    """Detailed response for file import."""

    total_rows: int = Field(description="Total number of rows read")
    created: int = Field(description="Number of assets created")
    updated: int = Field(description="Number of assets updated")
    errors: int = Field(description="Number of errors")
    error_details: list[AssetImportError] = Field(default_factory=list)
