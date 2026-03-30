from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class DecisionPath(BaseModel):
    """
    Represents a step in the decision path (audit trail).
    """

    node_id: str = Field(description="ID of the traversed node")
    node_label: str = Field(description="Node label for readability")
    node_type: str = Field(description="Node type (input, logic, output)")
    field_evaluated: str | None = Field(
        default=None,
        description="Field evaluated (for input/logic nodes)",
    )
    value_found: Any = Field(default=None, description="Value found during evaluation")
    condition_matched: str | None = Field(
        default=None,
        description="Label of the matched condition",
    )


class EvaluationResult(BaseModel):
    """
    Evaluation result for a single vulnerability.
    """

    vuln_id: str | None = Field(description="ID of the evaluated vulnerability")
    decision: str = Field(description="Final decision (Act, Attend, Track, Track*)")
    decision_color: str | None = Field(default=None, description="Color associated with the decision")
    path: list[DecisionPath] = Field(
        default_factory=list,
        description="Complete decision path (audit trail)",
    )
    error: str | None = Field(default=None, description="Error if evaluation failed")


class SingleEvaluationRequest(BaseModel):
    """
    Request to evaluate a single vulnerability (real-time).
    """

    vulnerability: VulnerabilityInput
    include_path: bool = Field(
        default=True,
        description="Include the decision path in the response",
    )


class EvaluationRequest(BaseModel):
    """
    Request to evaluate a batch of vulnerabilities.
    """

    vulnerabilities: list[VulnerabilityInput] = Field(
        description="List of vulnerabilities to evaluate",
    )
    include_path: bool = Field(
        default=True,
        description="Include the decision path for each vuln",
    )


class EvaluationResponse(BaseModel):
    """
    Batch evaluation response.
    """

    total: int = Field(description="Total number of vulnerabilities processed")
    success_count: int = Field(description="Number of successful evaluations")
    error_count: int = Field(description="Number of errors")
    results: list[EvaluationResult] = Field(description="Detailed results")

    # Aggregated statistics
    decision_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count by decision (e.g. {'Act': 5, 'Track': 10})",
    )


class PreviewEvaluationRequest(BaseModel):
    """Requete d'evaluation preview (arbre non sauvegarde)."""

    structure: TreeStructure
    vulnerability: VulnerabilityInput
    tree_id: int | None = None
    include_path: bool = True


class ExportRequest(EvaluationRequest):
    """Request to evaluate and export a batch."""

    format: Literal["csv", "json"] = Field(
        default="csv",
        description="Export format: csv or json",
    )
