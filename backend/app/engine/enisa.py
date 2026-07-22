"""Fonctions pures ENISA (Phase 3 CRA) : échéances 24h/72h/14j et
pré-remplissage des trois jalons. Aucune I/O, `now` toujours injecté."""
from datetime import datetime, timedelta
from typing import Any

from app.models.enisa import EnisaEvent

MILESTONES = ("early_warning", "notification", "final_report")

# Délais réglementaires (art. 14 CRA)
_DELAYS = {
    "early_warning": timedelta(hours=24),
    "notification": timedelta(hours=72),
    "final_report": timedelta(days=14),
}

_MILESTONE_TITLES = {
    "early_warning": "Early warning (24h)",
    "notification": "Vulnerability notification (72h)",
    "final_report": "Final report (14d)",
}


def compute_milestones(event: EnisaEvent, now: datetime) -> dict[str, dict[str, Any]]:
    """État des trois jalons. Vide si l'événement n'est pas confirmé.

    early_warning / notification : ancrés sur confirmed_at.
    final_report : ancré sur corrective_available_at (null => en attente,
    jamais en retard). Un jalon soumis n'a ni compte à rebours ni retard.
    """
    if event.confirmed_at is None:
        return {}

    submitted = {
        "early_warning": event.early_warning_submitted_at,
        "notification": event.notification_submitted_at,
        "final_report": event.final_report_submitted_at,
    }
    anchors = {
        "early_warning": event.confirmed_at,
        "notification": event.confirmed_at,
        "final_report": event.corrective_available_at,
    }

    result: dict[str, dict[str, Any]] = {}
    for milestone in MILESTONES:
        anchor = anchors[milestone]
        due_at = anchor + _DELAYS[milestone] if anchor is not None else None
        submitted_at = submitted[milestone]

        if submitted_at is not None or due_at is None:
            remaining: int | None = None
            overdue = False
        else:
            remaining = max(0, int((due_at - now).total_seconds()))
            overdue = now > due_at

        result[milestone] = {
            "due_at": due_at,
            "remaining_seconds": remaining,
            "overdue": overdue,
            "submitted_at": submitted_at,
        }
    return result


def build_milestone_content(
    event: EnisaEvent, milestone: str, enisa_settings: dict[str, Any]
) -> dict[str, Any]:
    """Contenu pré-rempli d'un jalon depuis le snapshot d'évaluation.

    Gabarits croissants : l'alerte 24h est minimale, la notification 72h
    détaille sévérité/assets/SBOM, le rapport final ajoute correctif et
    chronologie.
    """
    ctx = event.evaluation_context or {}
    content: dict[str, Any] = {
        "cve_id": event.cve_id,
        "manufacturer": enisa_settings.get("manufacturer", {}),
        "exploitation_active": bool(ctx.get("kev")),
        "decision": ctx.get("decision"),
    }

    if milestone in ("notification", "final_report"):
        content.update({
            "severity": {
                "cvss_score": ctx.get("cvss_score"),
                "epss_score": ctx.get("epss_score"),
            },
            "affected_assets": event.affected_assets or [],
            "sbom_components": ctx.get("sbom_components", []),
            # Champ libre : TreeVuln ne connaît pas les mesures prises
            "corrective_measures": "",
        })

    if milestone == "final_report":
        content.update({
            "corrective_available_at": (
                event.corrective_available_at.isoformat()
                if event.corrective_available_at else None
            ),
            "timeline": {
                "detected_at": event.detected_at.isoformat() if event.detected_at else None,
                "confirmed_at": event.confirmed_at.isoformat() if event.confirmed_at else None,
            },
            "audit_trail": ctx.get("audit_trail", []),
        })

    return content


def merge_draft(prefilled: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """Fusionne le pré-rempli et le brouillon utilisateur (le brouillon gagne)."""
    return {**prefilled, **draft}


def render_markdown(content: dict[str, Any], milestone: str) -> str:
    """Rendu Markdown lisible d'un jalon (copier-coller vers la plateforme)."""
    lines = [f"# {_MILESTONE_TITLES.get(milestone, milestone)}", ""]
    for key, value in content.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, (dict, list)):
            import json

            lines.append(f"## {label}")
            lines.append("```json")
            lines.append(json.dumps(value, indent=2, ensure_ascii=False, default=str))
            lines.append("```")
        else:
            lines.append(f"- **{label}** : {value}")
    return "\n".join(lines)


def get_notifiable_node_ids(structure: dict[str, Any]) -> set[str]:
    """Ids des nœuds Output marqués enisa_notifiable dans la structure."""
    return {
        node["id"]
        for node in structure.get("nodes", [])
        if node.get("type") == "output"
        and (node.get("config") or {}).get("enisa_notifiable") is True
    }
