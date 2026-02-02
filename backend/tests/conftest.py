"""
Configuration des tests pytest.
"""

import pytest

from app.schemas.tree import (
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    TreeStructure,
)


@pytest.fixture
def simple_tree_structure() -> TreeStructure:
    """
    Arbre de test simple:
    - Nœud INPUT vérifie cvss_score
    - Si >= 9.0 -> Act
    - Si >= 7.0 -> Attend
    - Sinon -> Track
    """
    nodes = [
        NodeSchema(
            id="input-cvss",
            type=NodeType.INPUT,
            label="CVSS Score",
            config={"field": "cvss_score"},
            conditions=[
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Critical"),
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=7.0, label="High"),
                NodeCondition(operator=ConditionOperator.LESS_THAN, value=7.0, label="Low"),
            ],
        ),
        NodeSchema(
            id="output-act",
            type=NodeType.OUTPUT,
            label="Act",
            config={"decision": "Act", "color": "#ff0000"},
        ),
        NodeSchema(
            id="output-attend",
            type=NodeType.OUTPUT,
            label="Attend",
            config={"decision": "Attend", "color": "#ff9900"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        EdgeSchema(id="e1", source="input-cvss", target="output-act", label="Critical"),
        EdgeSchema(id="e2", source="input-cvss", target="output-attend", label="High"),
        EdgeSchema(id="e3", source="input-cvss", target="output-track", label="Low"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)


@pytest.fixture
def tree_with_lookup() -> TreeStructure:
    """
    Arbre de test avec lookup asset:
    - Nœud INPUT vérifie cvss_score (>= 7.0 -> lookup asset)
    - Nœud LOGIC lookup asset criticality
    - Décision basée sur criticité
    """
    nodes = [
        NodeSchema(
            id="input-cvss",
            type=NodeType.INPUT,
            label="CVSS Score",
            config={"field": "cvss_score"},
            conditions=[
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=7.0, label="High"),
                NodeCondition(operator=ConditionOperator.LESS_THAN, value=7.0, label="Low"),
            ],
        ),
        NodeSchema(
            id="lookup-asset",
            type=NodeType.LOOKUP,
            label="Asset Criticality",
            config={
                "lookup_table": "assets",
                "lookup_key": "asset_id",
                "lookup_field": "criticality",
                "default_branch": 0,
            },
            conditions=[
                NodeCondition(operator=ConditionOperator.EQUALS, value="Critical", label="Critical"),
                NodeCondition(operator=ConditionOperator.EQUALS, value="High", label="High"),
                NodeCondition(operator=ConditionOperator.IN, value=["Medium", "Low"], label="Normal"),
            ],
        ),
        NodeSchema(
            id="output-act",
            type=NodeType.OUTPUT,
            label="Act",
            config={"decision": "Act", "color": "#ff0000"},
        ),
        NodeSchema(
            id="output-attend",
            type=NodeType.OUTPUT,
            label="Attend",
            config={"decision": "Attend", "color": "#ff9900"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        EdgeSchema(id="e1", source="input-cvss", target="lookup-asset", label="High"),
        EdgeSchema(id="e2", source="input-cvss", target="output-track", label="Low"),
        EdgeSchema(id="e3", source="lookup-asset", target="output-act", label="Critical"),
        EdgeSchema(id="e4", source="lookup-asset", target="output-attend", label="High"),
        EdgeSchema(id="e5", source="lookup-asset", target="output-track", label="Normal"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)
