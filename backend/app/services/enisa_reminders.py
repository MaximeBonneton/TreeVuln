"""Tâche périodique de rappel des échéances ENISA (Phase 3 CRA).

Boucle asyncio unique lancée dans le lifespan. Chaque cycle : événements
confirmés avec jalon non soumis -> seuils franchis non notifiés ->
dispatch webhook `enisa_deadline`. Dédup via EnisaEvent.reminders_sent.
Un cycle raté ne tue jamais la boucle.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import async_session_maker
from app.engine.enisa import MILESTONES, compute_milestones
from app.models.enisa import EnisaEvent
from app.services.webhook_dispatch import schedule_webhook_dispatch

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300  # 5 minutes
DEFAULT_THRESHOLDS = ["T-12h", "T-2h", "overdue"]

# "T-12h" -> marge avant échéance ; "overdue" -> échéance dépassée
_THRESHOLD_MARGINS = {"T-12h": timedelta(hours=12), "T-2h": timedelta(hours=2)}

# Ordre de sévérité explicite (le plus urgent d'abord), indépendant de l'ordre
# d'insertion de _THRESHOLD_MARGINS : overdue > T-2h > T-12h (marge la plus
# petite = le plus urgent).
_SEVERITY_ORDER = ["overdue", "T-2h", "T-12h"]


def _crossed_thresholds(
    milestone_state: dict, now: datetime, thresholds: list[str]
) -> list[str]:
    """Seuils franchis pour un jalon non soumis, du plus au moins sévère."""
    due_at = milestone_state["due_at"]
    if due_at is None or milestone_state["submitted_at"] is not None:
        return []
    crossed = []
    for name in _SEVERITY_ORDER:
        if name not in thresholds:
            continue
        if name == "overdue":
            if now > due_at:
                crossed.append(name)
        elif now >= due_at - _THRESHOLD_MARGINS[name]:
            crossed.append(name)
    return crossed


async def check_reminders(now: datetime, thresholds: list[str]) -> None:
    """Un cycle de vérification. N'élève jamais d'exception."""
    try:
        async with async_session_maker() as db:
            rows = await db.execute(
                select(EnisaEvent).where(EnisaEvent.status == "confirmed")
            )
            events = list(rows.scalars().all())

            for event in events:
                milestones = compute_milestones(event, now)
                sent = dict(event.reminders_sent or {})
                changed = False

                for milestone in MILESTONES:
                    state = milestones.get(milestone)
                    if not state:
                        continue
                    crossed = _crossed_thresholds(state, now, thresholds)
                    already = set(sent.get(milestone, []))
                    fresh = [t for t in crossed if t not in already]
                    if not fresh:
                        continue
                    # Un seul rappel par cycle : le plus sévère ; les autres
                    # seuils franchis sont marqués envoyés (pas de rafale
                    # au premier cycle après un redémarrage)
                    schedule_webhook_dispatch(
                        event.tree_id,
                        "enisa_deadline",
                        {
                            "event_id": event.id,
                            "cve_id": event.cve_id,
                            "milestone": milestone,
                            "threshold": fresh[0],
                            "due_at": state["due_at"].isoformat(),
                            "remaining_seconds": state["remaining_seconds"],
                        },
                    )
                    sent[milestone] = sorted(already | set(crossed))
                    changed = True

                if changed:
                    event.reminders_sent = sent
            await db.commit()

    except Exception:
        logger.exception("ENISA reminder cycle failed — will retry next cycle")


async def _reminder_loop() -> None:
    """Boucle infinie, arrêtée par annulation au shutdown du lifespan."""
    from app.services.settings_service import ENISA_SETTINGS_KEY, SettingsService

    while True:
        try:
            async with async_session_maker() as db:
                stored = await SettingsService(db).get_setting(ENISA_SETTINGS_KEY) or {}
            thresholds = stored.get("reminder_thresholds", DEFAULT_THRESHOLDS)
            await check_reminders(datetime.now(timezone.utc), thresholds)
        except Exception:
            logger.exception("ENISA reminder loop iteration failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_reminder_loop() -> asyncio.Task:
    """Démarre la boucle (appelé une fois dans le lifespan)."""
    return asyncio.create_task(_reminder_loop())
