"""output_node_id dans les résultats + validation du flag enisa_notifiable."""
import pytest
from pydantic import ValidationError

from app.engine.inference import InferenceEngine
from app.schemas.tree import NodeSchema, TreeStructure
from app.schemas.vulnerability import VulnerabilityInput

STRUCTURE = TreeStructure.model_validate({
    "nodes": [
        {
            "id": "in-1", "type": "input", "label": "KEV",
            "config": {"field": "kev"},
            "conditions": [
                {"label": "oui", "operator": "eq", "value": True},
                {"label": "non", "operator": "eq", "value": False},
            ],
        },
        {"id": "out-act", "type": "output", "label": "Act",
         "config": {"decision": "Act", "enisa_notifiable": True}},
        {"id": "out-track", "type": "output", "label": "Track",
         "config": {"decision": "Track"}},
    ],
    "edges": [
        {"id": "e1", "source": "in-1", "target": "out-act", "source_handle": "handle-0"},
        {"id": "e2", "source": "in-1", "target": "out-track", "source_handle": "handle-1"},
    ],
})


class TestOutputNodeId:
    def test_present_sans_include_path(self):
        engine = InferenceEngine(STRUCTURE)
        vuln = VulnerabilityInput(cve_id="CVE-1", kev=True)
        result = engine.evaluate(vuln, {}, include_path=False)
        assert result.decision == "Act"
        assert result.output_node_id == "out-act"

    def test_present_avec_include_path(self):
        engine = InferenceEngine(STRUCTURE)
        vuln = VulnerabilityInput(cve_id="CVE-1", kev=False)
        result = engine.evaluate(vuln, {}, include_path=True)
        assert result.output_node_id == "out-track"

    def test_absent_sur_erreur(self):
        engine = InferenceEngine(STRUCTURE)
        # kev=None ne correspond à aucune des deux conditions (eq True / eq False)
        vuln = VulnerabilityInput(cve_id="CVE-1", kev=None)
        result = engine.evaluate(vuln, {}, False)
        # pas de branche pour cette valeur -> erreur, pas d'output atteint
        assert result.error is not None
        assert result.output_node_id is None


class TestEnisaNotifiableValidation:
    def _node(self, node_type: str, config: dict) -> dict:
        return {"id": "n1", "type": node_type, "label": "N", "position": {"x": 0, "y": 0},
                "config": config}

    def test_flag_bool_accepte_sur_output(self):
        node = NodeSchema.model_validate(
            self._node("output", {"decision": "Act", "enisa_notifiable": True})
        )
        assert node.config["enisa_notifiable"] is True

    def test_flag_non_bool_refuse(self):
        with pytest.raises(ValidationError, match="enisa_notifiable"):
            NodeSchema.model_validate(
                self._node("output", {"decision": "Act", "enisa_notifiable": "yes"})
            )

    def test_flag_refuse_hors_output(self):
        with pytest.raises(ValidationError, match="enisa_notifiable"):
            NodeSchema.model_validate(
                self._node("input", {"field": "kev", "enisa_notifiable": True})
            )

    def test_absence_du_flag_ok(self):
        node = NodeSchema.model_validate(self._node("output", {"decision": "Act"}))
        assert "enisa_notifiable" not in node.config
