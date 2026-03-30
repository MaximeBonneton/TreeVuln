"""
Pytest test configuration.
"""

import pytest

from app.schemas.tree import (
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    SimpleConditionCriteria,
    TreeStructure,
)


@pytest.fixture
def simple_tree_structure() -> TreeStructure:
    """
    Simple test tree:
    - INPUT node checks cvss_score
    - If >= 9.0 -> Act
    - If >= 7.0 -> Attend
    - Otherwise -> Track
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
    Test tree with asset lookup:
    - INPUT node checks cvss_score (>= 7.0 -> asset lookup)
    - LOGIC node looks up asset criticality
    - Decision based on criticality
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


@pytest.fixture
def compound_condition_tree() -> TreeStructure:
    """
    Test tree with compound conditions:
    - INPUT node checks cvss_av AND cvss_ac in compound mode
    - If cvss_av=Network AND cvss_ac=Low -> Act
    - If cvss_av=Network OR cvss_ac=Low -> Attend
    - Otherwise -> Track
    """
    nodes = [
        NodeSchema(
            id="input-compound",
            type=NodeType.INPUT,
            label="CVSS Compound",
            config={"field": "cvss_av"},
            conditions=[
                NodeCondition(
                    label="Network+Low",
                    logic="AND",
                    criteria=[
                        SimpleConditionCriteria(field="cvss_av", operator=ConditionOperator.EQUALS, value="Network"),
                        SimpleConditionCriteria(field="cvss_ac", operator=ConditionOperator.EQUALS, value="Low"),
                    ],
                ),
                NodeCondition(
                    label="Network OR Low",
                    logic="OR",
                    criteria=[
                        SimpleConditionCriteria(field="cvss_av", operator=ConditionOperator.EQUALS, value="Network"),
                        SimpleConditionCriteria(field="cvss_ac", operator=ConditionOperator.EQUALS, value="Low"),
                    ],
                ),
                NodeCondition(
                    label="Other",
                    operator=ConditionOperator.IS_NOT_NULL,
                    value=None,
                ),
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
        EdgeSchema(id="e1", source="input-compound", target="output-act", source_handle="handle-0", label="Network+Low"),
        EdgeSchema(id="e2", source="input-compound", target="output-attend", source_handle="handle-1", label="Network OR Low"),
        EdgeSchema(id="e3", source="input-compound", target="output-track", source_handle="handle-2", label="Other"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)


@pytest.fixture
def multi_input_tree() -> TreeStructure:
    """
    Test tree with multi-input node (input_count=2):
    - INPUT node "kev" (2 outputs: true/false)
    - INPUT node "Technical Impact" (input_count=2, 2 conditions each: >=9 / <9)
    - 4 output nodes
    """
    nodes = [
        NodeSchema(
            id="input-kev",
            type=NodeType.INPUT,
            label="KEV",
            config={"field": "kev"},
            conditions=[
                NodeCondition(operator=ConditionOperator.EQUALS, value=True, label="Active"),
                NodeCondition(operator=ConditionOperator.EQUALS, value=False, label="None"),
            ],
        ),
        NodeSchema(
            id="input-impact",
            type=NodeType.INPUT,
            label="Technical Impact",
            config={"field": "cvss_score", "input_count": 2},
            conditions=[
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Total"),
                NodeCondition(operator=ConditionOperator.LESS_THAN, value=9.0, label="Partial"),
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
            id="output-track-star",
            type=NodeType.OUTPUT,
            label="Track*",
            config={"decision": "Track*", "color": "#ffff00"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        # kev=true -> input-impact input 0
        EdgeSchema(id="e1", source="input-kev", target="input-impact", source_handle="handle-0", target_handle="input-0", label="Active"),
        # kev=false -> input-impact input 1
        EdgeSchema(id="e2", source="input-kev", target="input-impact", source_handle="handle-1", target_handle="input-1", label="None"),
        # input-impact, input 0 (kev=true), cvss>=9 -> Act
        EdgeSchema(id="e3", source="input-impact", target="output-act", source_handle="handle-0-0"),
        # input-impact, input 0 (kev=true), cvss<9 -> Attend
        EdgeSchema(id="e4", source="input-impact", target="output-attend", source_handle="handle-0-1"),
        # input-impact, input 1 (kev=false), cvss>=9 -> Track*
        EdgeSchema(id="e5", source="input-impact", target="output-track-star", source_handle="handle-1-0"),
        # input-impact, input 1 (kev=false), cvss<9 -> Track
        EdgeSchema(id="e6", source="input-impact", target="output-track", source_handle="handle-1-1"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)
