"""
Tests de la validation de structure d'arbre.
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
    """Tests avec des arbres valides."""

    def test_valid_simple_tree(self, simple_tree_structure: TreeStructure):
        """Un arbre simple valide ne génère pas de warnings."""
        warnings = validate_tree_structure(simple_tree_structure)
        assert warnings == []

    def test_valid_tree_with_lookup(self, tree_with_lookup: TreeStructure):
        """Un arbre avec lookup valide ne génère pas de warnings."""
        warnings = validate_tree_structure(tree_with_lookup)
        assert warnings == []


class TestEmptyTree:
    """Tests avec un arbre vide."""

    def test_empty_tree(self):
        """Un arbre vide génère un warning."""
        tree = TreeStructure()
        warnings = validate_tree_structure(tree)
        assert len(warnings) == 1
        assert "aucun nœud" in warnings[0].lower()


class TestInvalidEdges:
    """Tests des edges invalides."""

    def test_edge_references_nonexistent_source(self):
        """Warning si une edge référence un nœud source inexistant."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [
            EdgeSchema(id="e1", source="nonexistent", target="n1"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("source inexistant" in w for w in warnings)

    def test_edge_references_nonexistent_target(self):
        """Warning si une edge référence un nœud cible inexistant."""
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
        assert any("cible inexistant" in w for w in warnings)


class TestCycleDetection:
    """Tests de détection de cycles."""

    def test_cycle_detected(self):
        """Warning si un cycle est détecté."""
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
    """Tests sans nœud racine."""

    def test_no_root_node(self):
        """Warning si tous les nœuds sont ciblés par des edges."""
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
        assert any("racine" in w.lower() for w in warnings)


class TestNoOutputNode:
    """Tests sans nœud output."""

    def test_no_output_node(self):
        """Warning si aucun nœud output n'est présent."""
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
    """Tests des handles invalides."""

    def test_condition_index_out_of_range(self):
        """Warning si un handle pointe vers une condition inexistante."""
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
            # handle-5 mais il n'y a qu'une seule condition (index 0)
            EdgeSchema(id="e1", source="n1", target="n2", source_handle="handle-5"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        warnings = validate_tree_structure(tree)
        assert any("condition_index=5" in w for w in warnings)

    def test_edge_from_output_node(self):
        """Warning si une edge sort d'un nœud output."""
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
