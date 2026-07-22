"""Tests des fonctions pures ENISA : échéances, pré-remplissage, fusion."""
from datetime import datetime, timedelta, timezone

from app.engine.enisa import (
    MILESTONES,
    build_milestone_content,
    compute_milestones,
    get_notifiable_node_ids,
    merge_draft,
    render_markdown,
)
from app.models.enisa import EnisaEvent

NOW = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)


def _event(**kwargs) -> EnisaEvent:
    base = dict(
        tree_id=1, cve_id="CVE-2026-1234", status="confirmed",
        detected_at=NOW - timedelta(hours=20),
        confirmed_at=NOW - timedelta(hours=10),
        affected_assets=[], evaluation_context={}, drafts={}, reminders_sent={},
    )
    base.update(kwargs)
    return EnisaEvent(**base)


class TestComputeMilestones:
    def test_non_confirme_aucun_jalon(self):
        event = _event(status="candidate", confirmed_at=None)
        assert compute_milestones(event, NOW) == {}

    def test_echeances_24h_72h(self):
        event = _event()  # confirmé il y a 10h
        m = compute_milestones(event, NOW)
        assert m["early_warning"]["due_at"] == event.confirmed_at + timedelta(hours=24)
        assert m["early_warning"]["remaining_seconds"] == 14 * 3600
        assert m["early_warning"]["overdue"] is False
        assert m["notification"]["due_at"] == event.confirmed_at + timedelta(hours=72)

    def test_depassement(self):
        event = _event(confirmed_at=NOW - timedelta(hours=30))
        m = compute_milestones(event, NOW)
        assert m["early_warning"]["overdue"] is True
        assert m["early_warning"]["remaining_seconds"] == 0

    def test_final_report_sans_correctif(self):
        event = _event(corrective_available_at=None)
        m = compute_milestones(event, NOW)
        assert m["final_report"]["due_at"] is None
        assert m["final_report"]["overdue"] is False

    def test_final_report_ancre_sur_correctif(self):
        corrective = NOW - timedelta(days=2)
        event = _event(corrective_available_at=corrective)
        m = compute_milestones(event, NOW)
        assert m["final_report"]["due_at"] == corrective + timedelta(days=14)

    def test_jalon_soumis_ni_retard_ni_compte_a_rebours(self):
        event = _event(
            confirmed_at=NOW - timedelta(hours=100),
            early_warning_submitted_at=NOW - timedelta(hours=90),
        )
        m = compute_milestones(event, NOW)
        assert m["early_warning"]["submitted_at"] is not None
        assert m["early_warning"]["overdue"] is False
        assert m["early_warning"]["remaining_seconds"] is None
        # la notification (72h), non soumise, est bien en retard
        assert m["notification"]["overdue"] is True


class TestBuildMilestoneContent:
    SETTINGS = {"manufacturer": {"name": "ACME Med", "contact": "cert@acme.example"}}

    def _event_with_context(self):
        return _event(
            affected_assets=[{"asset_id": "srv-prod-001", "criticality": "Critical"}],
            evaluation_context={
                "decision": "Act", "kev": True, "epss_score": 0.9,
                "cvss_score": 9.8,
                "sbom_components": [{"name": "openssl", "version": "3.0.1"}],
                "audit_trail": [{"node_label": "Exploitation", "value_found": True}],
            },
        )

    def test_early_warning_minimal(self):
        content = build_milestone_content(self._event_with_context(), "early_warning", self.SETTINGS)
        assert content["cve_id"] == "CVE-2026-1234"
        assert content["manufacturer"]["name"] == "ACME Med"
        assert content["exploitation_active"] is True
        # l'alerte précoce ne contient pas le détail des composants
        assert "sbom_components" not in content

    def test_notification_detaille(self):
        content = build_milestone_content(self._event_with_context(), "notification", self.SETTINGS)
        assert content["severity"]["cvss_score"] == 9.8
        assert content["affected_assets"][0]["asset_id"] == "srv-prod-001"
        assert content["sbom_components"][0]["name"] == "openssl"
        assert content["corrective_measures"] == ""  # champ libre à compléter

    def test_final_report_chronologie(self):
        event = self._event_with_context()
        event.corrective_available_at = NOW
        content = build_milestone_content(event, "final_report", self.SETTINGS)
        assert content["corrective_available_at"] == NOW.isoformat()
        assert content["timeline"]["detected_at"] == event.detected_at.isoformat()

    def test_settings_vides(self):
        content = build_milestone_content(self._event_with_context(), "early_warning", {})
        assert content["manufacturer"] == {}


class TestMergeAndRender:
    def test_merge_draft_ecrase(self):
        merged = merge_draft({"a": 1, "b": 2}, {"b": 99})
        assert merged == {"a": 1, "b": 99}

    def test_render_markdown_contient_cve(self):
        md = render_markdown({"cve_id": "CVE-2026-1234", "manufacturer": {"name": "ACME"}},
                             "early_warning")
        assert "CVE-2026-1234" in md
        assert "Early warning" in md


class TestNotifiableNodeIds:
    def test_extraction_depuis_structure(self):
        structure = {
            "nodes": [
                {"id": "out-1", "type": "output", "config": {"enisa_notifiable": True}},
                {"id": "out-2", "type": "output", "config": {}},
                {"id": "in-1", "type": "input", "config": {"enisa_notifiable": True}},
            ],
            "edges": [],
        }
        # seul un OUTPUT flaggé compte
        assert get_notifiable_node_ids(structure) == {"out-1"}

    def test_structure_vide(self):
        assert get_notifiable_node_ids({"nodes": [], "edges": []}) == set()
