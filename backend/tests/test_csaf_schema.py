"""Tests de la validation VEX/CSAF des nœuds Output (Phase 1 CRA)."""

import pytest
from pydantic import ValidationError

from app.schemas.tree import NodeSchema


def _output_node(config: dict) -> dict:
    return {"id": "out-1", "type": "output", "label": "Act", "config": config}


class TestOutputVexValidation:
    def test_output_sans_champs_vex_reste_valide(self):
        node = NodeSchema.model_validate(_output_node({"decision": "Act", "color": "#f00"}))
        assert node.config["decision"] == "Act"

    def test_not_affected_avec_justification_valide(self):
        node = NodeSchema.model_validate(_output_node({
            "decision": "Track", "vex_status": "not_affected",
            "vex_justification": "component_not_present",
        }))
        assert node.config["vex_status"] == "not_affected"

    def test_affected_sans_justification_valide(self):
        node = NodeSchema.model_validate(_output_node({
            "decision": "Act", "vex_status": "affected",
        }))
        assert node.config["vex_status"] == "affected"

    def test_not_affected_sans_justification_rejete(self):
        with pytest.raises(ValidationError, match="vex_justification"):
            NodeSchema.model_validate(_output_node({
                "decision": "Track", "vex_status": "not_affected",
            }))

    def test_justification_hors_not_affected_rejetee(self):
        with pytest.raises(ValidationError, match="vex_justification"):
            NodeSchema.model_validate(_output_node({
                "decision": "Act", "vex_status": "affected",
                "vex_justification": "component_not_present",
            }))

    def test_justification_sans_status_rejetee(self):
        with pytest.raises(ValidationError, match="vex_justification"):
            NodeSchema.model_validate(_output_node({
                "decision": "Act", "vex_justification": "component_not_present",
            }))

    def test_vex_status_inconnu_rejete(self):
        with pytest.raises(ValidationError, match="vex_status"):
            NodeSchema.model_validate(_output_node({
                "decision": "Act", "vex_status": "exploitable",
            }))

    def test_justification_inconnue_rejetee(self):
        with pytest.raises(ValidationError, match="vex_justification"):
            NodeSchema.model_validate(_output_node({
                "decision": "Track", "vex_status": "not_affected",
                "vex_justification": "trust_me",
            }))

    def test_champs_vex_ignores_sur_noeud_input(self):
        # La règle ne s'applique qu'aux nœuds output
        node = NodeSchema.model_validate({
            "id": "in-1", "type": "input", "label": "CVSS",
            "config": {"field": "cvss_score", "vex_status": "bogus"},
        })
        assert node.type == "input"
