"""Tests de l'intégration des champs virtuels sbom_* dans le moteur."""
from app.engine.inference import InferenceEngine
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput

# Arbre : sbom_component_present true -> Act ; false -> Track ; null -> Attend
SBOM_TREE = TreeStructure.model_validate({
    "nodes": [
        {"id": "in-1", "type": "input", "label": "Component present?",
         "config": {"field": "sbom_component_present"},
         "conditions": [
             {"label": "present", "operator": "eq", "value": True},
             {"label": "absent", "operator": "eq", "value": False},
             {"label": "unknown", "operator": "is_null", "value": None},
         ]},
        {"id": "out-act", "type": "output", "label": "Act",
         "config": {"decision": "Act"}},
        {"id": "out-track", "type": "output", "label": "Track",
         "config": {"decision": "Track"}},
        {"id": "out-attend", "type": "output", "label": "Attend",
         "config": {"decision": "Attend"}},
    ],
    "edges": [
        {"id": "e0", "source": "in-1", "target": "out-act", "source_handle": "handle-0"},
        {"id": "e1", "source": "in-1", "target": "out-track", "source_handle": "handle-1"},
        {"id": "e2", "source": "in-1", "target": "out-attend", "source_handle": "handle-2"},
    ],
})

LOOKUPS = {
    "sbom_components": {
        "srv-001": [{"purl": "pkg:npm/lodash@4.17.21", "name": "lodash",
                     "version": "4.17.21"}],
    }
}


class TestSbomFieldsInEngine:
    def test_composant_present(self):
        engine = InferenceEngine(SBOM_TREE)
        vuln = VulnerabilityInput(cve_id="CVE-2024-0001", asset_id="srv-001",
                                  extra={"purl": "pkg:npm/lodash@4.17.21"})
        result = engine.evaluate(vuln, LOOKUPS, include_path=True)
        assert result.decision == "Act"
        # L'audit trail expose la valeur calculée
        assert result.path[0].value_found is True

    def test_composant_absent(self):
        engine = InferenceEngine(SBOM_TREE)
        vuln = VulnerabilityInput(cve_id="CVE-2024-0002", asset_id="srv-001",
                                  extra={"purl": "pkg:npm/left-pad@1.0.0"})
        result = engine.evaluate(vuln, LOOKUPS, include_path=True)
        assert result.decision == "Track"

    def test_asset_sans_sbom_null(self):
        engine = InferenceEngine(SBOM_TREE)
        vuln = VulnerabilityInput(cve_id="CVE-2024-0003", asset_id="srv-sans-sbom",
                                  extra={"purl": "pkg:npm/lodash@4.17.21"})
        result = engine.evaluate(vuln, LOOKUPS, include_path=True)
        assert result.decision == "Attend"

    def test_vuln_sans_purl_null(self):
        engine = InferenceEngine(SBOM_TREE)
        vuln = VulnerabilityInput(cve_id="CVE-2024-0004", asset_id="srv-001")
        result = engine.evaluate(vuln, LOOKUPS, include_path=True)
        assert result.decision == "Attend"


class TestUsesSbomFields:
    def test_arbre_avec_champ_sbom(self):
        assert InferenceEngine(SBOM_TREE).uses_sbom_fields() is True

    def test_arbre_sans_champ_sbom(self):
        tree = TreeStructure.model_validate({
            "nodes": [
                {"id": "in-1", "type": "input", "label": "CVSS",
                 "config": {"field": "cvss_score"},
                 "conditions": [{"label": "x", "operator": "gte", "value": 9}]},
                {"id": "out-1", "type": "output", "label": "Act",
                 "config": {"decision": "Act"}},
            ],
            "edges": [{"id": "e0", "source": "in-1", "target": "out-1",
                       "source_handle": "handle-0"}],
        })
        assert InferenceEngine(tree).uses_sbom_fields() is False

    def test_champ_sbom_dans_critere_compose(self):
        tree = TreeStructure.model_validate({
            "nodes": [
                {"id": "in-1", "type": "input", "label": "Combo",
                 "config": {"field": "cvss_score"},
                 "conditions": [{
                     "label": "x", "logic": "AND",
                     "criteria": [
                         {"field": "sbom_component_present", "operator": "eq",
                          "value": True},
                         {"operator": "gte", "value": 7},
                     ],
                 }]},
                {"id": "out-1", "type": "output", "label": "Act",
                 "config": {"decision": "Act"}},
            ],
            "edges": [{"id": "e0", "source": "in-1", "target": "out-1",
                       "source_handle": "handle-0"}],
        })
        assert InferenceEngine(tree).uses_sbom_fields() is True
