"""
Tests for the inference engine.
"""

import pytest

from app.engine.inference import InferenceEngine
from app.engine.nodes import InputNode
from app.schemas.tree import (
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    TreeStructure,
)
from app.schemas.vulnerability import VulnerabilityInput


class TestInferenceEngine:
    """Tests for InferenceEngine."""

    def test_simple_tree_critical_cvss(self, simple_tree_structure: TreeStructure):
        """Test: CVSS >= 9.0 should return Act."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-1", cvss_score=9.5)

        result = engine.evaluate(vuln)

        assert result.decision == "Act"
        assert result.error is None
        assert len(result.path) == 2  # input + output

    def test_simple_tree_high_cvss(self, simple_tree_structure: TreeStructure):
        """Test: CVSS >= 7.0 and < 9.0 should return Attend."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-2", cvss_score=7.5)

        result = engine.evaluate(vuln)

        assert result.decision == "Attend"
        assert result.error is None

    def test_simple_tree_low_cvss(self, simple_tree_structure: TreeStructure):
        """Test: CVSS < 7.0 should return Track."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-3", cvss_score=4.0)

        result = engine.evaluate(vuln)

        assert result.decision == "Track"
        assert result.error is None

    def test_audit_trail_contains_all_nodes(self, simple_tree_structure: TreeStructure):
        """Test: The decision path contains all traversed nodes."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-4", cvss_score=9.0)

        result = engine.evaluate(vuln, include_path=True)

        assert len(result.path) == 2
        assert result.path[0].node_id == "input-cvss"
        assert result.path[0].value_found == 9.0
        assert result.path[0].condition_matched == "Critical"
        assert result.path[1].node_id == "output-act"

    def test_no_path_when_disabled(self, simple_tree_structure: TreeStructure):
        """Test: No path when include_path=False."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-5", cvss_score=9.0)

        result = engine.evaluate(vuln, include_path=False)

        assert result.decision == "Act"
        assert len(result.path) == 0


class TestInferenceEngineWithLookup:
    """Tests for InferenceEngine with lookup."""

    def test_lookup_critical_asset(self, tree_with_lookup: TreeStructure):
        """Test: High CVSS + critical asset -> Act."""
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
        """Test: High CVSS + high asset -> Attend."""
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
        """Test: High CVSS + normal asset -> Track."""
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
        """Test: Low CVSS does not go through the lookup."""
        engine = InferenceEngine(tree_with_lookup)
        vuln = VulnerabilityInput(
            id="vuln-4",
            cvss_score=5.0,
            asset_id="srv-prod-001",  # Critical asset but low CVSS
        )

        result = engine.evaluate(vuln)  # Pas de lookups fournis

        assert result.decision == "Track"
        # Only 2 nodes traversed (input + output, no lookup)
        assert len(result.path) == 2


class TestInferenceEngineEdgeCases:
    """Tests for edge cases."""

    def test_missing_field(self, simple_tree_structure: TreeStructure):
        """Test: Missing field returns an error."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-1")  # Pas de cvss_score

        result = engine.evaluate(vuln)

        assert result.decision == "Error"
        assert result.error is not None
        assert "no condition" in result.error.lower()

    def test_empty_tree(self):
        """Test: Empty tree returns an error."""
        engine = InferenceEngine(TreeStructure())
        vuln = VulnerabilityInput(id="vuln-1", cvss_score=9.0)

        result = engine.evaluate(vuln)

        assert result.decision == "Error"
        assert "empty" in result.error.lower() or "invalid" in result.error.lower()

    def test_extra_fields_in_vulnerability(self, simple_tree_structure: TreeStructure):
        """Test: Extra fields are accessible."""
        # Create a tree that uses a custom field
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
        """Test: get_required_fields returns the required fields."""
        engine = InferenceEngine(tree_with_lookup)

        fields = engine.get_required_fields()

        assert "cvss_score" in fields
        assert "asset_id" in fields

    def test_get_lookup_tables(self, tree_with_lookup: TreeStructure):
        """Test: get_lookup_tables returns the lookup tables."""
        engine = InferenceEngine(tree_with_lookup)

        tables = engine.get_lookup_tables()

        assert "assets" in tables


class TestE2SingleEdgeShortcut:
    """E-2: le raccourci "une seule edge" ne doit pas ignorer la condition matchée."""

    def test_single_edge_does_not_override_condition_match(self):
        """
        Arbre INPUT à 2 conditions (<9 -> handle-0, >=9 -> handle-1) avec une
        seule edge connectée sur handle-1 (vers Act). Une vuln qui matche la
        condition 0 (handle-0) ne doit PAS suivre l'unique edge disponible :
        aucune branche ne correspond, donc decision == "Error".
        """
        nodes = [
            NodeSchema(
                id="input-cvss",
                type=NodeType.INPUT,
                label="CVSS Score",
                config={"field": "cvss_score"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.LESS_THAN, value=9.0, label="Low"),
                    NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Critical"),
                ],
            ),
            NodeSchema(
                id="output-act",
                type=NodeType.OUTPUT,
                label="Act",
                config={"decision": "Act"},
            ),
        ]
        edges = [
            EdgeSchema(
                id="e1", source="input-cvss", target="output-act",
                source_handle="handle-1", label="Critical",
            ),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        engine = InferenceEngine(tree)
        vuln = VulnerabilityInput(id="v1", cvss_score=5.0)  # matche "Low" (handle-0)

        result = engine.evaluate(vuln)

        assert result.decision == "Error"


class TestE3RootSelection:
    """E-3: un nœud totalement déconnecté (orphelin) ne doit jamais devenir racine."""

    def test_orphan_output_placed_first_is_ignored(self):
        """
        Un OUTPUT orphelin (aucune edge) placé en tête de la liste des nœuds
        ne doit pas devenir la racine : la vraie racine (input-cvss, qui a
        une edge sortante) doit être utilisée pour l'évaluation.
        """
        nodes = [
            NodeSchema(
                id="orphan-output",
                type=NodeType.OUTPUT,
                label="Orphan",
                config={"decision": "WRONG"},
            ),
            NodeSchema(
                id="input-cvss",
                type=NodeType.INPUT,
                label="CVSS Score",
                config={"field": "cvss_score"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Critical"),
                ],
            ),
            NodeSchema(
                id="output-act",
                type=NodeType.OUTPUT,
                label="Act",
                config={"decision": "Act"},
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="input-cvss", target="output-act", label="Critical"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        engine = InferenceEngine(tree)

        assert engine.root_node_id == "input-cvss"

        vuln = VulnerabilityInput(id="v1", cvss_score=9.5)
        result = engine.evaluate(vuln)

        assert result.decision == "Act"


class TestE5ConditionIndexRouting:
    """E-5: le routing doit utiliser l'index de condition, pas une recherche par label."""

    def test_duplicate_labels_route_by_index_not_label(self):
        """
        Deux conditions portent le même label ("Match"), chacune reliée à un
        OUTPUT différent via un source_handle distinct (handle-0 / handle-1).
        Une vuln matchant la 2e condition doit atteindre le 2e OUTPUT, pas le
        premier (ce qui arriverait si le routing re-dérivait l'index en
        recherchant le premier label correspondant).
        """
        nodes = [
            NodeSchema(
                id="input-cvss",
                type=NodeType.INPUT,
                label="CVSS Score",
                config={"field": "cvss_score"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.LESS_THAN, value=5.0, label="Match"),
                    NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=5.0, label="Match"),
                ],
            ),
            NodeSchema(
                id="output-first",
                type=NodeType.OUTPUT,
                label="First",
                config={"decision": "First"},
            ),
            NodeSchema(
                id="output-second",
                type=NodeType.OUTPUT,
                label="Second",
                config={"decision": "Second"},
            ),
        ]
        edges = [
            EdgeSchema(id="e1", source="input-cvss", target="output-first", source_handle="handle-0", label="Match"),
            EdgeSchema(id="e2", source="input-cvss", target="output-second", source_handle="handle-1", label="Match"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        engine = InferenceEngine(tree)
        vuln = VulnerabilityInput(id="v1", cvss_score=9.0)  # matche la condition d'index 1

        result = engine.evaluate(vuln)

        assert result.decision == "Second"


class TestE4TypeCoercion:
    """E-4: _evaluate_simple doit coercer les types avant de comparer eq/neq.

    Sans coercition, une valeur texte issue d'un CSV ("9.8") ne matche
    jamais une condition numérique (9.8), ce qui fausse silencieusement
    la décision.
    """

    def _make_node(self) -> InputNode:
        """Construit un InputNode minimal pour tester _evaluate_simple directement."""
        schema = NodeSchema(
            id="input-x",
            type=NodeType.INPUT,
            label="X",
            config={"field": "x"},
            conditions=[NodeCondition(operator=ConditionOperator.EQUALS, value="x", label="l")],
        )
        return InputNode(schema)

    def test_string_number_equals_float(self):
        """"9.8" == 9.8 doit matcher (coercition float)."""
        node = self._make_node()
        assert node._evaluate_simple("9.8", ConditionOperator.EQUALS, 9.8) is True

    def test_string_bool_equals_bool(self):
        """"true" == True doit matcher (coercition booléenne)."""
        node = self._make_node()
        assert node._evaluate_simple("true", ConditionOperator.EQUALS, True) is True

    def test_string_bool_case_insensitive(self):
        """"FALSE" == False doit matcher, insensible à la casse."""
        node = self._make_node()
        assert node._evaluate_simple("FALSE", ConditionOperator.EQUALS, False) is True

    def test_string_equals_string_still_works(self):
        """Le cas texte/texte classique reste inchangé."""
        node = self._make_node()
        assert node._evaluate_simple("High", ConditionOperator.EQUALS, "High") is True
        assert node._evaluate_simple("High", ConditionOperator.EQUALS, "Low") is False

    def test_not_equals_with_coercion(self):
        """NOT_EQUALS doit bénéficier de la même coercition."""
        node = self._make_node()
        assert node._evaluate_simple("9.8", ConditionOperator.NOT_EQUALS, 9.8) is False
        assert node._evaluate_simple("9.9", ConditionOperator.NOT_EQUALS, 9.8) is True
