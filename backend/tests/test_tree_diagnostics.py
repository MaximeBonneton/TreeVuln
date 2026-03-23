"""Tests du module de diagnostic d'arbre."""

from app.schemas.diagnostic import DiagnosticItem, DiagnosticResult


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
