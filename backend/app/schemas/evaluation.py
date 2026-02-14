from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.vulnerability import VulnerabilityInput


class DecisionPath(BaseModel):
    """
    Représente une étape dans le chemin de décision (audit trail).
    """

    node_id: str = Field(description="ID du nœud traversé")
    node_label: str = Field(description="Label du nœud pour lisibilité")
    node_type: str = Field(description="Type de nœud (input, logic, output)")
    field_evaluated: str | None = Field(
        default=None,
        description="Champ évalué (pour nœuds input/logic)",
    )
    value_found: Any = Field(default=None, description="Valeur trouvée lors de l'évaluation")
    condition_matched: str | None = Field(
        default=None,
        description="Label de la condition qui a matché",
    )


class EvaluationResult(BaseModel):
    """
    Résultat d'évaluation pour une vulnérabilité unique.
    """

    vuln_id: str | None = Field(description="ID de la vulnérabilité évaluée")
    decision: str = Field(description="Décision finale (Act, Attend, Track, Track*)")
    decision_color: str | None = Field(default=None, description="Couleur associée à la décision")
    path: list[DecisionPath] = Field(
        default_factory=list,
        description="Chemin complet de la décision (audit trail)",
    )
    error: str | None = Field(default=None, description="Erreur si l'évaluation a échoué")


class SingleEvaluationRequest(BaseModel):
    """
    Requête pour évaluer une seule vulnérabilité (temps réel).
    """

    vulnerability: VulnerabilityInput
    include_path: bool = Field(
        default=True,
        description="Inclure le chemin de décision dans la réponse",
    )


class EvaluationRequest(BaseModel):
    """
    Requête pour évaluer un batch de vulnérabilités.
    """

    vulnerabilities: list[VulnerabilityInput] = Field(
        description="Liste des vulnérabilités à évaluer",
    )
    include_path: bool = Field(
        default=True,
        description="Inclure le chemin de décision pour chaque vuln",
    )


class EvaluationResponse(BaseModel):
    """
    Réponse d'évaluation batch.
    """

    total: int = Field(description="Nombre total de vulnérabilités traitées")
    success_count: int = Field(description="Nombre d'évaluations réussies")
    error_count: int = Field(description="Nombre d'erreurs")
    results: list[EvaluationResult] = Field(description="Résultats détaillés")

    # Statistiques agrégées
    decision_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Comptage par décision (ex: {'Act': 5, 'Track': 10})",
    )


class ExportRequest(EvaluationRequest):
    """Requête pour évaluer et exporter un batch."""

    format: Literal["csv", "json"] = Field(
        default="csv",
        description="Format d'export: csv ou json",
    )
