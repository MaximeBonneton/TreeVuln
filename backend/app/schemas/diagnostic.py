"""Schemas for decision tree diagnostics."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.tree import TreeStructure


class DiagnosticItem(BaseModel):
    """A problem detected in the tree."""

    code: str
    message: str
    severity: Literal["error", "warning"]
    node_id: str | None = None
    edge_id: str | None = None


class DiagnosticResult(BaseModel):
    """Complete diagnostic result."""

    errors: list[DiagnosticItem] = []
    warnings: list[DiagnosticItem] = []


class DiagnosticRequest(BaseModel):
    """Tree diagnostic request."""

    structure: TreeStructure
