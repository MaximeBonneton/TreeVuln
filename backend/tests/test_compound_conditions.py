"""
Tests des conditions composées (AND/OR) avec multi-champs.
"""

import pytest

from app.engine.inference import InferenceEngine
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class TestCompoundConditionsAND:
    """Tests pour les conditions AND."""

    def test_and_both_match(self, compound_condition_tree: TreeStructure):
        """AND: les deux critères satisfaits -> branche AND."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-1",
            extra={"cvss_av": "Network", "cvss_ac": "Low"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Act"

    def test_and_one_fails(self, compound_condition_tree: TreeStructure):
        """AND: un critère échoue -> passe à la condition suivante (OR)."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-2",
            extra={"cvss_av": "Network", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        # AND échoue (ac!=Low), mais OR matche (av=Network)
        assert result.decision == "Attend"


class TestCompoundConditionsOR:
    """Tests pour les conditions OR."""

    def test_or_first_matches(self, compound_condition_tree: TreeStructure):
        """OR: premier critère satisfait -> branche OR."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-3",
            extra={"cvss_av": "Network", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Attend"

    def test_or_second_matches(self, compound_condition_tree: TreeStructure):
        """OR: seul le second critère satisfait -> branche OR."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-4",
            extra={"cvss_av": "Local", "cvss_ac": "Low"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Attend"

    def test_or_none_matches(self, compound_condition_tree: TreeStructure):
        """OR: aucun critère satisfait -> branche suivante (Other)."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-5",
            extra={"cvss_av": "Local", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Track"


class TestCompoundRetrocompatibility:
    """Tests de rétrocompatibilité avec le mode simple."""

    def test_simple_condition_still_works(self, simple_tree_structure: TreeStructure):
        """Les conditions simples (mode legacy) fonctionnent toujours."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-6", cvss_score=9.5)

        result = engine.evaluate(vuln)
        assert result.decision == "Act"

    def test_mixed_simple_and_compound(self, compound_condition_tree: TreeStructure):
        """L'arbre compound_condition_tree mélange mode composé et simple (Other)."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-7",
            extra={"cvss_av": "Physical", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        # Ni AND ni OR ne matchent -> fallback sur "Other" (IS_NOT_NULL)
        assert result.decision == "Track"
