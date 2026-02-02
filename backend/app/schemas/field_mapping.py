"""Schemas pour le mapping des champs."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Types de champs supportés."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    ARRAY = "array"
    UNKNOWN = "unknown"


class FieldDefinition(BaseModel):
    """Définition d'un champ disponible pour les nœuds Input."""

    name: str = Field(description="Nom technique du champ (ex: cvss_score)")
    label: str | None = Field(default=None, description="Label affiché (ex: Score CVSS)")
    type: FieldType = Field(default=FieldType.UNKNOWN, description="Type de données")
    description: str | None = Field(default=None, description="Description du champ")
    examples: list[Any] = Field(
        default_factory=list,
        max_length=5,
        description="Exemples de valeurs (max 5)",
    )
    required: bool = Field(default=False, description="Champ obligatoire dans les vulnérabilités")


class FieldMapping(BaseModel):
    """Mapping complet des champs pour un arbre."""

    fields: list[FieldDefinition] = Field(default_factory=list)
    source: str | None = Field(
        default=None,
        description="Origine du mapping: 'manual', 'import', 'scan:fichier.csv'",
    )
    version: int = Field(default=1, description="Version du mapping")


class FieldMappingUpdate(BaseModel):
    """Schéma pour la mise à jour du mapping."""

    fields: list[FieldDefinition]
    source: str | None = Field(default="manual")


class ScanResult(BaseModel):
    """Résultat du scan d'un fichier CSV/JSON."""

    fields: list[FieldDefinition]
    rows_scanned: int = Field(description="Nombre de lignes analysées")
    source_type: str = Field(description="Type de fichier: 'csv' ou 'json'")
    warnings: list[str] = Field(default_factory=list, description="Avertissements éventuels")
