"""
Tests for the inference engine.
"""

import concurrent.futures
import logging
import time

import pytest

from app.engine import nodes as nodes_module
from app.engine.inference import InferenceEngine
from app.engine.nodes import InputNode, _safe_regex_match, _values_equal
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


class TestE4RestrictCoercionToCrossType:
    """E-4 (correctif de régression) : _values_equal ne doit coercer en
    float QUE lorsque les deux opérandes ont des types Python différents
    (str vs int/float/bool). Si les DEUX sont des chaînes, la comparaison
    doit rester une comparaison de texte stricte, sinon "01" matche "1"
    et "nan" ne matche plus lui-même (float('nan') != float('nan'))."""

    def test_two_distinct_strings_that_look_numeric_do_not_match(self):
        """"1" et "01" sont deux textes distincts : ne doivent pas matcher."""
        assert _values_equal("1", "01") is False

    def test_two_distinct_strings_with_different_float_repr_do_not_match(self):
        """"1.0" et "1" sont deux textes distincts : ne doivent pas matcher."""
        assert _values_equal("1.0", "1") is False

    def test_identical_nan_strings_match_as_text(self):
        """"nan" == "nan" doit matcher en tant que texte (pas de coercition
        float, qui casserait l'égalité car float('nan') != float('nan'))."""
        assert _values_equal("nan", "nan") is True

    def test_cross_type_string_number_still_coerces(self):
        """Intention d'origine de E-4 préservée : "9.8" (str, ex. issu d'un
        CSV) doit toujours matcher 9.8 (float, valeur de condition)."""
        assert _values_equal("9.8", 9.8) is True

    def test_cross_type_string_bool_still_coerces(self):
        """Intention d'origine de E-4 préservée : "true" (str) doit
        toujours matcher True (bool)."""
        assert _values_equal("true", True) is True

    def test_two_strings_equal_still_match(self):
        """Comparaison texte/texte classique toujours fonctionnelle."""
        assert _values_equal("High", "High") is True

    def test_two_numbers_equal_still_match(self):
        """Comparaison numérique/numérique classique toujours fonctionnelle."""
        assert _values_equal(9.8, 9.8) is True


class TestB12ExceptionGuards:
    """B-12: les exceptions natives (ValueError/IndexError) ne doivent jamais
    remonter comme des erreurs non gérées (500) mais être converties en
    decision == "Error"."""

    def test_gt_on_non_numeric_value_returns_error_not_exception(self):
        """Une condition gt sur un champ texte ne doit pas lever ValueError."""
        nodes = [
            NodeSchema(
                id="input-x",
                type=NodeType.INPUT,
                label="X",
                config={"field": "x"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.GREATER_THAN, value=9, label="High"),
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
            EdgeSchema(id="e1", source="input-x", target="output-act", label="High"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        engine = InferenceEngine(tree)
        vuln = VulnerabilityInput(id="v1", extra={"x": "haute"})

        result = engine.evaluate(vuln)

        assert result.decision == "Error"

    def test_lookup_default_branch_out_of_range_does_not_crash(self):
        """Un default_branch hors bornes sur un LookupNode ne doit pas lever IndexError."""
        nodes = [
            NodeSchema(
                id="lookup-asset",
                type=NodeType.LOOKUP,
                label="Asset",
                config={
                    "lookup_table": "assets",
                    "lookup_key": "asset_id",
                    "lookup_field": "criticality",
                    "default_branch": 5,
                },
                conditions=[
                    NodeCondition(operator=ConditionOperator.EQUALS, value="Critical", label="Critical"),
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
            EdgeSchema(id="e1", source="lookup-asset", target="output-act", label="Critical"),
        ]
        tree = TreeStructure(nodes=nodes, edges=edges)
        engine = InferenceEngine(tree)
        vuln = VulnerabilityInput(id="v1", asset_id="unknown-asset")

        result = engine.evaluate(vuln)  # pas de lookups fournis -> asset introuvable

        assert result.decision == "Error"


# ======================================================================
# S-13b — protection ReDoS qui ne casse pas durablement le pool de threads
# ======================================================================


class TestRegexReDoSProtection:
    """
    Un utilisateur authentifié (y compris rôle operator) contrôle à la
    fois le pattern regex ET le texte testé via les endpoints
    preview/diagnose.

    Reprise revue 2026-07-16 (#2, #6, #8) : la protection repose désormais
    sur le module tiers `regex` et son paramètre `timeout=`, qui interrompt
    RÉELLEMENT un match catastrophique (sa boucle C vérifie l'horloge
    périodiquement, contrairement au module standard `re` qui ne rend
    jamais la main). Conséquences testées ici :
    - plus de plafond de longueur de texte qui transformait silencieusement
      un match en no-match (#2) ;
    - plus de pool de threads partagé, donc plus de course au submit (#6)
      ni de threads zombies à régénérer (#8).
    """

    def test_long_text_still_matches(self):
        """#2 : un champ texte long (> 1000 caractères, ancien plafond) doit
        continuer de matcher — l'ancien cap retournait silencieusement False
        et faussait la décision SSVC."""
        text = "x" * 1500 + " remote code execution risk"
        assert _safe_regex_match("remote code execution", text) is True

    def test_long_text_without_match_returns_false(self):
        assert _safe_regex_match("nonexistent-pattern", "x" * 5000) is False

    # Pattern réellement catastrophique POUR LE MODULE `regex` (vérifié
    # empiriquement) : celui-ci optimise les cas classiques comme (a+)+$
    # (réponse en microsecondes), mais (a|aa)+$ force un backtracking
    # exponentiel que seul le timeout peut interrompre.
    _CATASTROPHIC_PATTERN = "(a|aa)+$"
    _CATASTROPHIC_TEXT = "a" * 35 + "!"

    def test_catastrophic_pattern_times_out_and_returns_false(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ):
        """#8 : un vrai pattern à backtracking catastrophique est interrompu
        par le timeout du module `regex` (pas de thread zombie), retourne
        False et laisse une trace en log."""
        monkeypatch.setattr(nodes_module, "_REGEX_TIMEOUT_SECONDS", 0.2)

        with caplog.at_level(logging.WARNING, logger="app.engine.nodes"):
            start = time.monotonic()
            result = _safe_regex_match(self._CATASTROPHIC_PATTERN, self._CATASTROPHIC_TEXT)
            elapsed = time.monotonic() - start

        assert result is False
        # Le timeout a réellement interrompu le calcul (marge large pour CI)
        assert elapsed < 1.5
        assert any("timed out" in record.message for record in caplog.records)

    def test_normal_regex_still_works_after_a_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Après un timeout, les évaluations suivantes restent correctes
        (plus d'état partagé à réparer : chaque appel est indépendant)."""
        monkeypatch.setattr(nodes_module, "_REGEX_TIMEOUT_SECONDS", 0.2)
        assert _safe_regex_match(self._CATASTROPHIC_PATTERN, self._CATASTROPHIC_TEXT) is False
        assert _safe_regex_match(r"^CVE-\d{4}-\d+$", "CVE-2024-1234") is True
        assert _safe_regex_match(r"^CVE-\d{4}-\d+$", "not-a-cve") is False

    def test_concurrent_mixed_patterns_do_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """#6 : des évaluations concurrentes mêlant patterns valides et
        catastrophiques ne doivent ni lever d'exception (l'ancien code
        pouvait lever RuntimeError sur un pool shutdown par un timeout
        concurrent) ni fausser les résultats des patterns valides."""
        monkeypatch.setattr(nodes_module, "_REGEX_TIMEOUT_SECONDS", 0.2)

        def run(i: int) -> bool:
            if i % 2:
                return _safe_regex_match(self._CATASTROPHIC_PATTERN, self._CATASTROPHIC_TEXT)
            return _safe_regex_match(r"^\d+$", "12345")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run, range(16)))

        assert all(results[i] is True for i in range(0, 16, 2))
        assert all(results[i] is False for i in range(1, 16, 2))

    def test_invalid_pattern_returns_false(self):
        """Un pattern regex syntaxiquement invalide reste géré sans exception."""
        assert _safe_regex_match("(unclosed", "anything") is False

    def test_pattern_too_long_is_rejected(self):
        long_pattern = "a" * (nodes_module._MAX_REGEX_PATTERN_LENGTH + 1)
        assert _safe_regex_match(long_pattern, "aaa") is False
