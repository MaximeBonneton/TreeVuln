"""Schemas pour le diagnostic d'arbre de decision."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.tree import TreeStructure


class DiagnosticItem(BaseModel):
    """Un probleme detecte dans l'arbre."""

    code: str
    message: str
    severity: Literal["error", "warning"]
    node_id: str | None = None
    edge_id: str | None = None


class DiagnosticResult(BaseModel):
    """Resultat complet du diagnostic."""

    errors: list[DiagnosticItem] = []
    warnings: list[DiagnosticItem] = []


class DiagnosticRequest(BaseModel):
    """Requete de diagnostic d'arbre."""

    structure: TreeStructure
