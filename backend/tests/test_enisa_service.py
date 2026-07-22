"""Upsert des candidats ENISA : dédup, agrégation, redétection, isolation."""
import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.enisa import EnisaEvent
from app.schemas.evaluation import EvaluationResult
from app.services.enisa_service import record_candidates

STRUCTURE = {
    "nodes": [
        {"id": "out-act", "type": "output",
         "config": {"decision": "Act", "enisa_notifiable": True}},
        {"id": "out-track", "type": "output", "config": {"decision": "Track"}},
    ],
    "edges": [],
}


def _result(cve: str | None, node: str | None = "out-act") -> EvaluationResult:
    return EvaluationResult(vuln_id=cve, decision="Act", output_node_id=node)


def _vuln(cve: str | None, asset: str | None = None) -> dict:
    v = {"cve_id": cve, "kev": True, "cvss_score": 9.8}
    if asset:
        v["asset_id"] = asset
    return v


@pytest.fixture(autouse=True)
def _patch_session_maker(db_engine, monkeypatch):
    """record_candidates ouvre sa propre session (comme webhook_dispatch),
    indépendante de la requête HTTP. On la redirige vers la base éphémère
    de test (le sessionmaker global d'app.database pointe sur l'URL
    placeholder définie avant l'import de `app`)."""
    import app.services.enisa_service as svc

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(svc, "async_session_maker", maker)


@pytest.mark.asyncio
class TestRecordCandidates:
    async def _fetch_all(self, db_session):
        result = await db_session.execute(select(EnisaEvent))
        return list(result.scalars().all())

    async def test_creation_candidat(self, db_session, sample_tree):
        cve = "CVE-2026-0001"
        await record_candidates(
            sample_tree.id, STRUCTURE,
            [(_result(cve), _vuln(cve, "srv-prod-001"))],
        )
        events = await self._fetch_all(db_session)
        assert len(events) == 1
        assert events[0].status == "candidate"
        assert events[0].cve_id == cve
        assert events[0].affected_assets == [{"asset_id": "srv-prod-001"}]
        assert events[0].evaluation_context["decision"] == "Act"
        assert events[0].evaluation_context["kev"] is True

    async def test_dedup_meme_cve(self, db_session, sample_tree):
        cve = "CVE-2026-0002"
        pairs = [(_result(cve), _vuln(cve, "a1")), (_result(cve), _vuln(cve, "a2"))]
        await record_candidates(sample_tree.id, STRUCTURE, pairs)
        await record_candidates(sample_tree.id, STRUCTURE, pairs)
        events = await self._fetch_all(db_session)
        assert len(events) == 1
        # assets agrégés sans doublon
        assert sorted(a["asset_id"] for a in events[0].affected_assets) == ["a1", "a2"]

    async def test_output_non_flagge_ignore(self, db_session, sample_tree):
        await record_candidates(
            sample_tree.id, STRUCTURE,
            [(_result("CVE-2026-0003", node="out-track"), _vuln("CVE-2026-0003"))],
        )
        assert await self._fetch_all(db_session) == []

    async def test_sans_cve_ignore(self, db_session, sample_tree):
        await record_candidates(
            sample_tree.id, STRUCTURE, [(_result(None), _vuln(None))]
        )
        assert await self._fetch_all(db_session) == []

    async def test_redetection_apres_dismiss(self, db_session, sample_tree):
        cve = "CVE-2026-0004"
        await record_candidates(sample_tree.id, STRUCTURE, [(_result(cve), _vuln(cve))])
        events = await self._fetch_all(db_session)
        events[0].status = "dismissed"
        await db_session.commit()

        await record_candidates(sample_tree.id, STRUCTURE, [(_result(cve), _vuln(cve))])
        await db_session.refresh(events[0])
        assert events[0].status == "dismissed"  # PAS de réouverture auto
        assert events[0].redetection_count == 1

    async def test_conflit_insertion_concurrente_ne_perd_pas_le_lot(self, db_session, sample_tree):
        """Deux appels concurrents découvrant le même nouveau CVE ne doivent
        perdre aucun candidat, y compris les CVE sans rapport avec la
        collision présents dans chaque lot.

        record_candidates ouvre sa propre session par appel (comme
        webhook_dispatch) : exécuter deux appels réels via asyncio.gather
        reproduit fidèlement la race SELECT-puis-INSERT sur deux connexions
        Postgres distinctes (le second INSERT bloque jusqu'au commit du
        premier, puis lève IntegrityError sur uq_enisa_events_tree_cve —
        exactement le scénario décrit par la revue)."""
        shared_cve = "CVE-2026-0006"
        pair_a = [
            (_result(shared_cve), _vuln(shared_cve, "asset-a")),
            (_result("CVE-2026-0007"), _vuln("CVE-2026-0007", "asset-x")),
        ]
        pair_b = [
            (_result(shared_cve), _vuln(shared_cve, "asset-b")),
            (_result("CVE-2026-0008"), _vuln("CVE-2026-0008", "asset-y")),
        ]

        await asyncio.gather(
            record_candidates(sample_tree.id, STRUCTURE, pair_a),
            record_candidates(sample_tree.id, STRUCTURE, pair_b),
        )

        events = await self._fetch_all(db_session)
        by_cve = {e.cve_id: e for e in events}

        # Aucun candidat perdu : les 3 CVE distincts du lot combiné sont présents.
        assert set(by_cve.keys()) == {shared_cve, "CVE-2026-0007", "CVE-2026-0008"}

        # Le CVE en collision a bien agrégé les assets des deux appels
        # concurrents (pas juste celui du "gagnant" de la course).
        shared_assets = sorted(a["asset_id"] for a in by_cve[shared_cve].affected_assets)
        assert shared_assets == ["asset-a", "asset-b"]

        # Les CVE non concurrents de chaque lot ne sont pas affectés.
        assert by_cve["CVE-2026-0007"].affected_assets == [{"asset_id": "asset-x"}]
        assert by_cve["CVE-2026-0008"].affected_assets == [{"asset_id": "asset-y"}]

    async def test_isolation_des_erreurs(self, db_session, sample_tree, monkeypatch):
        """Une panne interne ne doit jamais remonter à l'appelant."""
        import app.services.enisa_service as svc

        def _boom(*args, **kwargs):
            raise RuntimeError("db down")

        monkeypatch.setattr(svc, "async_session_maker", _boom)
        # Ne doit PAS lever
        await record_candidates(
            sample_tree.id, STRUCTURE,
            [(_result("CVE-2026-0005"), _vuln("CVE-2026-0005"))],
        )
