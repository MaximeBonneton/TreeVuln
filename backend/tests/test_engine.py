"""
Tests du moteur d'inférence.
"""

import pytest

from app.engine.inference import InferenceEngine
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class TestInferenceEngine:
    """Tests pour InferenceEngine."""

    def test_simple_tree_critical_cvss(self, simple_tree_structure: TreeStructure):
        """Test: CVSS >= 9.0 devrait retourner Act."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-1", cvss_score=9.5)

        result = engine.evaluate(vuln)

        assert result.decision == "Act"
        assert result.error is None
        assert len(result.path) == 2  # input + output

    def test_simple_tree_high_cvss(self, simple_tree_structure: TreeStructure):
        """Test: CVSS >= 7.0 et < 9.0 devrait retourner Attend."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-2", cvss_score=7.5)

        result = engine.evaluate(vuln)

        assert result.decision == "Attend"
        assert result.error is None

    def test_simple_tree_low_cvss(self, simple_tree_structure: TreeStructure):
        """Test: CVSS < 7.0 devrait retourner Track."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-3", cvss_score=4.0)

        result = engine.evaluate(vuln)

        assert result.decision == "Track"
        assert result.error is None

    def test_audit_trail_contains_all_nodes(self, simple_tree_structure: TreeStructure):
        """Test: Le chemin de décision contient tous les nœuds traversés."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-4", cvss_score=9.0)

        result = engine.evaluate(vuln, include_path=True)

        assert len(result.path) == 2
        assert result.path[0].node_id == "input-cvss"
        assert result.path[0].value_found == 9.0
        assert result.path[0].condition_matched == "Critical"
        assert result.path[1].node_id == "output-act"

    def test_no_path_when_disabled(self, simple_tree_structure: TreeStructure):
        """Test: Pas de chemin quand include_path=False."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-5", cvss_score=9.0)

        result = engine.evaluate(vuln, include_path=False)

        assert result.decision == "Act"
        assert len(result.path) == 0


class TestInferenceEngineWithLookup:
    """Tests pour InferenceEngine avec lookup."""

    def test_lookup_critical_asset(self, tree_with_lookup: TreeStructure):
        """Test: CVSS élevé + asset critique -> Act."""
        engine = InferenceEngine(tree_with_lookup)
        vuln = VulnerabilityInput(
            id="vuln-1",
            cvss_score=8.0,
            asset_id="srv-prod-001",
        )
        lookups = {
            "assets": {
                "srv-prod-001": {"criticality": "Critical"},
            }
        }

        result = engine.evaluate(vuln, lookups=lookups)

        assert result.decision == "Act"
        assert result.error is None

    def test_lookup_high_asset(self, tree_with_lookup: TreeStructure):
        """Test: CVSS élevé + asset high -> Attend."""
        engine = InferenceEngine(tree_with_lookup)
        vuln = VulnerabilityInput(
            id="vuln-2",
            cvss_score=8.0,
            asset_id="ws-admin-001",
        )
        lookups = {
            "assets": {
                "ws-admin-001": {"criticality": "High"},
            }
        }

        result = engine.evaluate(vuln, lookups=lookups)

        assert result.decision == "Attend"

    def test_lookup_normal_asset(self, tree_with_lookup: TreeStructure):
        """Test: CVSS élevé + asset normal -> Track."""
        engine = InferenceEngine(tree_with_lookup)
        vuln = VulnerabilityInput(
            id="vuln-3",
            cvss_score=8.0,
            asset_id="srv-dev-001",
        )
        lookups = {
            "assets": {
                "srv-dev-001": {"criticality": "Medium"},
            }
        }

        result = engine.evaluate(vuln, lookups=lookups)

        assert result.decision == "Track"

    def test_low_cvss_skips_lookup(self, tree_with_lookup: TreeStructure):
        """Test: CVSS bas ne passe pas par le lookup."""
        engine = InferenceEngine(tree_with_lookup)
        vuln = VulnerabilityInput(
            id="vuln-4",
            cvss_score=5.0,
            asset_id="srv-prod-001",  # Asset critique mais CVSS bas
        )

        result = engine.evaluate(vuln)  # Pas de lookups fournis

        assert result.decision == "Track"
        # Seuls 2 nœuds traversés (input + output, pas de lookup)
        assert len(result.path) == 2


class TestInferenceEngineEdgeCases:
    """Tests des cas limites."""

    def test_missing_field(self, simple_tree_structure: TreeStructure):
        """Test: Champ manquant retourne une erreur."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-1")  # Pas de cvss_score

        result = engine.evaluate(vuln)

        assert result.decision == "Error"
        assert result.error is not None
        assert "aucune condition" in result.error.lower()

    def test_empty_tree(self):
        """Test: Arbre vide retourne une erreur."""
        engine = InferenceEngine(TreeStructure())
        vuln = VulnerabilityInput(id="vuln-1", cvss_score=9.0)

        result = engine.evaluate(vuln)

        assert result.decision == "Error"
        assert "vide" in result.error.lower() or "invalide" in result.error.lower()

    def test_extra_fields_in_vulnerability(self, simple_tree_structure: TreeStructure):
        """Test: Les champs extra sont accessibles."""
        # Crée un arbre qui utilise un champ custom
        from app.schemas.tree import (
            ConditionOperator,
            EdgeSchema,
            NodeCondition,
            NodeSchema,
            NodeType,
        )

        nodes = [
            NodeSchema(
                id="input-custom",
                type=NodeType.INPUT,
                label="Custom Field",
                config={"field": "my_custom_field"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.EQUALS, value="yes", label="Yes"),
                    NodeCondition(operator=ConditionOperator.EQUALS, value="no", label="No"),
                ],
            ),
            NodeSchema(
                id="output-yes",
                type=NodeType.OUTPUT,
                label="Yes Output",
                config={"decision": "Proceed"},
            ),
            NodeSchema(
                id="output-no",
                type=NodeType.OUTPUT,
                label="No Output",
                config={"decision": "Skip"},
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="input-custom", target="output-yes", label="Yes"),
            EdgeSchema(id="e2", source="input-custom", target="output-no", label="No"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)

        engine = InferenceEngine(tree)
        vuln = VulnerabilityInput(
            id="vuln-1",
            extra={"my_custom_field": "yes"},
        )

        result = engine.evaluate(vuln)

        assert result.decision == "Proceed"

    def test_get_required_fields(self, tree_with_lookup: TreeStructure):
        """Test: get_required_fields retourne les champs nécessaires."""
        engine = InferenceEngine(tree_with_lookup)

        fields = engine.get_required_fields()

        assert "cvss_score" in fields
        assert "asset_id" in fields

    def test_get_lookup_tables(self, tree_with_lookup: TreeStructure):
        """Test: get_lookup_tables retourne les tables de lookup."""
        engine = InferenceEngine(tree_with_lookup)

        tables = engine.get_lookup_tables()

        assert "assets" in tables
