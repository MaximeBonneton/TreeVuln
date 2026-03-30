from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.field_mapping import FieldMapping


class NodeType(str, Enum):
    """Available node types in the tree."""

    INPUT = "input"  # Input node (reads a field + output conditions)
    LOOKUP = "lookup"  # Lookup node (searches in an external table)
    OUTPUT = "output"  # Output node (final decision)
    EQUATION = "equation"  # Equation node (multi-field calculation with formula)


class ConditionOperator(str, Enum):
    """Condition operators for branches."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    IN = "in"  # Value in a list
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class SimpleConditionCriteria(BaseModel):
    """
    Simple criterion for a compound condition.
    Allows specifying a field different from the node's main field.
    """

    field: str | None = Field(
        default=None,
        description="Field to evaluate. If None, uses the node's main field.",
    )
    operator: ConditionOperator
    value: Any = Field(description="Comparison value")


class NodeCondition(BaseModel):
    """
    Condition for an outgoing branch of a node.
    Defines when to follow this branch.

    Supports two modes:
    - Simple mode (backward compatible): operator + value
    - Compound mode: logic (AND/OR) + criteria (list of criteria)
    """

    label: str = Field(description="Label displayed on the branch (e.g. 'High', 'Critical')")

    # Simple mode (backward compatible) - used when logic is None
    operator: ConditionOperator | None = Field(
        default=None,
        description="Operator for simple mode",
    )
    value: Any = Field(
        default=None,
        description="Comparison value for simple mode (can be a list for IN/NOT_IN)",
    )

    # Compound mode - used when logic is defined
    logic: Literal["AND", "OR"] | None = Field(
        default=None,
        description="Logic for combining criteria (AND or OR)",
    )
    criteria: list[SimpleConditionCriteria] | None = Field(
        default=None,
        description="List of criteria for compound mode",
    )

    @model_validator(mode="after")
    def validate_condition_mode(self) -> "NodeCondition":
        """Validate that the condition is in simple OR compound mode, not both."""
        has_simple = self.operator is not None
        has_compound = self.logic is not None and self.criteria is not None

        if has_simple and has_compound:
            raise ValueError(
                "A condition cannot have both operator/value AND logic/criteria. "
                "Use either simple mode (operator + value) or compound mode (logic + criteria)."
            )

        if not has_simple and not has_compound:
            raise ValueError(
                "A condition must have either operator (simple mode) "
                "or logic + criteria (compound mode)."
            )

        if self.logic is not None and (self.criteria is None or len(self.criteria) == 0):
            raise ValueError(
                "Compound mode (logic defined) requires at least one criterion in 'criteria'."
            )

        return self


class NodeSchema(BaseModel):
    """
    Schema for a node in the decision tree.
    """

    id: str = Field(description="Unique node identifier")
    type: NodeType
    label: str = Field(description="Label displayed in the UI")

    # Position in the canvas (for React Flow)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

    # Configuration specific to the node type
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="""
        Configuration by type:
        - INPUT: {"field": "cvss_score", "input_count": 1} - field to read, number of inputs
        - LOOKUP: {"lookup_table": "assets", "lookup_key": "asset_id", "lookup_field": "criticality", "input_count": 1}
        - OUTPUT: {"decision": "Act", "color": "#ff0000"}

        input_count > 1 activates multi-input mode where each input generates its own outputs.
        Output handles become: handle-{input_index}-{condition_index}
        """,
    )

    # Conditions for outgoing branches (except OUTPUT)
    conditions: list[NodeCondition] = Field(
        default_factory=list,
        description="Conditions for each outgoing branch",
    )


class EdgeSchema(BaseModel):
    """
    Schema for an edge (connection) between two nodes.
    """

    id: str = Field(description="Unique edge identifier")
    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    source_handle: str | None = Field(
        default=None,
        description="Output handle. Format: 'handle-{condition}' or 'handle-{input}-{condition}' for multi-input",
    )
    target_handle: str | None = Field(
        default=None,
        description="Input handle for multi-input nodes. Format: 'input-{index}'",
    )
    label: str | None = Field(default=None, description="Condition label")


class TreeStructure(BaseModel):
    """Complete decision tree structure."""

    nodes: list[NodeSchema] = Field(default_factory=list)
    edges: list[EdgeSchema] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata (viewport, zoom, etc.)",
    )


class TreeCreate(BaseModel):
    """Schema for creating a tree."""

    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    structure: TreeStructure = Field(default_factory=TreeStructure)


class TreeUpdate(BaseModel):
    """Schema for updating a tree."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    structure: TreeStructure | None = None
    version_comment: str | None = Field(
        default=None,
        max_length=500,
        description="Comment for this version (if saving with versioning)",
    )


class TreeResponse(BaseModel):
    """Response schema for a tree."""

    id: int
    name: str
    description: str | None
    structure: TreeStructure
    is_default: bool = False
    api_enabled: bool = False
    api_slug: str | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TreeListItem(BaseModel):
    """Summary schema for the tree list (sidebar)."""

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
    """Schema for the API configuration of a tree."""

    api_enabled: bool
    api_slug: str | None = Field(
        default=None,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
        description="URL-safe slug (lowercase, digits, hyphens)",
    )


class TreeDuplicateRequest(BaseModel):
    """Schema for duplicating a tree."""

    new_name: str = Field(max_length=255, description="Name of the new tree")
    include_assets: bool = Field(default=True, description="Copy associated assets")


class TreeVersionResponse(BaseModel):
    """Response schema for a tree version."""

    id: int
    tree_id: int
    version_number: int
    structure_snapshot: TreeStructure
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Decision-as-Code (export/import) ---


class TreeExportData(BaseModel):
    """Tree content in the export file."""

    name: str
    description: str | None = None
    structure: TreeStructure
    field_mapping: FieldMapping | None = None


class TreeExportFile(BaseModel):
    """Complete Decision-as-Code export file format."""

    format: Literal["treevuln-decision-tree"]
    version: Literal[1]
    exported_at: datetime
    tree: TreeExportData


class TreeImportRequest(BaseModel):
    """Decision-as-Code import file (same format as export).

    exported_at is optional to allow manually created files.
    """

    format: str
    version: int
    exported_at: datetime | None = None
    tree: TreeExportData

    @model_validator(mode="after")
    def validate_format_and_version(self) -> "TreeImportRequest":
        if self.format != "treevuln-decision-tree":
            raise ValueError(
                f"Unknown format: {self.format}. Expected: treevuln-decision-tree"
            )
        if self.version not in (1,):
            raise ValueError(
                f"Unsupported version: {self.version}. Supported: [1]"
            )
        return self
