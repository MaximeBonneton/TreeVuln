"""
Tests for CVSS vector parsing.
"""

import pytest

from app.engine.cvss import (
    detect_cvss_version,
    get_cvss_field_definitions,
    is_cvss_field,
    parse_cvss_vector,
)


class TestDetectCvssVersion:
    """Tests for detect_cvss_version function."""

    def test_detect_31(self):
        """Should detect CVSS 3.1 version."""
        assert detect_cvss_version("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H") == "3.1"

    def test_detect_30_as_31(self):
        """Should treat CVSS 3.0 as 3.1."""
        assert detect_cvss_version("CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H") == "3.1"

    def test_detect_40(self):
        """Should detect CVSS 4.0 version."""
        assert detect_cvss_version("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N") == "4.0"

    def test_detect_case_insensitive(self):
        """Should be case insensitive."""
        assert detect_cvss_version("cvss:3.1/av:n/ac:l/pr:n/ui:n/s:c/c:h/i:h/a:h") == "3.1"

    def test_detect_unknown(self):
        """Should return None for unknown formats."""
        assert detect_cvss_version("AV:N/AC:L") is None
        assert detect_cvss_version("") is None
        assert detect_cvss_version("CVSS:2.0/AV:N") is None

    def test_detect_none_input(self):
        """Should handle None input."""
        assert detect_cvss_version(None) is None

    def test_detect_non_string_input(self):
        """Should handle non-string input."""
        assert detect_cvss_version(123) is None


class TestParseCvssVector:
    """Tests for parse_cvss_vector function."""

    def test_parse_31_full(self):
        """Should parse all CVSS 3.1 base metrics."""
        vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
        result = parse_cvss_vector(vector)

        assert result["cvss_av"] == "Network"
        assert result["cvss_ac"] == "Low"
        assert result["cvss_pr"] == "None"
        assert result["cvss_ui"] == "None"
        assert result["cvss_s"] == "Changed"
        assert result["cvss_c"] == "High"
        assert result["cvss_i"] == "High"
        assert result["cvss_a"] == "High"

    def test_parse_31_partial_impact(self):
        """Should parse CVSS 3.1 with partial impact values."""
        vector = "CVSS:3.1/AV:L/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:N"
        result = parse_cvss_vector(vector)

        assert result["cvss_av"] == "Local"
        assert result["cvss_ac"] == "High"
        assert result["cvss_pr"] == "Low"
        assert result["cvss_ui"] == "Required"
        assert result["cvss_s"] == "Unchanged"
        assert result["cvss_c"] == "Low"
        assert result["cvss_i"] == "Low"
        assert result["cvss_a"] == "None"

    def test_parse_31_physical_adjacent(self):
        """Should parse Physical and Adjacent attack vectors."""
        vector = "CVSS:3.1/AV:P/AC:L/PR:H/UI:N/S:U/C:N/I:N/A:H"
        result = parse_cvss_vector(vector)

        assert result["cvss_av"] == "Physical"
        assert result["cvss_pr"] == "High"

        vector2 = "CVSS:3.1/AV:A/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"
        result2 = parse_cvss_vector(vector2)
        assert result2["cvss_av"] == "Adjacent"

    def test_parse_40_full(self):
        """Should parse CVSS 4.0 metrics."""
        vector = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:L/SI:L/SA:N"
        result = parse_cvss_vector(vector)

        assert result["cvss_av"] == "Network"
        assert result["cvss_ac"] == "Low"
        assert result["cvss_at"] == "None"
        assert result["cvss_pr"] == "None"
        assert result["cvss_ui"] == "None"
        assert result["cvss_vc"] == "High"
        assert result["cvss_vi"] == "High"
        assert result["cvss_va"] == "High"
        assert result["cvss_sc"] == "Low"
        assert result["cvss_si"] == "Low"
        assert result["cvss_sa"] == "None"

    def test_parse_40_with_attack_requirements(self):
        """Should parse CVSS 4.0 Attack Requirements metric."""
        vector = "CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N"
        result = parse_cvss_vector(vector)

        assert result["cvss_at"] == "Present"

    def test_parse_40_user_interaction_values(self):
        """Should parse CVSS 4.0 User Interaction values (Passive/Active)."""
        vector = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N"
        result = parse_cvss_vector(vector)
        assert result["cvss_ui"] == "Passive"

        vector2 = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N"
        result2 = parse_cvss_vector(vector2)
        assert result2["cvss_ui"] == "Active"

    def test_parse_empty_vector(self):
        """Should return empty dict for empty or invalid vectors."""
        assert parse_cvss_vector("") == {}
        assert parse_cvss_vector(None) == {}
        assert parse_cvss_vector("invalid") == {}

    def test_parse_case_insensitive(self):
        """Should be case insensitive."""
        vector = "cvss:3.1/av:n/ac:l/pr:n/ui:n/s:c/c:h/i:h/a:h"
        result = parse_cvss_vector(vector)

        assert result["cvss_av"] == "Network"
        assert result["cvss_c"] == "High"

    def test_parse_with_extra_whitespace(self):
        """Should handle vectors with extra whitespace."""
        vector = " CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H "
        result = parse_cvss_vector(vector)

        assert result["cvss_av"] == "Network"


class TestIsCvssField:
    """Tests for is_cvss_field function."""

    def test_valid_cvss_fields(self):
        """Should return True for valid CVSS metric fields."""
        assert is_cvss_field("cvss_av") is True
        assert is_cvss_field("cvss_ac") is True
        assert is_cvss_field("cvss_pr") is True
        assert is_cvss_field("cvss_ui") is True
        assert is_cvss_field("cvss_s") is True
        assert is_cvss_field("cvss_c") is True
        assert is_cvss_field("cvss_i") is True
        assert is_cvss_field("cvss_a") is True

    def test_cvss_40_fields(self):
        """Should return True for CVSS 4.0 specific fields."""
        assert is_cvss_field("cvss_at") is True
        assert is_cvss_field("cvss_vc") is True
        assert is_cvss_field("cvss_vi") is True
        assert is_cvss_field("cvss_va") is True
        assert is_cvss_field("cvss_sc") is True
        assert is_cvss_field("cvss_si") is True
        assert is_cvss_field("cvss_sa") is True

    def test_excluded_cvss_fields(self):
        """Should return False for cvss_score and cvss_vector."""
        assert is_cvss_field("cvss_score") is False
        assert is_cvss_field("cvss_vector") is False

    def test_non_cvss_fields(self):
        """Should return False for non-CVSS fields."""
        assert is_cvss_field("epss_score") is False
        assert is_cvss_field("kev") is False
        assert is_cvss_field("asset_id") is False
        assert is_cvss_field("cve_id") is False

    def test_unknown_cvss_prefix_fields(self):
        """Should return False for unknown cvss_ prefixed fields."""
        assert is_cvss_field("cvss_unknown") is False
        assert is_cvss_field("cvss_xyz") is False


class TestGetCvssFieldDefinitions:
    """Tests for get_cvss_field_definitions function."""

    def test_returns_field_definitions(self):
        """Should return a list of FieldDefinition objects."""
        definitions = get_cvss_field_definitions()

        assert len(definitions) > 0
        assert all(hasattr(d, "name") for d in definitions)
        assert all(hasattr(d, "label") for d in definitions)
        assert all(hasattr(d, "type") for d in definitions)

    def test_contains_31_fields(self):
        """Should contain CVSS 3.1 base metric fields."""
        definitions = get_cvss_field_definitions()
        field_names = {d.name for d in definitions}

        assert "cvss_av" in field_names
        assert "cvss_ac" in field_names
        assert "cvss_pr" in field_names
        assert "cvss_ui" in field_names
        assert "cvss_s" in field_names
        assert "cvss_c" in field_names
        assert "cvss_i" in field_names
        assert "cvss_a" in field_names

    def test_contains_40_specific_fields(self):
        """Should contain CVSS 4.0 specific fields."""
        definitions = get_cvss_field_definitions()
        field_names = {d.name for d in definitions}

        assert "cvss_at" in field_names
        assert "cvss_vc" in field_names
        assert "cvss_vi" in field_names
        assert "cvss_va" in field_names
        assert "cvss_sc" in field_names
        assert "cvss_si" in field_names
        assert "cvss_sa" in field_names

    def test_no_duplicate_field_names(self):
        """Should not have duplicate field names."""
        definitions = get_cvss_field_definitions()
        field_names = [d.name for d in definitions]

        assert len(field_names) == len(set(field_names))

    def test_fields_have_labels(self):
        """All fields should have meaningful labels."""
        definitions = get_cvss_field_definitions()

        for definition in definitions:
            assert definition.label is not None
            assert len(definition.label) > 0
            assert "CVSS" in definition.label

    def test_fields_have_examples(self):
        """All fields should have examples."""
        definitions = get_cvss_field_definitions()

        for definition in definitions:
            assert len(definition.examples) > 0

    def test_fields_are_string_type(self):
        """All CVSS metric fields should be string type."""
        definitions = get_cvss_field_definitions()

        for definition in definitions:
            assert definition.type.value == "string"
