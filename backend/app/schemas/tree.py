from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class NodeType(str, Enum):
    """Types de nœuds disponibles dans l'arbre."""

    INPUT = "input"  # Nœud d'entrée (lecture d'un champ + conditions de sortie)
    LOOKUP = "lookup"  # Nœud lookup (recherche dans une table externe)
    OUTPUT = "output"  # Nœud de sortie (décision finale)


class ConditionOperator(str, Enum):
    """Opérateurs de condition pour les branches."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    IN = "in"  # Valeur dans une liste
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class SimpleConditionCriteria(BaseModel):
    """
    Critère simple pour une condition composée.
    Permet de spécifier un champ différent du champ principal du nœud.
    """

    field: str | None = Field(
        default=None,
        description="Champ à évaluer. Si None, utilise le champ principal du nœud.",
    )
    operator: ConditionOperator
    value: Any = Field(description="Valeur de comparaison")


class NodeCondition(BaseModel):
    """
    Condition d'une branche sortante d'un nœud.
    Permet de définir quand suivre cette branche.

    Supporte deux modes :
    - Mode simple (rétrocompatible) : operator + value
    - Mode composé : logic (AND/OR) + criteria (liste de critères)
    """

    label: str = Field(description="Label affiché sur la branche (ex: 'High', 'Critical')")

    # Mode simple (rétrocompatible) - utilisé si logic est None
    operator: ConditionOperator | None = Field(
        default=None,
        description="Opérateur pour le mode simple",
    )
    value: Any = Field(
        default=None,
        description="Valeur de comparaison pour le mode simple (peut être liste pour IN/NOT_IN)",
    )

    # Mode composé - utilisé si logic est défini
    logic: Literal["AND", "OR"] | None = Field(
        default=None,
        description="Logique de combinaison des critères (AND ou OR)",
    )
    criteria: list[SimpleConditionCriteria] | None = Field(
        default=None,
        description="Liste des critères pour le mode composé",
    )

    @model_validator(mode="after")
    def validate_condition_mode(self) -> "NodeCondition":
        """Valide que la condition est en mode simple OU composé, pas les deux."""
        has_simple = self.operator is not None
        has_compound = self.logic is not None and self.criteria is not None

        if has_simple and has_compound:
            raise ValueError(
                "Une condition ne peut pas avoir à la fois operator/value ET logic/criteria. "
                "Utilisez soit le mode simple (operator + value), soit le mode composé (logic + criteria)."
            )

        if not has_simple and not has_compound:
            raise ValueError(
                "Une condition doit avoir soit operator (mode simple), "
                "soit logic + criteria (mode composé)."
            )

        if self.logic is not None and (self.criteria is None or len(self.criteria) == 0):
            raise ValueError(
                "Le mode composé (logic défini) nécessite au moins un critère dans 'criteria'."
            )

        return self


class NodeSchema(BaseModel):
    """
    Schéma d'un nœud dans l'arbre de décision.
    """

    id: str = Field(description="Identifiant unique du nœud")
    type: NodeType
    label: str = Field(description="Label affiché dans l'UI")

    # Position dans le canvas (pour React Flow)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

    # Configuration spécifique au type de nœud
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="""
        Configuration selon le type:
        - INPUT: {"field": "cvss_score", "input_count": 1} - champ à lire, nombre d'entrées
        - LOOKUP: {"lookup_table": "assets", "lookup_key": "asset_id", "lookup_field": "criticality", "input_count": 1}
        - OUTPUT: {"decision": "Act", "color": "#ff0000"}

        input_count > 1 active le mode multi-input où chaque entrée génère ses propres sorties.
        Les handles de sortie deviennent: handle-{input_index}-{condition_index}
        """,
    )

    # Conditions pour les branches sortantes (sauf OUTPUT)
    conditions: list[NodeCondition] = Field(
        default_factory=list,
        description="Conditions pour chaque branche sortante",
    )


class EdgeSchema(BaseModel):
    """
    Schéma d'une arête (connexion) entre deux nœuds.
    """

    id: str = Field(description="Identifiant unique de l'arête")
    source: str = Field(description="ID du nœud source")
    target: str = Field(description="ID du nœud cible")
    source_handle: str | None = Field(
        default=None,
        description="Handle de sortie. Format: 'handle-{condition}' ou 'handle-{input}-{condition}' pour multi-input",
    )
    target_handle: str | None = Field(
        default=None,
        description="Handle d'entrée pour les nœuds multi-input. Format: 'input-{index}'",
    )
    label: str | None = Field(default=None, description="Label de la condition")


class TreeStructure(BaseModel):
    """Structure complète de l'arbre de décision."""

    nodes: list[NodeSchema] = Field(default_factory=list)
    edges: list[EdgeSchema] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Métadonnées (viewport, zoom, etc.)",
    )


class TreeCreate(BaseModel):
    """Schéma pour la création d'un arbre."""

    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    structure: TreeStructure = Field(default_factory=TreeStructure)


class TreeUpdate(BaseModel):
    """Schéma pour la mise à jour d'un arbre."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    structure: TreeStructure | None = None
    version_comment: str | None = Field(
        default=None,
        max_length=500,
        description="Commentaire pour cette version (si sauvegarde avec versioning)",
    )


class TreeResponse(BaseModel):
    """Schéma de réponse pour un arbre."""

    id: int
    name: str
    description: str | None
    structure: TreeStructure
    is_default: bool = False
    api_enabled: bool = False
    api_slug: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TreeListItem(BaseModel):
    """Schéma résumé pour la liste des arbres (sidebar)."""

    id: int
    name: str
    description: str | None
    is_default: bool
    api_enabled: bool
    api_slug: str | None
    node_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TreeApiConfig(BaseModel):
    """Schéma pour la configuration API d'un arbre."""

    api_enabled: bool
    api_slug: str | None = Field(
        default=None,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="Slug URL-safe (minuscules, chiffres, tirets)",
    )


class TreeDuplicateRequest(BaseModel):
    """Schéma pour la duplication d'un arbre."""

    new_name: str = Field(max_length=255, description="Nom du nouvel arbre")
    include_assets: bool = Field(default=True, description="Copier les assets associés")


class TreeVersionResponse(BaseModel):
    """Schéma de réponse pour une version d'arbre."""

    id: int
    tree_id: int
    version_number: int
    structure_snapshot: TreeStructure
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
