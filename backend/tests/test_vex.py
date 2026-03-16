"""
Tests pour le générateur VEX CycloneDX 1.6.
"""

import pytest

from app.engine.vex import (
    VALID_VEX_JUSTIFICATIONS,
    VALID_VEX_STATUSES,
    _build_detail,
    _get_vex_config,
    build_vex_document,
)
from app.schemas.evaluation import DecisionPath, EvaluationResult


# --- Fixtures ---


def _make_result(
    vuln_id: str = "CVE-2024-1234",
    decision: str = "Act",
    error: str | None = None,
    path: list[DecisionPath] | None = None,
) -> EvaluationResult:
    """Helper pour créer un EvaluationResult de test."""
    if path is None:
        path = [
            DecisionPath(
                node_id="input-kev",
                node_label="Exploitation",
                node_type="input",
                field_evaluated="kev",
                value_found=True,
                condition_matched="Active",
            ),
            DecisionPath(
                node_id="output-act",
                node_label="Act",
                node_type="output",
                field_evaluated=None,
                value_found="Act",
                condition_matched=None,
            ),
        ]
    return EvaluationResult(
        vuln_id=vuln_id,
        decision=decision,
        decision_color="#dc2626",
        path=path,
        error=error,
    )


def _make_tree_structure(
    vex_status: str | None = "exploitable",
    vex_justification: str | None = None,
    output_node_id: str = "output-act",
) -> dict:
    """Helper pour créer une structure d'arbre avec vex_status."""
    config: dict = {"decision": "Act", "color": "#dc2626"}
    if vex_status:
        config["vex_status"] = vex_status
    if vex_justification:
        config["vex_justification"] = vex_justification
    return {
        "nodes": [
            {
                "id": "input-kev",
                "type": "input",
                "label": "Exploitation",
                "config": {"field": "kev"},
            },
            {
                "id": output_node_id,
                "type": "output",
                "label": "Act",
                "config": config,
            },
        ],
        "edges": [],
    }


# --- Tests _build_detail ---


class TestBuildDetail:
    def test_simple_path(self):
        """Construit un détail depuis un audit trail simple."""
        result = _make_result()
        detail = _build_detail(result)
        assert "Exploitation: kev=True (Active)" in detail
        assert "Decision: Act" in detail
        assert "\u2192" in detail  # Flèche unicode

    def test_multi_step_path(self):
        """Construit un détail avec plusieurs étapes."""
        result = _make_result(
            path=[
                DecisionPath(
                    node_id="input-kev",
                    node_label="Exploitation",
                    node_type="input",
                    field_evaluated="kev",
                    value_found=True,
                    condition_matched="Active",
                ),
                DecisionPath(
                    node_id="input-epss",
                    node_label="Automatable",
                    node_type="input",
                    field_evaluated="epss_score",
                    value_found=0.5,
                    condition_matched="Yes",
                ),
                DecisionPath(
                    node_id="output-act",
                    node_label="Act",
                    node_type="output",
                    field_evaluated=None,
                    value_found="Act",
                    condition_matched=None,
                ),
            ]
        )
        detail = _build_detail(result)
        assert "Exploitation: kev=True (Active)" in detail
        assert "Automatable: epss_score=0.5 (Yes)" in detail
        assert "Decision: Act" in detail

    def test_node_without_field(self):
        """Un nœud sans field_evaluated mais avec condition_matched est inclus."""
        result = _make_result(
            path=[
                DecisionPath(
                    node_id="eq-1",
                    node_label="Risk Score",
                    node_type="equation",
                    field_evaluated=None,
                    value_found=85.5,
                    condition_matched="High",
                ),
                DecisionPath(
                    node_id="output-act",
                    node_label="Act",
                    node_type="output",
                    field_evaluated=None,
                    value_found="Act",
                    condition_matched=None,
                ),
            ]
        )
        detail = _build_detail(result)
        assert "Risk Score: 85.5 (High)" in detail

    def test_empty_path(self):
        """Un path vide retourne une chaîne vide."""
        result = _make_result(path=[])
        detail = _build_detail(result)
        assert detail == ""


# --- Tests _get_vex_config ---


class TestGetVexConfig:
    def test_finds_status(self):
        """Trouve le vex_status du nœud output."""
        result = _make_result()
        tree = _make_tree_structure(vex_status="exploitable")
        status, justification = _get_vex_config(result, tree)
        assert status == "exploitable"
        assert justification is None

    def test_finds_status_and_justification(self):
        """Trouve le vex_status et la justification."""
        result = _make_result(
            decision="Not Affected",
            path=[
                DecisionPath(
                    node_id="output-na",
                    node_label="Not Affected",
                    node_type="output",
                    field_evaluated=None,
                    value_found="Not Affected",
                    condition_matched=None,
                ),
            ],
        )
        tree = {
            "nodes": [
                {
                    "id": "output-na",
                    "type": "output",
                    "config": {
                        "decision": "Not Affected",
                        "vex_status": "not_affected",
                        "vex_justification": "code_not_reachable",
                    },
                }
            ]
        }
        status, justification = _get_vex_config(result, tree)
        assert status == "not_affected"
        assert justification == "code_not_reachable"

    def test_no_vex_status(self):
        """Retourne None si pas de vex_status dans la config."""
        result = _make_result()
        tree = _make_tree_structure(vex_status=None)
        status, justification = _get_vex_config(result, tree)
        assert status is None

    def test_empty_path(self):
        """Retourne None si le path est vide."""
        result = _make_result(path=[])
        tree = _make_tree_structure()
        status, justification = _get_vex_config(result, tree)
        assert status is None

    def test_node_not_found(self):
        """Retourne None si le nœud output n'est pas dans l'arbre."""
        result = _make_result()
        tree = {"nodes": []}
        status, justification = _get_vex_config(result, tree)
        assert status is None


# --- Tests build_vex_document ---


class TestBuildVexDocument:
    def test_valid_document_structure(self):
        """Produit un document CycloneDX valide."""
        results = [_make_result()]
        tree = _make_tree_structure(vex_status="exploitable")

        doc, warnings = build_vex_document(results, tree, "MyApp", "1.0.0")

        assert doc["bomFormat"] == "CycloneDX"
        assert doc["specVersion"] == "1.6"
        assert doc["version"] == 1
        assert doc["serialNumber"].startswith("urn:uuid:")
        assert doc["metadata"]["component"]["name"] == "MyApp"
        assert doc["metadata"]["component"]["version"] == "1.0.0"
        assert doc["metadata"]["tools"]["components"][0]["name"] == "TreeVuln"
        assert len(doc["vulnerabilities"]) == 1
        assert warnings == []

    def test_timestamp_format(self):
        """Le timestamp utilise le suffixe Z."""
        doc, _ = build_vex_document([], {}, "App", "1.0")
        assert doc["metadata"]["timestamp"].endswith("Z")

    def test_exploitable_no_justification(self):
        """Un statut exploitable n'a pas de justification."""
        results = [_make_result()]
        tree = _make_tree_structure(vex_status="exploitable")

        doc, _ = build_vex_document(results, tree, "App", "1.0")

        vuln = doc["vulnerabilities"][0]
        assert vuln["analysis"]["state"] == "exploitable"
        assert "justification" not in vuln["analysis"]

    def test_not_affected_with_justification(self):
        """Un statut not_affected inclut la justification du nœud."""
        result = _make_result(
            decision="Not Affected",
            path=[
                DecisionPath(
                    node_id="output-na",
                    node_label="Not Affected",
                    node_type="output",
                    field_evaluated=None,
                    value_found="Not Affected",
                    condition_matched=None,
                ),
            ],
        )
        tree = {
            "nodes": [
                {
                    "id": "output-na",
                    "type": "output",
                    "config": {
                        "vex_status": "not_affected",
                        "vex_justification": "code_not_reachable",
                    },
                }
            ]
        }

        doc, _ = build_vex_document([result], tree, "App", "1.0")

        vuln = doc["vulnerabilities"][0]
        assert vuln["analysis"]["state"] == "not_affected"
        assert vuln["analysis"]["justification"] == "code_not_reachable"

    def test_not_affected_default_justification(self):
        """Un statut not_affected sans justification utilise requires_environment."""
        result = _make_result(
            decision="Not Affected",
            path=[
                DecisionPath(
                    node_id="output-na",
                    node_label="Not Affected",
                    node_type="output",
                    field_evaluated=None,
                    value_found="Not Affected",
                    condition_matched=None,
                ),
            ],
        )
        tree = {
            "nodes": [
                {
                    "id": "output-na",
                    "type": "output",
                    "config": {"vex_status": "not_affected"},
                }
            ]
        }

        doc, _ = build_vex_document([result], tree, "App", "1.0")

        assert doc["vulnerabilities"][0]["analysis"]["justification"] == "requires_environment"

    def test_error_excluded_with_warning(self):
        """Un résultat en erreur est exclu avec un warning."""
        results = [_make_result(error="Missing field")]
        tree = _make_tree_structure()

        doc, warnings = build_vex_document(results, tree, "App", "1.0")

        assert len(doc["vulnerabilities"]) == 0
        assert any("evaluation error" in w for w in warnings)

    def test_no_vuln_id_excluded(self):
        """Un résultat sans vuln_id est exclu."""
        results = [_make_result(vuln_id=None)]
        tree = _make_tree_structure()

        doc, warnings = build_vex_document(results, tree, "App", "1.0")

        assert len(doc["vulnerabilities"]) == 0
        assert any("without id" in w for w in warnings)

    def test_no_vex_status_excluded_with_warning(self):
        """Un résultat sans vex_status est exclu avec un warning."""
        results = [_make_result()]
        tree = _make_tree_structure(vex_status=None)

        doc, warnings = build_vex_document(results, tree, "App", "1.0")

        assert len(doc["vulnerabilities"]) == 0
        assert any("no vex_status" in w for w in warnings)

    def test_invalid_vex_status_excluded(self):
        """Un vex_status invalide est exclu avec un warning."""
        results = [_make_result()]
        tree = _make_tree_structure(vex_status="invalid_status")

        doc, warnings = build_vex_document(results, tree, "App", "1.0")

        assert len(doc["vulnerabilities"]) == 0
        assert any("invalid vex_status" in w for w in warnings)

    def test_empty_vulnerabilities(self):
        """Un document vide est valide."""
        doc, warnings = build_vex_document([], {}, "App", "1.0")

        assert doc["vulnerabilities"] == []
        assert warnings == []

    def test_product_name_version_in_metadata(self):
        """Le nom et la version du produit sont dans les métadonnées."""
        doc, _ = build_vex_document([], {}, "Mon Produit", "2.1.0")

        assert doc["metadata"]["component"]["name"] == "Mon Produit"
        assert doc["metadata"]["component"]["version"] == "2.1.0"

    def test_all_included(self):
        """Toutes les vulns avec vex_status sont incluses."""
        results = [
            _make_result(vuln_id="CVE-2024-001"),
            _make_result(vuln_id="CVE-2024-002"),
            _make_result(vuln_id="CVE-2024-003"),
        ]
        tree = _make_tree_structure(vex_status="exploitable")

        doc, warnings = build_vex_document(results, tree, "App", "1.0")

        assert len(doc["vulnerabilities"]) == 3
        assert warnings == []

    def test_invalid_justification_falls_back(self):
        """Une justification invalide utilise requires_environment en fallback."""
        result = _make_result(
            decision="Not Affected",
            path=[
                DecisionPath(
                    node_id="output-na",
                    node_label="NA",
                    node_type="output",
                    field_evaluated=None,
                    value_found="NA",
                    condition_matched=None,
                ),
            ],
        )
        tree = {
            "nodes": [
                {
                    "id": "output-na",
                    "type": "output",
                    "config": {
                        "vex_status": "not_affected",
                        "vex_justification": "invalid_justification",
                    },
                }
            ]
        }

        doc, warnings = build_vex_document([result], tree, "App", "1.0")

        assert doc["vulnerabilities"][0]["analysis"]["justification"] == "requires_environment"
        assert any("invalid vex_justification" in w for w in warnings)


# --- Tests constantes ---


class TestConstants:
    def test_valid_statuses(self):
        """Les statuts VEX sont conformes à CycloneDX 1.6."""
        assert "not_affected" in VALID_VEX_STATUSES
        assert "exploitable" in VALID_VEX_STATUSES
        assert "in_triage" in VALID_VEX_STATUSES
        assert "resolved" in VALID_VEX_STATUSES
        # Les anciens noms VEX ne sont PAS valides en CycloneDX
        assert "affected" not in VALID_VEX_STATUSES
        assert "fixed" not in VALID_VEX_STATUSES

    def test_valid_justifications(self):
        """Les justifications sont conformes à CycloneDX 1.6."""
        assert "code_not_present" in VALID_VEX_JUSTIFICATIONS
        assert "code_not_reachable" in VALID_VEX_JUSTIFICATIONS
        assert "protected_by_mitigating_control" in VALID_VEX_JUSTIFICATIONS
