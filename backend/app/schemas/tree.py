from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class NodeCondition(BaseModel):
    """
    Condition d'une branche sortante d'un nœud.
    Permet de définir quand suivre cette branche.
    """

    operator: ConditionOperator
    value: Any = Field(description="Valeur de comparaison (peut être liste pour IN/NOT_IN)")
    label: str = Field(description="Label affiché sur la branche (ex: 'High', 'Critical')")


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
        - INPUT: {"field": "cvss_score"} - champ à lire dans la vulnérabilité
        - LOOKUP: {"lookup_table": "assets", "lookup_key": "asset_id", "lookup_field": "criticality"}
        - OUTPUT: {"decision": "Act", "color": "#ff0000"}
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
        description="Handle de sortie (correspond à l'index de la condition)",
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
