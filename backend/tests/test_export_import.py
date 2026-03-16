"""
Tests pour la fonctionnalité Decision-as-Code (export/import).
Tests unitaires sur les schemas Pydantic et la logique de nommage.
"""

import pytest
from pydantic import ValidationError

from app.schemas.tree import (
    TreeExportFile,
    TreeImportRequest,
    TreeExportData,
    TreeStructure,
)


# --- Tests schemas export ---


def test_export_file_valid():
    """Un fichier d'export valide est correctement parsé."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Test Tree",
            "description": "Un arbre de test",
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
    """Un fichier d'export avec field mapping est correctement parsé."""
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
    """model_dump_json() produit un JSON valide avec datetime sérialisé."""
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


# --- Tests schemas import ---


def test_import_valid():
    """Un fichier d'import valide est accepté."""
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
    """exported_at est accepté quand fourni."""
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
    """Un format inconnu est rejeté avec une erreur claire."""
    data = {
        "format": "wrong-format",
        "version": 1,
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    with pytest.raises(ValidationError, match="Format inconnu"):
        TreeImportRequest.model_validate(data)


def test_import_invalid_version():
    """Une version non supportée est rejetée."""
    data = {
        "format": "treevuln-decision-tree",
        "version": 99,
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    with pytest.raises(ValidationError, match="Version non supportée"):
        TreeImportRequest.model_validate(data)


def test_import_missing_format():
    """Un fichier sans le champ format est rejeté."""
    data = {
        "version": 1,
        "tree": {
            "name": "Test",
            "structure": {"nodes": [], "edges": [], "metadata": {}},
        },
    }
    with pytest.raises(ValidationError):
        TreeImportRequest.model_validate(data)


# --- Test round-trip ---


def test_round_trip_export_import(simple_tree_structure):
    """Un arbre exporté puis importé conserve sa structure."""
    # Simuler un export
    export_data = {
        "format": "treevuln-decision-tree",
        "version": 1,
        "exported_at": "2026-03-16T14:30:00Z",
        "tree": {
            "name": "Round Trip Test",
            "description": "Test de round-trip",
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

    # Valider comme export
    export_file = TreeExportFile.model_validate(export_data)

    # Ré-importer le JSON sérialisé
    import_data = export_file.model_dump()
    import_data["exported_at"] = export_file.exported_at.isoformat()
    import_req = TreeImportRequest.model_validate(import_data)

    # Vérifier que les données sont identiques
    assert import_req.tree.name == "Round Trip Test"
    assert import_req.tree.description == "Test de round-trip"
    assert len(import_req.tree.structure.nodes) == len(simple_tree_structure.nodes)
    assert len(import_req.tree.structure.edges) == len(simple_tree_structure.edges)
    assert import_req.tree.field_mapping is not None
    assert import_req.tree.field_mapping.fields[0].name == "cvss_score"


def test_export_no_field_mapping_duplication(simple_tree_structure):
    """Le field_mapping ne doit pas être dupliqué dans structure.metadata."""
    # Simuler un arbre avec field_mapping dans metadata
    structure_dict = simple_tree_structure.model_dump()
    structure_dict["metadata"]["field_mapping"] = {
        "fields": [{"name": "test", "type": "string"}],
        "source": "manual",
        "version": 1,
    }

    # Construire un export (simulation de ce que fait le service)
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

    # Vérifier : field_mapping dans tree.field_mapping, PAS dans structure.metadata
    assert export_file.tree.field_mapping is not None
    assert "field_mapping" not in export_file.tree.structure.metadata
