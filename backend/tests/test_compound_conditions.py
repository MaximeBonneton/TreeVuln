"""
Tests for compound conditions (AND/OR) with multi-field support.
"""

import pytest

from app.engine.inference import InferenceEngine
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class TestCompoundConditionsAND:
    """Tests for AND conditions."""

    def test_and_both_match(self, compound_condition_tree: TreeStructure):
        """AND: both criteria satisfied -> AND branch."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-1",
            extra={"cvss_av": "Network", "cvss_ac": "Low"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Act"

    def test_and_one_fails(self, compound_condition_tree: TreeStructure):
        """AND: one criterion fails -> falls through to the next condition (OR)."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-2",
            extra={"cvss_av": "Network", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        # AND échoue (ac!=Low), mais OR matche (av=Network)
        assert result.decision == "Attend"


class TestCompoundConditionsOR:
    """Tests for OR conditions."""

    def test_or_first_matches(self, compound_condition_tree: TreeStructure):
        """OR: first criterion satisfied -> OR branch."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-3",
            extra={"cvss_av": "Network", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Attend"

    def test_or_second_matches(self, compound_condition_tree: TreeStructure):
        """OR: only the second criterion satisfied -> OR branch."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-4",
            extra={"cvss_av": "Local", "cvss_ac": "Low"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Attend"

    def test_or_none_matches(self, compound_condition_tree: TreeStructure):
        """OR: no criterion satisfied -> next branch (Other)."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-5",
            extra={"cvss_av": "Local", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        assert result.decision == "Track"


class TestCompoundRetrocompatibility:
    """Tests for backward compatibility with simple mode."""

    def test_simple_condition_still_works(self, simple_tree_structure: TreeStructure):
        """Simple conditions (legacy mode) still work."""
        engine = InferenceEngine(simple_tree_structure)
        vuln = VulnerabilityInput(id="vuln-6", cvss_score=9.5)

        result = engine.evaluate(vuln)
        assert result.decision == "Act"

    def test_mixed_simple_and_compound(self, compound_condition_tree: TreeStructure):
        """The compound_condition_tree mixes compound and simple modes (Other)."""
        engine = InferenceEngine(compound_condition_tree)
        vuln = VulnerabilityInput(
            id="vuln-7",
            extra={"cvss_av": "Physical", "cvss_ac": "High"},
        )

        result = engine.evaluate(vuln)
        # Ni AND ni OR ne matchent -> fallback sur "Other" (IS_NOT_NULL)
        assert result.decision == "Track"
