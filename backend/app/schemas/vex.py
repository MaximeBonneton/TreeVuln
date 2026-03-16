"""Schemas pour la génération de documents VEX (CycloneDX 1.6)."""

from typing import Any

from pydantic import BaseModel, Field


class VexRequest(BaseModel):
    """Requête de génération VEX."""

    product_name: str = Field(description="Nom du produit/application")
    product_version: str = Field(
        default="unspecified", description="Version du produit"
    )
    vulnerabilities: list[dict[str, Any]] = Field(
        description="Liste des vulnérabilités (même format que /evaluate)"
    )


class VexGenerationResult(BaseModel):
    """Réponse de génération VEX."""

    document: dict = Field(description="Document CycloneDX VEX complet")
    total_evaluated: int = Field(description="Nombre total de vulns évaluées")
    included_in_vex: int = Field(description="Vulns incluses dans le VEX")
    excluded: int = Field(
        description="Vulns exclues (pas de vex_status ou erreur)"
    )
    warnings: list[str] = Field(default_factory=list)
