"""Enregistrement des candidats ENISA depuis le pipeline d'évaluation.

Session indépendante de la requête (comme webhook_dispatch) et isolation
stricte : une panne ici ne doit JAMAIS faire échouer une évaluation.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import async_session_maker
from app.engine.enisa import get_notifiable_node_ids
from app.models.enisa import EnisaEvent
from app.schemas.evaluation import EvaluationResult

logger = logging.getLogger(__name__)

# Clés du contexte snapshoté depuis la vulnérabilité d'origine
_CONTEXT_FIELDS = ("kev", "epss_score", "cvss_score")


async def record_candidates(
    tree_id: int,
    structure: dict[str, Any],
    evaluated: list[tuple[EvaluationResult, dict[str, Any]]],
) -> None:
    """Upsert des candidats pour les résultats atteignant un Output flaggé.

    Dédup par (tree_id, cve_id) : les réévaluations rafraîchissent
    last_detected_at, remplacent evaluation_context et agrègent les assets.
    Un événement dismissed n'est pas réouvert : redetection_count++.
    """
    try:
        notifiable = get_notifiable_node_ids(structure)
        if not notifiable:
            return

        # Regroupe par CVE (un upsert par CVE distinct, pas par ligne)
        by_cve: dict[str, dict[str, Any]] = {}
        for result, vuln in evaluated:
            if result.error or result.output_node_id not in notifiable:
                continue
            cve = (vuln.get("cve_id") or "").strip()
            if not cve:
                continue
            entry = by_cve.setdefault(cve, {"assets": [], "context": None})
            asset_id = vuln.get("asset_id")
            if asset_id and asset_id not in entry["assets"]:
                entry["assets"].append(asset_id)
            entry["context"] = _build_context(result, vuln)

        if not by_cve:
            return

        now = datetime.now(timezone.utc)
        async with async_session_maker() as db:
            existing_rows = await db.execute(
                select(EnisaEvent).where(
                    EnisaEvent.tree_id == tree_id,
                    EnisaEvent.cve_id.in_(by_cve.keys()),
                )
            )
            existing = {e.cve_id: e for e in existing_rows.scalars().all()}

            for cve, entry in by_cve.items():
                assets = [{"asset_id": a} for a in entry["assets"]]
                event = existing.get(cve)
                if event is not None:
                    _apply_update(event, now, entry, assets)
                    continue

                # Chemin de création, isolé dans un SAVEPOINT : sous
                # concurrence (deux pipelines d'ingestion/évaluation qui
                # découvrent le même nouveau CVE en même temps), le SELECT
                # ci-dessus peut ne pas voir la ligne créée entre-temps par
                # l'autre transaction. Sans isolation, l'IntegrityError sur
                # uq_enisa_events_tree_cve serait attrapée par le except
                # englobant et ferait perdre TOUT le lot de candidats de cet
                # appel (y compris les CVE sans rapport). Le SAVEPOINT limite
                # le rollback à ce seul CVE ; les autres continuent normalement.
                try:
                    async with db.begin_nested():
                        db.add(EnisaEvent(
                            tree_id=tree_id,
                            cve_id=cve,
                            status="candidate",
                            detected_at=now,
                            last_detected_at=now,
                            affected_assets=assets,
                            evaluation_context=entry["context"],
                        ))
                        await db.flush()
                except IntegrityError:
                    # L'autre transaction a gagné la course : on retraite ce
                    # CVE comme une mise à jour (même sémantique que si le
                    # SELECT initial l'avait trouvé).
                    refetched = await db.execute(
                        select(EnisaEvent).where(
                            EnisaEvent.tree_id == tree_id, EnisaEvent.cve_id == cve
                        )
                    )
                    concurrent_event = refetched.scalar_one_or_none()
                    if concurrent_event is not None:
                        _apply_update(concurrent_event, now, entry, assets)
                    else:
                        # Cas improbable (ligne supprimée entre la violation
                        # et le refetch) : on logge et on continue plutôt que
                        # de perdre le reste du lot.
                        logger.warning(
                            "ENISA conflict without matching row after refetch "
                            "(tree_id=%s, cve=%s)",
                            tree_id, cve,
                        )
            await db.commit()

    except Exception:
        logger.exception(
            "ENISA candidate recording failed (tree_id=%s) — evaluation unaffected",
            tree_id,
        )


def _apply_update(
    event: EnisaEvent,
    now: datetime,
    entry: dict[str, Any],
    assets: list[dict[str, Any]],
) -> None:
    """Rafraîchit un événement existant : dernière détection, contexte,
    agrégation des assets sans doublon, redetection_count si dismissed."""
    event.last_detected_at = now
    event.evaluation_context = entry["context"]
    known = {a.get("asset_id") for a in (event.affected_assets or [])}
    merged = list(event.affected_assets or [])
    merged.extend(a for a in assets if a["asset_id"] not in known)
    event.affected_assets = merged
    if event.status == "dismissed":
        event.redetection_count += 1


def _build_context(result: EvaluationResult, vuln: dict[str, Any]) -> dict[str, Any]:
    """Snapshot du dernier état connu pour le pré-remplissage."""
    context: dict[str, Any] = {
        "decision": result.decision,
        "audit_trail": [step.model_dump() for step in result.path],
    }
    for field in _CONTEXT_FIELDS:
        if field in vuln:
            context[field] = vuln[field]
    return context
