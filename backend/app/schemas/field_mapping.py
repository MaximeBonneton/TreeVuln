"""Schemas for field mapping."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Supported field types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    ARRAY = "array"
    UNKNOWN = "unknown"


class FieldDefinition(BaseModel):
    """Definition of a field available for Input nodes."""

    name: str = Field(description="Technical field name (e.g. cvss_score)")
    label: str | None = Field(default=None, description="Display label (e.g. CVSS Score)")
    type: FieldType = Field(default=FieldType.UNKNOWN, description="Data type")
    description: str | None = Field(default=None, description="Field description")
    examples: list[Any] = Field(
        default_factory=list,
        max_length=5,
        description="Example values (max 5)",
    )
    required: bool = Field(default=False, description="Required field in vulnerabilities")


class FieldMapping(BaseModel):
    """Complete field mapping for a tree."""

    fields: list[FieldDefinition] = Field(default_factory=list)
    source: str | None = Field(
        default=None,
        description="Mapping origin: 'manual', 'import', 'scan:file.csv'",
    )
    version: int = Field(default=1, description="Version du mapping")


class FieldMappingUpdate(BaseModel):
    """Schema for updating the mapping."""

    fields: list[FieldDefinition]
    source: str | None = Field(default="manual")


class ScanResult(BaseModel):
    """Result of scanning a CSV/JSON file."""

    fields: list[FieldDefinition]
    rows_scanned: int = Field(description="Number of rows analyzed")
    source_type: str = Field(description="Type de fichier: 'csv' ou 'json'")
    warnings: list[str] = Field(default_factory=list, description="Any warnings")
