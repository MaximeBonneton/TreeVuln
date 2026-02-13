"""
Tests du routing multi-input pour les nœuds avec input_count > 1.
"""

import pytest

from app.engine.inference import InferenceEngine
from app.schemas.tree import (
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    TreeStructure,
)
from app.schemas.vulnerability import VulnerabilityInput


class TestMultiInputRouting:
    """Tests du routing multi-input."""

    def test_kev_true_high_cvss(self, multi_input_tree: TreeStructure):
        """kev=true + cvss>=9 -> Act (via input-0, handle-0-0)."""
        engine = InferenceEngine(multi_input_tree)
        vuln = VulnerabilityInput(id="vuln-1", kev=True, cvss_score=9.5)

        result = engine.evaluate(vuln)
        assert result.decision == "Act"

    def test_kev_true_low_cvss(self, multi_input_tree: TreeStructure):
        """kev=true + cvss<9 -> Attend (via input-0, handle-0-1)."""
        engine = InferenceEngine(multi_input_tree)
        vuln = VulnerabilityInput(id="vuln-2", kev=True, cvss_score=7.0)

        result = engine.evaluate(vuln)
        assert result.decision == "Attend"

    def test_kev_false_high_cvss(self, multi_input_tree: TreeStructure):
        """kev=false + cvss>=9 -> Track* (via input-1, handle-1-0)."""
        engine = InferenceEngine(multi_input_tree)
        vuln = VulnerabilityInput(id="vuln-3", kev=False, cvss_score=9.5)

        result = engine.evaluate(vuln)
        assert result.decision == "Track*"

    def test_kev_false_low_cvss(self, multi_input_tree: TreeStructure):
        """kev=false + cvss<9 -> Track (via input-1, handle-1-1)."""
        engine = InferenceEngine(multi_input_tree)
        vuln = VulnerabilityInput(id="vuln-4", kev=False, cvss_score=5.0)

        result = engine.evaluate(vuln)
        assert result.decision == "Track"


class TestMultiInputHandleParsing:
    """Tests du parsing des handles multi-input."""

    def test_parse_input_handle(self, multi_input_tree: TreeStructure):
        """Parse target_handle 'input-0' -> index 0."""
        engine = InferenceEngine(multi_input_tree)
        assert engine._parse_input_index("input-0") == 0
        assert engine._parse_input_index("input-1") == 1

    def test_parse_invalid_handle(self, multi_input_tree: TreeStructure):
        """Handles invalides retournent None."""
        engine = InferenceEngine(multi_input_tree)
        assert engine._parse_input_index(None) is None
        assert engine._parse_input_index("") is None
        assert engine._parse_input_index("target") is None

    def test_parse_malformed_handle(self, multi_input_tree: TreeStructure):
        """Handles malformés retournent None."""
        engine = InferenceEngine(multi_input_tree)
        assert engine._parse_input_index("input-") is None
        assert engine._parse_input_index("input-abc") is None


class TestMultiInputAuditTrail:
    """Tests de l'audit trail pour multi-input."""

    def test_path_includes_all_nodes(self, multi_input_tree: TreeStructure):
        """Le chemin doit contenir les 3 nœuds traversés."""
        engine = InferenceEngine(multi_input_tree)
        vuln = VulnerabilityInput(id="vuln-1", kev=True, cvss_score=9.5)

        result = engine.evaluate(vuln, include_path=True)

        assert len(result.path) == 3  # input-kev + input-impact + output-act
        assert result.path[0].node_id == "input-kev"
        assert result.path[1].node_id == "input-impact"
        assert result.path[2].node_id == "output-act"


class TestMultiInputEdgeCases:
    """Tests des cas limites multi-input."""

    def test_input_index_out_of_bounds(self):
        """input_index >= input_count retourne une erreur."""
        nodes = [
            NodeSchema(
                id="input-a",
                type=NodeType.INPUT,
                label="A",
                config={"field": "kev"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.EQUALS, value=True, label="Yes"),
                ],
            ),
            NodeSchema(
                id="input-b",
                type=NodeType.INPUT,
                label="B",
                config={"field": "cvss_score", "input_count": 1},
                conditions=[
                    NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=5.0, label="High"),
                ],
            ),
            NodeSchema(
                id="output-x",
                type=NodeType.OUTPUT,
                label="X",
                config={"decision": "X"},
            ),
        ]
        edges = [
            # Pointe vers input-2 qui n'existe pas (input_count=1, max index=0)
            EdgeSchema(id="e1", source="input-a", target="input-b", source_handle="handle-0", target_handle="input-2"),
            EdgeSchema(id="e2", source="input-b", target="output-x", source_handle="handle-0"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        engine = InferenceEngine(tree)

        vuln = VulnerabilityInput(id="vuln-1", kev=True, cvss_score=9.0)
        result = engine.evaluate(vuln)

        assert result.decision == "Error"
        assert "input_index" in result.error
