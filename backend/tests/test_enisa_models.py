"""Tests d'introspection du modèle EnisaEvent (Phase 3 CRA)."""
from sqlalchemy import inspect

from app.models.enisa import EnisaEvent


class TestEnisaEventModel:
    def test_tablename(self):
        assert EnisaEvent.__tablename__ == "enisa_events"

    def test_colonnes_chrono(self):
        cols = {c.key for c in inspect(EnisaEvent).columns}
        assert {
            "id", "tree_id", "cve_id", "status",
            "detected_at", "last_detected_at", "confirmed_at",
            "corrective_available_at", "dismissed_at", "closed_at",
            "early_warning_submitted_at", "notification_submitted_at",
            "final_report_submitted_at",
            "early_warning_submitted_by", "notification_submitted_by",
            "final_report_submitted_by",
            "affected_assets", "evaluation_context", "drafts", "reminders_sent",
            "confirmed_by", "dismissed_by", "dismiss_reason", "close_reason",
            "redetection_count", "created_at", "updated_at",
        } <= cols

    def test_unicite_tree_cve(self):
        uniques = [
            c for c in EnisaEvent.__table__.constraints
            if c.name == "uq_enisa_events_tree_cve"
        ]
        assert len(uniques) == 1
        assert {col.name for col in uniques[0].columns} == {"tree_id", "cve_id"}

    def test_cascade_arbre(self):
        fk = next(iter(EnisaEvent.__table__.columns["tree_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_defauts(self):
        event = EnisaEvent(tree_id=1, cve_id="CVE-2026-0001")
        # Les défauts Python sont appliqués à l'insertion ; on vérifie ici
        # les défauts déclarés au niveau colonne
        assert EnisaEvent.__table__.columns["status"].default.arg == "candidate"
        assert EnisaEvent.__table__.columns["redetection_count"].default.arg == 0
