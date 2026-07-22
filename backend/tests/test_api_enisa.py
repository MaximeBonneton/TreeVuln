"""Tests d'intégration des routes /api/v1/enisa/*."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enisa import EnisaEvent

pytestmark = pytest.mark.asyncio


async def _create_event(db_session, tree_id: int, cve: str, **kwargs) -> EnisaEvent:
    event = EnisaEvent(tree_id=tree_id, cve_id=cve, **kwargs)
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


class TestEnisaRoutes:
    async def test_liste_filtre_statut(self, admin_client, db_session, sample_tree):
        await _create_event(db_session, sample_tree.id, "CVE-1")
        await _create_event(
            db_session, sample_tree.id, "CVE-2",
            status="confirmed", confirmed_at=datetime.now(timezone.utc),
        )
        resp = await admin_client.get(
            f"/api/v1/enisa/events?tree_id={sample_tree.id}&status=candidate"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [e["cve_id"] for e in data["events"]] == ["CVE-1"]

    async def test_detail_contient_jalons(self, admin_client, db_session, sample_tree):
        event = await _create_event(
            db_session, sample_tree.id, "CVE-3",
            status="confirmed",
            confirmed_at=datetime.now(timezone.utc) - timedelta(hours=10),
        )
        resp = await admin_client.get(f"/api/v1/enisa/events/{event.id}")
        assert resp.status_code == 200
        milestones = resp.json()["milestones"]
        assert milestones["early_warning"]["overdue"] is False
        assert milestones["final_report"]["due_at"] is None

    async def test_confirm(self, admin_client, db_session, sample_tree):
        event = await _create_event(db_session, sample_tree.id, "CVE-4")
        resp = await admin_client.post(f"/api/v1/enisa/events/{event.id}/confirm")
        assert resp.status_code == 200
        await db_session.refresh(event)
        assert event.status == "confirmed"
        assert event.confirmed_at is not None
        assert event.confirmed_by  # username tracé

    async def test_confirm_deja_confirme_409(self, admin_client, db_session, sample_tree):
        event = await _create_event(
            db_session, sample_tree.id, "CVE-5",
            status="confirmed", confirmed_at=datetime.now(timezone.utc),
        )
        resp = await admin_client.post(f"/api/v1/enisa/events/{event.id}/confirm")
        assert resp.status_code == 409

    async def test_dismiss_motif_obligatoire(self, admin_client, db_session, sample_tree):
        event = await _create_event(db_session, sample_tree.id, "CVE-6")
        resp = await admin_client.post(f"/api/v1/enisa/events/{event.id}/dismiss", json={})
        assert resp.status_code == 422
        resp = await admin_client.post(
            f"/api/v1/enisa/events/{event.id}/dismiss",
            json={"reason": "faux positif"},
        )
        assert resp.status_code == 200
        await db_session.refresh(event)
        assert event.status == "dismissed"
        assert event.dismiss_reason == "faux positif"

    async def test_close_sans_jalons_motif_obligatoire(
        self, admin_client, db_session, sample_tree
    ):
        event = await _create_event(
            db_session, sample_tree.id, "CVE-7",
            status="confirmed", confirmed_at=datetime.now(timezone.utc),
        )
        resp = await admin_client.post(f"/api/v1/enisa/events/{event.id}/close", json={})
        assert resp.status_code == 409  # jalons non soumis, pas de motif
        resp = await admin_client.post(
            f"/api/v1/enisa/events/{event.id}/close",
            json={"reason": "hors périmètre CRA"},
        )
        assert resp.status_code == 200

    async def test_submit_milestone(self, admin_client, db_session, sample_tree):
        event = await _create_event(
            db_session, sample_tree.id, "CVE-8",
            status="confirmed", confirmed_at=datetime.now(timezone.utc),
        )
        resp = await admin_client.post(
            f"/api/v1/enisa/events/{event.id}/submit/early_warning"
        )
        assert resp.status_code == 200
        await db_session.refresh(event)
        assert event.early_warning_submitted_at is not None
        assert event.early_warning_submitted_by

    async def test_milestone_invalide_422(self, admin_client, db_session, sample_tree):
        event = await _create_event(db_session, sample_tree.id, "CVE-9")
        resp = await admin_client.post(f"/api/v1/enisa/events/{event.id}/submit/bogus")
        assert resp.status_code == 422

    async def test_draft_et_export(self, admin_client, db_session, sample_tree):
        event = await _create_event(
            db_session, sample_tree.id, "CVE-10",
            status="confirmed", confirmed_at=datetime.now(timezone.utc),
            evaluation_context={"decision": "Act", "kev": True},
        )
        resp = await admin_client.put(
            f"/api/v1/enisa/events/{event.id}/draft/notification",
            json={"fields": {"corrective_measures": "patch appliqué"}},
        )
        assert resp.status_code == 200
        resp = await admin_client.get(
            f"/api/v1/enisa/events/{event.id}/export/notification?format=json"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["cve_id"] == "CVE-10"
        assert body["corrective_measures"] == "patch appliqué"  # brouillon fusionné
        resp = await admin_client.get(
            f"/api/v1/enisa/events/{event.id}/export/notification?format=markdown"
        )
        assert resp.status_code == 200
        assert "CVE-10" in resp.text

    async def test_corrective_date(self, admin_client, db_session, sample_tree):
        event = await _create_event(
            db_session, sample_tree.id, "CVE-11",
            status="confirmed", confirmed_at=datetime.now(timezone.utc),
        )
        resp = await admin_client.put(
            f"/api/v1/enisa/events/{event.id}/corrective-date",
            json={"corrective_available_at": "2026-07-25T00:00:00Z"},
        )
        assert resp.status_code == 200
        assert resp.json()["milestones"]["final_report"]["due_at"] is not None

    async def test_summary(self, admin_client, db_session, sample_tree):
        await _create_event(db_session, sample_tree.id, "CVE-12")
        await _create_event(
            db_session, sample_tree.id, "CVE-13",
            status="confirmed",
            confirmed_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        resp = await admin_client.get(f"/api/v1/enisa/summary?tree_id={sample_tree.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["candidates"] == 1
        assert data["confirmed"] == 1
        assert data["overdue_milestones"] == 1  # early_warning de CVE-13 dépassée

    async def test_non_authentifie_401(self, client, db_session, sample_tree):
        resp = await client.get(f"/api/v1/enisa/events?tree_id={sample_tree.id}")
        assert resp.status_code == 401
