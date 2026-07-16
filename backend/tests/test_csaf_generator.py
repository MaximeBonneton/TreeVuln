"""Tests du générateur de documents CSAF 2.0 profil VEX."""
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from app.engine.csaf import CsafExclusion, build_csaf_document
from app.schemas.evaluation import DecisionPath, EvaluationResult
from app.schemas.tree import TreeStructure

FIXTURES = Path(__file__).parent / "fixtures"
GENERATED_AT = datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc)
TRACKING_ID = "acme-medical-example-com-9f4c1c9e-0000-0000-0000-000000000001"
PUBLISHER = {
    "name": "ACME Medical",
    "namespace": "https://acme-medical.example.com",
    "category": "vendor",
}
ASSETS = {
    "srv-prod-001": {"asset_id": "srv-prod-001", "name": "Production Web Server"},
    "srv-dev-001": {"asset_id": "srv-dev-001", "name": "Development Server"},
}


def _structure() -> TreeStructure:
    """Arbre minimal : 3 outputs avec vex_status, 1 output sans."""
    return TreeStructure.model_validate({
        "nodes": [
            {"id": "in-1", "type": "input", "label": "KEV",
             "config": {"field": "kev"},
             "conditions": [{"label": "yes", "operator": "eq", "value": True}]},
            {"id": "out-act", "type": "output", "label": "Act",
             "config": {"decision": "Act", "vex_status": "affected"}},
            {"id": "out-track", "type": "output", "label": "Track",
             "config": {"decision": "Track", "vex_status": "not_affected",
                        "vex_justification": "component_not_present"}},
            {"id": "out-fixed", "type": "output", "label": "Fixed",
             "config": {"decision": "Track", "vex_status": "fixed"}},
            {"id": "out-nomap", "type": "output", "label": "NoMap",
             "config": {"decision": "Attend"}},
        ],
        "edges": [],
    })


def _result(vuln_id: str | None, output_node: str, decision: str) -> EvaluationResult:
    return EvaluationResult(
        vuln_id=vuln_id,
        decision=decision,
        path=[
            DecisionPath(node_id="in-1", node_label="KEV", node_type="input",
                         field_evaluated="kev", value_found=True,
                         condition_matched="yes"),
            DecisionPath(node_id=output_node, node_label=decision,
                         node_type="output"),
        ],
    )


def _build(items):
    return build_csaf_document(
        items, ASSETS, _structure(), PUBLISHER, TRACKING_ID, GENERATED_AT
    )


class TestDocumentStructure:
    def test_metadonnees_document(self):
        items = [(_result("CVE-2024-0001", "out-act", "Act"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"})]
        doc, exclusions = _build(items)
        assert exclusions == []
        assert doc["document"]["category"] == "csaf_vex"
        assert doc["document"]["csaf_version"] == "2.0"
        assert doc["document"]["publisher"] == {
            "category": "vendor",
            "name": "ACME Medical",
            "namespace": "https://acme-medical.example.com",
        }
        tracking = doc["document"]["tracking"]
        assert tracking["id"] == TRACKING_ID
        assert tracking["version"] == "1"
        assert tracking["status"] == "final"
        assert tracking["initial_release_date"] == tracking["current_release_date"]
        assert len(tracking["revision_history"]) == 1

    def test_product_tree_un_produit_par_asset_reference(self):
        items = [
            (_result("CVE-2024-0001", "out-act", "Act"),
             {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"}),
            (_result("CVE-2024-0002", "out-track", "Track"),
             {"cve_id": "CVE-2024-0002", "asset_id": "srv-dev-001"}),
            # Même asset que le premier : pas de doublon dans product_tree
            (_result("CVE-2024-0002", "out-act", "Act"),
             {"cve_id": "CVE-2024-0002", "asset_id": "srv-prod-001"}),
        ]
        doc, _ = _build(items)
        products = doc["product_tree"]["full_product_names"]
        assert sorted(p["product_id"] for p in products) == [
            "srv-dev-001", "srv-prod-001",
        ]
        by_id = {p["product_id"]: p["name"] for p in products}
        assert by_id["srv-prod-001"] == "Production Web Server"


class TestProductStatusEtFlags:
    def test_regroupement_par_statut(self):
        items = [
            (_result("CVE-2024-0001", "out-act", "Act"),
             {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"}),
            (_result("CVE-2024-0001", "out-track", "Track"),
             {"cve_id": "CVE-2024-0001", "asset_id": "srv-dev-001"}),
        ]
        doc, _ = _build(items)
        assert len(doc["vulnerabilities"]) == 1
        vuln = doc["vulnerabilities"][0]
        assert vuln["cve"] == "CVE-2024-0001"
        assert vuln["product_status"]["known_affected"] == ["srv-prod-001"]
        assert vuln["product_status"]["known_not_affected"] == ["srv-dev-001"]

    def test_flag_justification_pour_not_affected(self):
        items = [(_result("CVE-2024-0001", "out-track", "Track"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-dev-001"})]
        doc, _ = _build(items)
        flags = doc["vulnerabilities"][0]["flags"]
        assert flags == [{
            "label": "component_not_present",
            "product_ids": ["srv-dev-001"],
        }]

    def test_statut_fixed(self):
        items = [(_result("CVE-2024-0001", "out-fixed", "Track"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"})]
        doc, _ = _build(items)
        assert doc["vulnerabilities"][0]["product_status"]["fixed"] == ["srv-prod-001"]


class TestNotesAuditTrail:
    def test_note_par_couple_cve_produit(self):
        items = [(_result("CVE-2024-0001", "out-act", "Act"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"})]
        doc, _ = _build(items)
        notes = doc["vulnerabilities"][0]["notes"]
        assert len(notes) == 1
        note = notes[0]
        assert note["category"] == "other"
        assert note["title"] == "TreeVuln decision path"
        # Le texte contient le produit, les étapes du chemin et la décision
        assert "srv-prod-001" in note["text"]
        assert "kev" in note["text"]
        assert "Décision TreeVuln : Act" in note["text"]


class TestExclusions:
    def test_erreur_evaluation_exclue(self):
        items = [(EvaluationResult(vuln_id="CVE-2024-0001", decision="Error",
                                   error="champ manquant"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"})]
        doc, exclusions = _build(items)
        assert doc is None
        assert exclusions == [CsafExclusion(
            vuln_id="CVE-2024-0001", reason="evaluation_error: champ manquant"
        )]

    def test_output_sans_vex_status_exclu(self):
        items = [(_result("CVE-2024-0001", "out-nomap", "Attend"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"})]
        doc, exclusions = _build(items)
        assert doc is None
        assert exclusions[0].reason == "output_node_has_no_vex_status"

    def test_asset_non_resolu_exclu(self):
        items = [(_result("CVE-2024-0001", "out-act", "Act"),
                  {"cve_id": "CVE-2024-0001", "asset_id": "srv-inconnu"})]
        doc, exclusions = _build(items)
        assert doc is None
        assert exclusions[0].reason == "unknown_asset: srv-inconnu"

    def test_sans_asset_id_exclu(self):
        items = [(_result("CVE-2024-0001", "out-act", "Act"),
                  {"cve_id": "CVE-2024-0001"})]
        doc, exclusions = _build(items)
        assert exclusions[0].reason == "missing_asset_id"

    def test_cve_invalide_exclu(self):
        items = [(_result("VULN-42", "out-act", "Act"),
                  {"cve_id": "VULN-42", "asset_id": "srv-prod-001"}),
                 (_result(None, "out-act", "Act"),
                  {"asset_id": "srv-prod-001"})]
        doc, exclusions = _build(items)
        assert doc is None
        assert len(exclusions) == 2
        assert all(e.reason == "missing_or_invalid_cve_id" for e in exclusions)

    def test_items_valides_conserves_malgre_exclusions(self):
        items = [
            (_result("CVE-2024-0001", "out-act", "Act"),
             {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"}),
            (_result("CVE-2024-0002", "out-nomap", "Attend"),
             {"cve_id": "CVE-2024-0002", "asset_id": "srv-prod-001"}),
        ]
        doc, exclusions = _build(items)
        assert doc is not None
        assert len(doc["vulnerabilities"]) == 1
        assert len(exclusions) == 1


class TestValidationSchemaOfficiel:
    def test_document_valide_contre_schema_csaf_2_0(self):
        schema = json.loads((FIXTURES / "csaf_json_schema.json").read_text())
        items = [
            (_result("CVE-2024-0001", "out-act", "Act"),
             {"cve_id": "CVE-2024-0001", "asset_id": "srv-prod-001"}),
            (_result("CVE-2024-0001", "out-track", "Track"),
             {"cve_id": "CVE-2024-0001", "asset_id": "srv-dev-001"}),
            (_result("CVE-2024-0002", "out-fixed", "Track"),
             {"cve_id": "CVE-2024-0002", "asset_id": "srv-prod-001"}),
        ]
        doc, _ = _build(items)
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        assert not errors, [e.message for e in errors]
