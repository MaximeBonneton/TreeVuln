"""
Tests for the Decision-as-Code feature (export/import).
Unit tests on Pydantic schemas and naming logic.
"""

import pytest
from pydantic import ValidationError

from app.schemas.tree import (
    TreeExportFile,
    TreeImportRequest,
    TreeExportData,
    TreeStructure,
)


# --- Export schema tests ---


def test_export_file_valid():
    """A valid export file is correctly parsed."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Test Tree",
            "description": "A test tree",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
            "field_mapping": None,
        },
    }
    export_file = TreeExportFile.model_validate(data)
    assert export_file.format == "treevuln-decision-tree"
    assert export_file.version == 1
    assert export_file.tree.name == "Test Tree"
    assert export_file.tree.field_mapping is None


def test_export_file_with_field_mapping():
    """An export file with field mapping is correctly parsed."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Test Tree",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
            "field_mapping": {
                "fields": [
                    {"name": "kev", "type": "boolean", "examples": [True, False]},
                ],
                "source": "csv_scan",
                "version": 3,
            },
        },
    }
    export_file = TreeExportFile.model_validate(data)
    assert export_file.tree.field_mapping is not None
    assert len(export_file.tree.field_mapping.fields) == 1
    assert export_file.tree.field_mapping.fields[0].name == "kev"


def test_export_file_serialization():
    """model_dump_json() produces valid JSON with serialized datetime."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
            "field_mapping": None,
        },
    }
    export_file = TreeExportFile.model_validate(data)
    json_str = export_file.model_dump_json(indent=2)
    assert '"treevuln-decision-tree"' in json_str
    assert '"2026-03-16' in json_str


# --- Import schema tests ---


def test_import_valid():
    """A valid import file is accepted."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "tree": {
            "name": "Imported Tree",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    import_req = TreeImportRequest.model_validate(data)
    assert import_req.tree.name == "Imported Tree"
    assert import_req.exported_at is None  # Optionnel


def test_import_with_exported_at():
    """exported_at is accepted when provided."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    import_req = TreeImportRequest.model_validate(data)
    assert import_req.exported_at is not None


def test_import_invalid_format():
    """An unknown format is rejected with a clear error."""
    data = {
        "format": "wrong-format",
        "version": 1,
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    with pytest.raises(ValidationError, match="Unknown format"):
        TreeImportRequest.model_validate(data)


def test_import_invalid_version():
    """An unsupported version is rejected."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 99,
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    with pytest.raises(ValidationError, match="Unsupported version"):
        TreeImportRequest.model_validate(data)


def test_import_missing_format():
    """A file without the format field is rejected."""
    data = {
        "version": 1,
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    with pytest.raises(ValidationError):
        TreeImportRequest.model_validate(data)


# --- Round-trip test ---


def test_round_trip_export_import(simple_tree_structure):
    """An exported then imported tree preserves its structure."""
    # Simulate an export
    export_data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Round Trip Test",
            "description": "Round-trip test",
            "structure": simple_tree_structure.model_dump(),
            "field_mapping": {
                "fields": [
                    {"name": "cvss_score", "type": "number"},
                ],
                "source": "manual",
                "version": 1,
            },
        },
    }

    # Validate as export
    export_file = TreeExportFile.model_validate(export_data)

    # Re-import the serialized JSON
    import_data = export_file.model_dump()
    import_data["exported_at"] = export_file.exported_at.isoformat()
    import_req = TreeImportRequest.model_validate(import_data)

    # Verify that the data is identical
    assert import_req.tree.name == "Round Trip Test"
    assert import_req.tree.description == "Round-trip test"
    assert len(import_req.tree.structure.nodes) == len(simple_tree_structure.nodes)
    assert len(import_req.tree.structure.edges) == len(simple_tree_structure.edges)
    assert import_req.tree.field_mapping is not None
    assert import_req.tree.field_mapping.fields[0].name == "cvss_score"


def test_export_no_field_mapping_duplication(simple_tree_structure):
    """The field_mapping must not be duplicated in structure.metadata."""
    # Simulate a tree with field_mapping in metadata
    structure_dict = simple_tree_structure.model_dump()
    structure_dict["metadata"]["field_mapping"] = {
        "fields": [{"name": "test", "type": "string"}],
        "source": "manual",
        "version": 1,
    }

    # Build an export (simulating what the service does)
    from copy import deepcopy

    structure_copy = deepcopy(structure_dict)
    field_mapping = structure_copy["metadata"].pop("field_mapping")

    export_data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Test",
            "structure": structure_copy,
            "field_mapping": field_mapping,
        },
    }

    export_file = TreeExportFile.model_validate(export_data)

    # Verify: field_mapping in tree.field_mapping, NOT in structure.metadata
    assert export_file.tree.field_mapping is not None
    assert "field_mapping" not in export_file.tree.structure.metadata


# ======================================================================
# S-17 — neutralisation de l'injection de formule CSV à l'export
# ======================================================================


class TestCsvFormulaInjectionNeutralized:
    """
    S-17 (Task 3.12) : les résultats d'évaluation contiennent des valeurs
    contrôlées par les sources externes (vuln_id d'un CSV importé, valeurs
    de champs). À l'export CSV, toute cellule commençant par un caractère
    de formule tableur (= + - @, tab, CR) doit être préfixée d'une
    apostrophe pour neutraliser l'interprétation par Excel/LibreOffice.
    """

    @staticmethod
    def _export(vuln_id: str) -> str:
        from app.engine.export import export_csv
        from app.schemas.evaluation import EvaluationResult

        result = EvaluationResult(vuln_id=vuln_id, decision="Track")
        return "".join(export_csv([result], include_path=False))

    def test_hyperlink_formula_is_neutralized(self):
        csv_out = self._export('=HYPERLINK("http://evil.example","CVE")')
        assert "'=HYPERLINK" in csv_out
        # La formule brute ne doit jamais apparaître en début de cellule
        assert '"=HYPERLINK' not in csv_out.replace("\"'=HYPERLINK", "")

    def test_all_formula_prefixes_are_neutralized(self):
        for prefix in ("=", "+", "-", "@", "\t", "\r"):
            csv_out = self._export(f"{prefix}cmd")
            assert f"'{prefix}cmd" in csv_out, (
                f"Le préfixe {prefix!r} doit être neutralisé par une apostrophe"
            )

    def test_normal_values_are_untouched(self):
        csv_out = self._export("CVE-2024-1234")
        assert "CVE-2024-1234" in csv_out
        assert "'CVE-2024-1234" not in csv_out
