"""Génération de documents CSAF 2.0 profil VEX (Phase 1 roadmap CRA).

Fonction pure, sans I/O : les résultats d'évaluation (avec audit trail),
le cache d'assets, la structure de l'arbre (pour lire le vex_status des
nœuds Output atteints) et l'identité éditeur produisent un document CSAF
unique. Les items non exportables (erreur, CVE ou asset manquant, Output
sans vex_status) sont exclus individuellement, jamais bloquants.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.schemas.csaf import CsafVexStatus, PRODUCT_STATUS_BY_VEX
from app.schemas.evaluation import EvaluationResult
from app.schemas.tree import NodeType, TreeStructure

# Pattern imposé par le schéma CSAF 2.0 pour le champ cve
_CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")


@dataclass
class CsafExclusion:
    """Item exclu du document, avec la raison (pour exclusions.json)."""

    vuln_id: str | None
    reason: str


def _vex_config_by_output(structure: TreeStructure) -> dict[str, dict[str, str]]:
    """Map node_id -> {vex_status, vex_justification} des nœuds Output."""
    mapping: dict[str, dict[str, str]] = {}
    for node in structure.nodes:
        if node.type == NodeType.OUTPUT and node.config.get("vex_status"):
            mapping[node.id] = {
                "vex_status": node.config["vex_status"],
                "vex_justification": node.config.get("vex_justification"),
            }
    return mapping


def _format_decision_path(result: EvaluationResult, product_id: str) -> str:
    """Sérialise lisiblement l'audit trail pour la note CSAF."""
    lines = [f"Produit : {product_id}"]
    for i, step in enumerate(result.path, start=1):
        detail = f"{i}. {step.node_label} [{step.node_type}]"
        if step.field_evaluated is not None:
            detail += f" {step.field_evaluated} = {step.value_found!r}"
        if step.condition_matched:
            detail += f" -> {step.condition_matched}"
        lines.append(detail)
    lines.append(f"Décision TreeVuln : {result.decision}")
    return "\n".join(lines)


def build_csaf_document(
    items: list[tuple[EvaluationResult, dict[str, Any]]],
    assets: dict[str, dict[str, Any]],
    structure: TreeStructure,
    publisher: dict[str, str],
    tracking_id: str,
    generated_at: datetime,
) -> tuple[dict[str, Any] | None, list[CsafExclusion]]:
    """Construit le document CSAF VEX à partir des résultats d'un batch.

    Args:
        items: couples (résultat d'évaluation, ligne d'entrée brute), dans
            l'ordre du batch — cve_id et asset_id sont lus sur la ligne brute.
        assets: cache {asset_id: {name, ...}} du référentiel de l'arbre.
        structure: structure de l'arbre (vex_status des nœuds Output).
        publisher: {"name", "namespace", "category"} depuis les settings.
        tracking_id: identifiant unique du document (généré par l'appelant).
        generated_at: horodatage de l'export (UTC).

    Returns:
        (document ou None si aucun item exportable, exclusions)
    """
    vex_by_output = _vex_config_by_output(structure)
    exclusions: list[CsafExclusion] = []

    # Accumulateurs : par CVE -> par groupe product_status -> product_ids ;
    # flags par (CVE, justification) ; notes par (CVE, produit).
    status_by_cve: dict[str, dict[str, list[str]]] = {}
    flags_by_cve: dict[str, dict[str, list[str]]] = {}
    notes_by_cve: dict[str, list[dict[str, str]]] = {}
    used_products: dict[str, str] = {}  # product_id -> name

    for result, row in items:
        if result.error:
            exclusions.append(CsafExclusion(
                vuln_id=result.vuln_id,
                reason=f"evaluation_error: {result.error}",
            ))
            continue

        cve_id = row.get("cve_id")
        if not isinstance(cve_id, str) or not _CVE_PATTERN.match(cve_id):
            exclusions.append(CsafExclusion(
                vuln_id=result.vuln_id, reason="missing_or_invalid_cve_id"
            ))
            continue

        asset_id = row.get("asset_id")
        if not asset_id:
            exclusions.append(CsafExclusion(
                vuln_id=result.vuln_id, reason="missing_asset_id"
            ))
            continue
        asset = assets.get(str(asset_id))
        if asset is None:
            exclusions.append(CsafExclusion(
                vuln_id=result.vuln_id, reason=f"unknown_asset: {asset_id}"
            ))
            continue

        reached_node_id = result.path[-1].node_id if result.path else None
        vex = vex_by_output.get(reached_node_id) if reached_node_id else None
        if vex is None:
            exclusions.append(CsafExclusion(
                vuln_id=result.vuln_id, reason="output_node_has_no_vex_status"
            ))
            continue

        product_id = str(asset_id)
        used_products[product_id] = asset.get("name") or product_id

        group = PRODUCT_STATUS_BY_VEX[vex["vex_status"]]
        ids = status_by_cve.setdefault(cve_id, {}).setdefault(group, [])
        if product_id not in ids:
            ids.append(product_id)

        if vex["vex_status"] == CsafVexStatus.NOT_AFFECTED.value:
            flag_ids = flags_by_cve.setdefault(cve_id, {}).setdefault(
                vex["vex_justification"], []
            )
            if product_id not in flag_ids:
                flag_ids.append(product_id)

        notes_by_cve.setdefault(cve_id, []).append({
            "category": "other",
            "title": "TreeVuln decision path",
            "text": _format_decision_path(result, product_id),
        })

    if not status_by_cve:
        return None, exclusions

    timestamp = generated_at.isoformat().replace("+00:00", "Z")

    vulnerabilities: list[dict[str, Any]] = []
    for cve_id in sorted(status_by_cve):
        vuln: dict[str, Any] = {
            "cve": cve_id,
            "product_status": {
                group: sorted(ids)
                for group, ids in sorted(status_by_cve[cve_id].items())
            },
            "notes": notes_by_cve[cve_id],
        }
        if cve_id in flags_by_cve:
            vuln["flags"] = [
                {"label": label, "product_ids": sorted(ids)}
                for label, ids in sorted(flags_by_cve[cve_id].items())
            ]
        vulnerabilities.append(vuln)

    document: dict[str, Any] = {
        "document": {
            "category": "csaf_vex",
            "csaf_version": "2.0",
            "lang": "en",
            "publisher": {
                "category": publisher["category"],
                "name": publisher["name"],
                "namespace": publisher["namespace"],
            },
            "title": "TreeVuln VEX export",
            "tracking": {
                "current_release_date": timestamp,
                "generator": {"engine": {"name": "TreeVuln"}},
                "id": tracking_id,
                "initial_release_date": timestamp,
                "revision_history": [
                    {"date": timestamp, "number": "1", "summary": "Initial version"}
                ],
                "status": "final",
                "version": "1",
            },
        },
        "product_tree": {
            "full_product_names": [
                {"name": name, "product_id": pid}
                for pid, name in sorted(used_products.items())
            ]
        },
        "vulnerabilities": vulnerabilities,
    }
    return document, exclusions
