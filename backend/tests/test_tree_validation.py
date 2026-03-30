"""
Tests for tree structure validation.
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
from app.services.tree_validation import validate_tree_structure


class TestValidTreeStructure:
    """Tests with valid trees."""

    def test_valid_simple_tree(self, simple_tree_structure: TreeStructure):
        """A valid simple tree does not generate warnings."""
        warnings = validate_tree_structure(simple_tree_structure)
        assert warnings == []

    def test_valid_tree_with_lookup(self, tree_with_lookup: TreeStructure):
        """A valid tree with lookup does not generate warnings."""
        warnings = validate_tree_structure(tree_with_lookup)
        assert warnings == []


class TestEmptyTree:
    """Tests with an empty tree."""

    def test_empty_tree(self):
        """An empty tree generates a warning."""
        tree = TreeStructure()
        warnings = validate_tree_structure(tree)
        assert len(warnings) == 1
        assert "no nodes" in warnings[0].lower()


class TestInvalidEdges:
    """Tests for invalid edges."""

    def test_edge_references_nonexistent_source(self):
        """Warning if an edge references a non-existent source node."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [
            EdgeSchema(id="e1", source="nonexistent", target="n1"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("non-existent source" in w for w in warnings)

    def test_edge_references_nonexistent_target(self):
        """Warning if an edge references a non-existent target node."""
        nodes = [
            NodeSchema(
                id="n1", type=NodeType.INPUT, label="In",
                config={"field": "x"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")],
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="nonexistent"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("non-existent target" in w for w in warnings)


class TestCycleDetection:
    """Tests for cycle detection."""

    def test_cycle_detected(self):
        """Warning if a cycle is detected."""
        nodes = [
            NodeSchema(
                id="n1", type=NodeType.INPUT, label="A",
                config={"field": "x"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")],
            ),
            NodeSchema(
                id="n2", type=NodeType.INPUT, label="B",
                config={"field": "y"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="b", label="B")],
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="n2", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n2", target="n1", source_handle="handle-0"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("cycle" in w.lower() for w in warnings)


class TestNoRootNode:
    """Tests without a root node."""

    def test_no_root_node(self):
        """Warning if all nodes are targeted by edges."""
        nodes = [
            NodeSchema(
                id="n1", type=NodeType.INPUT, label="A",
                config={"field": "x"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")],
            ),
            NodeSchema(
                id="n2", type=NodeType.INPUT, label="B",
                config={"field": "y"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="b", label="B")],
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="n2", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n2", target="n1", source_handle="handle-0"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("root" in w.lower() for w in warnings)


class TestNoOutputNode:
    """Tests without an output node."""

    def test_no_output_node(self):
        """Warning if no output node is present."""
        nodes = [
            NodeSchema(
                id="n1", type=NodeType.INPUT, label="A",
                config={"field": "x"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")],
            ),
        ]
        tree = TreeStructure(nodes=nodes, edges=[])
        warnings = validate_tree_structure(tree)
        assert any("output" in w.lower() for w in warnings)


class TestInvalidHandles:
    """Tests for invalid handles."""

    def test_condition_index_out_of_range(self):
        """Warning if a handle points to a non-existent condition."""
        nodes = [
            NodeSchema(
                id="n1", type=NodeType.INPUT, label="A",
                config={"field": "x"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A"),
                ],
            ),
            NodeSchema(
                id="n2", type=NodeType.OUTPUT, label="Out",
                config={"decision": "X"},
            ),
        ]
        edges = [
            # handle-5 but there is only one condition (index 0)
            EdgeSchema(id="e1", source="n1", target="n2", source_handle="handle-5"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("condition_index=5" in w for w in warnings)

    def test_edge_from_output_node(self):
        """Warning if an edge originates from an output node."""
        nodes = [
            NodeSchema(
                id="out", type=NodeType.OUTPUT, label="Out",
                config={"decision": "X"},
            ),
            NodeSchema(
                id="n2", type=NodeType.OUTPUT, label="Out2",
                config={"decision": "Y"},
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="out", target="n2", source_handle="handle-0"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("output" in w.lower() for w in warnings)
