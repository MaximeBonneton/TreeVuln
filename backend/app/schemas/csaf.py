"""Enums et constantes CSAF 2.0 / VEX (Phase 1 roadmap CRA).

Valeurs normalisées par le standard CSAF 2.0 (OASIS) :
- statuts produit du profil VEX ;
- justifications autorisées pour le statut not_affected (flag labels).
"""

from enum import Enum


class CsafVexStatus(str, Enum):
    """Statut VEX configuré sur un nœud Output."""

    NOT_AFFECTED = "not_affected"
    AFFECTED = "affected"
    FIXED = "fixed"
    UNDER_INVESTIGATION = "under_investigation"


class CsafVexJustification(str, Enum):
    """Justification CSAF obligatoire quand vex_status = not_affected."""

    COMPONENT_NOT_PRESENT = "component_not_present"
    VULNERABLE_CODE_NOT_PRESENT = "vulnerable_code_not_present"
    VULNERABLE_CODE_NOT_IN_EXECUTE_PATH = "vulnerable_code_not_in_execute_path"
    VULNERABLE_CODE_CANNOT_BE_CONTROLLED_BY_ADVERSARY = (
        "vulnerable_code_cannot_be_controlled_by_adversary"
    )
    INLINE_MITIGATIONS_ALREADY_EXIST = "inline_mitigations_already_exist"


# Groupe de product_status CSAF correspondant à chaque statut VEX
PRODUCT_STATUS_BY_VEX: dict[str, str] = {
    CsafVexStatus.AFFECTED.value: "known_affected",
    CsafVexStatus.NOT_AFFECTED.value: "known_not_affected",
    CsafVexStatus.FIXED.value: "fixed",
    CsafVexStatus.UNDER_INVESTIGATION.value: "under_investigation",
}
