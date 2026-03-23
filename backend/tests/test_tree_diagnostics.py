"""Tests du module de diagnostic d'arbre."""

import pytest

from app.schemas.diagnostic import DiagnosticItem, DiagnosticResult
from app.schemas.tree import (
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    TreeStructure,
)
from app.services.tree_diagnostics import diagnose_tree


class TestDiagnosticSchemas:
    """Tests des schemas de diagnostic."""

    def test_diagnostic_item_creation(self):
        item = DiagnosticItem(
            code="NO_ROOT",
            message="Aucun noeud racine",
            severity="error",
        )
        assert item.code == "NO_ROOT"
        assert item.severity == "error"
        assert item.node_id is None
        assert item.edge_id is None

    def test_diagnostic_item_with_node_id(self):
        item = DiagnosticItem(
            code="INPUT_NO_FIELD",
            message="Champ non configure",
            severity="error",
            node_id="input-1",
        )
        assert item.node_id == "input-1"

    def test_diagnostic_result(self):
        result = DiagnosticResult(
            errors=[DiagnosticItem(code="NO_ROOT", message="x", severity="error")],
            warnings=[DiagnosticItem(code="DEAD_BRANCH", message="y", severity="warning", node_id="n1")],
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestStructuralChecks:
    """Tests des checks structurels."""

    def test_valid_tree_no_errors(self, simple_tree_structure: TreeStructure):
        result = diagnose_tree(simple_tree_structure)
        assert len(result.errors) == 0

    def test_empty_tree(self):
        result = diagnose_tree(TreeStructure())
        codes = [e.code for e in result.errors]
        assert "NO_ROOT" in codes or "NO_OUTPUT" in codes

    def test_edge_source_missing(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="ghost", target="n1")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "EDGE_SOURCE_MISSING" in codes

    def test_edge_target_missing(self):
        nodes = [
            NodeSchema(
                id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")],
            ),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="ghost")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "EDGE_TARGET_MISSING" in codes

    def test_cycle_detected(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="A", config={"field": "x"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
            NodeSchema(id="n2", type=NodeType.INPUT, label="B", config={"field": "y"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="b", label="B")]),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="n2", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n2", target="n1", source_handle="handle-0"),
        ]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "CYCLE_DETECTED" in codes

    def test_no_output(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="A", config={"field": "x"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
        ]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=[]))
        codes = [e.code for e in result.errors]
        assert "NO_OUTPUT" in codes

    def test_no_conditions_input(self):
        """Un noeud input sans condition de sortie."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"}, conditions=[]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "NO_CONDITIONS" in codes

    def test_no_conditions_equation(self):
        """Un noeud equation sans condition de sortie."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.EQUATION, label="Eq", config={"formula": "x * 2", "variables": ["x"]}, conditions=[]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "NO_CONDITIONS" in codes

    def test_edge_from_output(self):
        nodes = [
            NodeSchema(id="out1", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
            NodeSchema(id="out2", type=NodeType.OUTPUT, label="Out2", config={"decision": "Y"}),
        ]
        edges = [EdgeSchema(id="e1", source="out1", target="out2", source_handle="handle-0")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "EDGE_FROM_OUTPUT" in codes


class TestConfigurationChecks:
    """Tests des checks de configuration."""

    def test_input_no_field(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "INPUT_NO_FIELD" in codes
        input_err = [e for e in result.errors if e.code == "INPUT_NO_FIELD"][0]
        assert input_err.node_id == "n1"

    def test_lookup_incomplete(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.LOOKUP, label="Lk", config={"lookup_table": "assets"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "LOOKUP_INCOMPLETE" in codes

    def test_output_no_decision(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "OUTPUT_NO_DECISION" in codes

    def test_equation_no_formula(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.EQUATION, label="Eq", config={},
                       conditions=[NodeCondition(operator=ConditionOperator.GREATER_THAN, value=5, label="High")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [e.code for e in result.errors]
        assert "EQUATION_NO_FORMULA" in codes

    def test_equation_variable_no_value_map(self):
        """Warning si une variable d'equation n'a pas de value_map."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.EQUATION, label="Eq",
                       config={"formula": "x * 2", "variables": ["x"]},
                       conditions=[NodeCondition(operator=ConditionOperator.GREATER_THAN, value=5, label="High")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out", source_handle="handle-0")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "EQUATION_NO_VALUE_MAP" in codes

    def test_equation_variable_with_value_map_no_warning(self):
        """Pas de warning si la variable a un value_map."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.EQUATION, label="Eq",
                       config={
                           "formula": "x * 2",
                           "variables": ["x"],
                           "value_maps": {"x": {"entries": [{"text": "High", "value": 10}], "default_value": 0}},
                       },
                       conditions=[NodeCondition(operator=ConditionOperator.GREATER_THAN, value=5, label="High")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out", source_handle="handle-0")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "EQUATION_NO_VALUE_MAP" not in codes

    def test_isolated_node(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
            NodeSchema(id="isolated", type=NodeType.INPUT, label="Alone", config={"field": "y"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="b", label="B")]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "ISOLATED_NODE" in codes
        isolated_warning = [w for w in result.warnings if w.code == "ISOLATED_NODE"][0]
        assert isolated_warning.node_id == "isolated"

    def test_orphan_handle(self):
        """Un noeud avec 2 conditions mais seulement 1 edge connectee."""
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[
                           NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9, label="High"),
                           NodeCondition(operator=ConditionOperator.LESS_THAN, value=9, label="Low"),
                       ]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out", source_handle="handle-0")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "ORPHAN_HANDLE" in codes


class TestLogicChecks:
    """Tests des checks logiques."""

    def test_dead_branch(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[
                           NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=5, label="High"),
                           NodeCondition(operator=ConditionOperator.LESS_THAN, value=5, label="Low"),
                       ]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "Act"}),
            NodeSchema(id="n2", type=NodeType.INPUT, label="Dead", config={"field": "y"},
                       conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="a", label="A")]),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="out", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n1", target="n2", source_handle="handle-1"),
        ]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "DEAD_BRANCH" in codes

    def test_no_dead_branch_in_valid_tree(self, simple_tree_structure: TreeStructure):
        result = diagnose_tree(simple_tree_structure)
        codes = [w.code for w in result.warnings]
        assert "DEAD_BRANCH" not in codes

    def test_numeric_gap(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[
                           NodeCondition(operator=ConditionOperator.LESS_THAN, value=5, label="Low"),
                           NodeCondition(operator=ConditionOperator.GREATER_THAN, value=7, label="High"),
                       ]),
            NodeSchema(id="out1", type=NodeType.OUTPUT, label="Out1", config={"decision": "A"}),
            NodeSchema(id="out2", type=NodeType.OUTPUT, label="Out2", config={"decision": "B"}),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="out1", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n1", target="out2", source_handle="handle-1"),
        ]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "NUMERIC_GAP" in codes

    def test_numeric_overlap(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[
                           NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=5, label="High"),
                           NodeCondition(operator=ConditionOperator.LESS_THAN_OR_EQUAL, value=7, label="Low"),
                       ]),
            NodeSchema(id="out1", type=NodeType.OUTPUT, label="Out1", config={"decision": "A"}),
            NodeSchema(id="out2", type=NodeType.OUTPUT, label="Out2", config={"decision": "B"}),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="out1", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n1", target="out2", source_handle="handle-1"),
        ]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "NUMERIC_OVERLAP" in codes

    def test_single_condition(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[
                           NodeCondition(operator=ConditionOperator.GREATER_THAN, value=0, label="Positive"),
                       ]),
            NodeSchema(id="out", type=NodeType.OUTPUT, label="Out", config={"decision": "X"}),
        ]
        edges = [EdgeSchema(id="e1", source="n1", target="out", source_handle="handle-0")]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "SINGLE_CONDITION" in codes

    def test_no_gap_with_contiguous_ranges(self):
        nodes = [
            NodeSchema(id="n1", type=NodeType.INPUT, label="In", config={"field": "x"},
                       conditions=[
                           NodeCondition(operator=ConditionOperator.LESS_THAN, value=7, label="Low"),
                           NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=7, label="High"),
                       ]),
            NodeSchema(id="out1", type=NodeType.OUTPUT, label="Out1", config={"decision": "A"}),
            NodeSchema(id="out2", type=NodeType.OUTPUT, label="Out2", config={"decision": "B"}),
        ]
        edges = [
            EdgeSchema(id="e1", source="n1", target="out1", source_handle="handle-0"),
            EdgeSchema(id="e2", source="n1", target="out2", source_handle="handle-1"),
        ]
        result = diagnose_tree(TreeStructure(nodes=nodes, edges=edges))
        codes = [w.code for w in result.warnings]
        assert "NUMERIC_GAP" not in codes
