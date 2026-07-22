"""Cycle de rappel : seuils franchis, dédup, dispatch webhook, isolation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.enisa import EnisaEvent
from app.services.enisa_reminders import check_reminders

NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
THRESHOLDS = ["T-12h", "T-2h", "overdue"]


@pytest.fixture(autouse=True)
def _patch_session_maker(db_engine, monkeypatch):
    """check_reminders ouvre sa propre session (comme webhook_dispatch et
    enisa_service), indépendante de la requête HTTP. On la redirige vers la
    base éphémère de test (le sessionmaker global d'app.database pointe sur
    l'URL placeholder définie avant l'import de `app`)."""
    import app.services.enisa_reminders as mod

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(mod, "async_session_maker", maker)


async def _confirmed_event(db_session, tree_id: int, cve: str, hours_ago: float) -> EnisaEvent:
    event = EnisaEvent(
        tree_id=tree_id, cve_id=cve, status="confirmed",
        confirmed_at=NOW - timedelta(hours=hours_ago),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest.mark.asyncio
class TestCheckReminders:
    async def test_seuil_t12_franchi(self, db_session, sample_tree):
        # confirmé il y a 14h -> early_warning due dans 10h -> T-12h franchi
        await _confirmed_event(db_session, sample_tree.id, "CVE-R1", 14)
        with patch("app.services.enisa_reminders.schedule_webhook_dispatch") as mock:
            await check_reminders(NOW, THRESHOLDS)
        calls = [c for c in mock.call_args_list if c.args[1] == "enisa_deadline"]
        assert len(calls) == 1
        payload = calls[0].args[2]
        assert payload["milestone"] == "early_warning"
        assert payload["threshold"] == "T-12h"
        assert payload["cve_id"] == "CVE-R1"

    async def test_dedup_seuil_deja_notifie(self, db_session, sample_tree):
        await _confirmed_event(db_session, sample_tree.id, "CVE-R2", 14)
        with patch("app.services.enisa_reminders.schedule_webhook_dispatch") as mock:
            await check_reminders(NOW, THRESHOLDS)
            await check_reminders(NOW + timedelta(minutes=5), THRESHOLDS)
        enisa_calls = [c for c in mock.call_args_list if c.args[1] == "enisa_deadline"]
        assert len(enisa_calls) == 1  # pas de doublon

    async def test_depassement(self, db_session, sample_tree):
        await _confirmed_event(db_session, sample_tree.id, "CVE-R3", 30)
        with patch("app.services.enisa_reminders.schedule_webhook_dispatch") as mock:
            await check_reminders(NOW, THRESHOLDS)
        thresholds = {c.args[2]["threshold"] for c in mock.call_args_list
                      if c.args[2]["milestone"] == "early_warning"}
        # à 30h : T-12h, T-2h et overdue sont tous franchis, mais un seul
        # rappel est émis (le plus sévère : overdue), les autres marqués envoyés
        assert thresholds == {"overdue"}

    async def test_jalon_soumis_pas_de_rappel(self, db_session, sample_tree):
        event = await _confirmed_event(db_session, sample_tree.id, "CVE-R4", 30)
        event.early_warning_submitted_at = NOW - timedelta(hours=1)
        await db_session.commit()
        with patch("app.services.enisa_reminders.schedule_webhook_dispatch") as mock:
            await check_reminders(NOW, THRESHOLDS)
        assert all(
            c.args[2]["milestone"] != "early_warning" for c in mock.call_args_list
        )

    async def test_isolation_erreur(self, db_session, sample_tree, monkeypatch):
        import app.services.enisa_reminders as mod

        def _boom(*a, **k):
            raise RuntimeError("down")

        monkeypatch.setattr(mod, "async_session_maker", _boom)
        await check_reminders(NOW, THRESHOLDS)  # ne doit pas lever


class TestWildcardExclusion:
    def test_wildcard_exclut_enisa(self):
        from app.services.webhook_dispatch import _event_matches

        assert _event_matches("on_act", ["*"]) is True
        assert _event_matches("enisa_deadline", ["*"]) is False
        assert _event_matches("enisa_deadline", ["enisa_deadline"]) is True
        assert _event_matches("enisa_deadline", ["*", "enisa_deadline"]) is True
