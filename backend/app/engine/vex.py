"""
Générateur de documents CycloneDX VEX 1.6.
Transforme les résultats d'évaluation TreeVuln en documents VEX standardisés.
"""

import uuid
from datetime import datetime, timezone

from app.schemas.evaluation import EvaluationResult

# Statuts VEX CycloneDX 1.6 valides (impactAnalysisState)
VALID_VEX_STATUSES = {
    "not_affected",
    "exploitable",
    "resolved",
    "resolved_with_pedigree",
    "in_triage",
    "false_positive",
}

# Justifications CycloneDX 1.6 valides (seulement pour not_affected)
VALID_VEX_JUSTIFICATIONS = {
    "code_not_present",
    "code_not_reachable",
    "requires_configuration",
    "requires_dependency",
    "requires_environment",
    "protected_by_compiler",
    "protected_at_runtime",
    "protected_at_perimeter",
    "protected_by_mitigating_control",
}


def _build_detail(result: EvaluationResult) -> str:
    """Construit le détail de justification depuis l'audit trail.

    Inclut tous les nœuds traversés (input, lookup, equation, output).
    """
    parts = []
    for step in result.path:
        if step.node_type == "output":
            parts.append(f"Decision: {result.decision}")
        elif step.condition_matched:
            # Inclut le nœud même si field_evaluated est None (ex: equation)
            if step.field_evaluated:
                field_info = f"{step.field_evaluated}={step.value_found}"
            else:
                field_info = str(step.value_found)
            parts.append(
                f"{step.node_label}: {field_info} ({step.condition_matched})"
            )
    return " \u2192 ".join(parts)


def _get_vex_config(
    result: EvaluationResult, tree_structure: dict
) -> tuple[str | None, str | None]:
    """Extrait le vex_status et vex_justification du nœud Output.

    Returns:
        tuple: (vex_status, vex_justification) — justification peut être None
    """
    if not result.path:
        return None, None
    output_node_id = result.path[-1].node_id
    for node in tree_structure.get("nodes", []):
        if node.get("id") == output_node_id:
            config = node.get("config", {})
            return config.get("vex_status"), config.get("vex_justification")
    return None, None


def build_vex_document(
    results: list[EvaluationResult],
    tree_structure: dict,
    product_name: str,
    product_version: str,
) -> tuple[dict, list[str]]:
    """Construit un document CycloneDX VEX depuis des résultats d'évaluation.

    Args:
        results: Résultats d'évaluation (avec audit trail)
        tree_structure: Structure brute de l'arbre (JSONB)
        product_name: Nom du produit pour les métadonnées CycloneDX
        product_version: Version du produit

    Returns:
        tuple: (document CycloneDX dict, liste de warnings)
    """
    warnings: list[str] = []
    vulnerabilities: list[dict] = []

    for result in results:
        # Exclure les erreurs
        if result.error:
            warnings.append(
                f"{result.vuln_id}: excluded (evaluation error: {result.error})"
            )
            continue

        # Exclure si pas de vuln_id
        if not result.vuln_id:
            warnings.append("Vulnerability without id excluded")
            continue

        # Récupérer le vex_status et justification depuis la config du nœud Output
        vex_status, vex_justification = _get_vex_config(result, tree_structure)
        if not vex_status:
            warnings.append(
                f"{result.vuln_id}: excluded (no vex_status on output node "
                f"'{result.decision}')"
            )
            continue

        if vex_status not in VALID_VEX_STATUSES:
            warnings.append(
                f"{result.vuln_id}: excluded (invalid vex_status '{vex_status}')"
            )
            continue

        # Construire l'objet analysis
        analysis: dict = {
            "state": vex_status,
            "detail": _build_detail(result),
        }
        # justification seulement pour not_affected (conformité CycloneDX 1.6)
        if vex_status == "not_affected":
            justification = vex_justification or "requires_environment"
            if justification in VALID_VEX_JUSTIFICATIONS:
                analysis["justification"] = justification
            else:
                analysis["justification"] = "requires_environment"
                warnings.append(
                    f"{result.vuln_id}: invalid vex_justification "
                    f"'{vex_justification}', using 'requires_environment'"
                )

        vulnerabilities.append({
            "id": result.vuln_id,
            "analysis": analysis,
        })

    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "TreeVuln",
                        "version": "0.1.0",
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": product_name,
                "version": product_version,
            },
        },
        "vulnerabilities": vulnerabilities,
    }

    return document, warnings
