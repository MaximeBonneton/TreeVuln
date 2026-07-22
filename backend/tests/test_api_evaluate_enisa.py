"""Intégration : hook record_candidates branché sur les routes d'évaluation
(Task 4, Phase 3 CRA). Couvre /single et /evaluate (batch) — les deux motifs
de construction des paires (résultat, vuln) réutilisés à l'identique par
/csv et les routes /tree/{slug}."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.enisa import EnisaEvent

pytestmark = pytest.mark.asyncio

TREE = {
    "nodes": [
        {"id": "in-cvss", "type": "input", "label": "CVSS",
         "config": {"field": "cvss_score"},
         "conditions": [
             {"label": "Critical", "operator": "gte", "value": 9.0},
             {"label": "Low", "operator": "lt", "value": 9.0},
         ]},
        {"id": "out-act", "type": "output", "label": "Act",
         "config": {"decision": "Act", "color": "#dc2626", "enisa_notifiable": True}},
        {"id": "out-track", "type": "output", "label": "Track",
         "config": {"decision": "Track", "color": "#22c55e"}},
    ],
    "edges": [
        {"id": "e0", "source": "in-cvss", "target": "out-act", "source_handle": "handle-0"},
        {"id": "e1", "source": "in-cvss", "target": "out-track", "source_handle": "handle-1"},
    ],
}


@pytest.fixture(autouse=True)
def _patch_session_maker(db_engine, monkeypatch):
    """record_candidates ouvre sa propre session : on la redirige vers la
    base éphémère de test (comme pour les autres services fire-and-forget)."""
    import app.services.enisa_service as svc

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(svc, "async_session_maker", maker)


async def _create_tree(admin_client, default: bool = False) -> int:
    resp = await admin_client.post("/api/v1/tree", json={"name": "Enisa Eval Tree", "structure": TREE})
    assert resp.status_code == 201, resp.text
    tree_id = resp.json()["id"]
    if default:
        await admin_client.put(f"/api/v1/tree/{tree_id}/set-default")
    return tree_id


async def test_evaluate_single_cree_candidat_enisa(admin_client, db_session):
    await _create_tree(admin_client, default=True)

    resp = await admin_client.post("/api/v1/evaluate/single", json={
        "vulnerability": {"cve_id": "CVE-2026-1001", "cvss_score": 9.8, "asset_id": "srv-prod-001"},
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["decision"] == "Act"

    events = (await db_session.execute(select(EnisaEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].cve_id == "CVE-2026-1001"
    assert events[0].affected_assets == [{"asset_id": "srv-prod-001"}]


async def test_evaluate_single_output_non_flagge_ne_cree_rien(admin_client, db_session):
    await _create_tree(admin_client, default=True)

    resp = await admin_client.post("/api/v1/evaluate/single", json={
        "vulnerability": {"cve_id": "CVE-2026-1002", "cvss_score": 1.0},
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["decision"] == "Track"

    events = (await db_session.execute(select(EnisaEvent))).scalars().all()
    assert events == []


async def test_evaluate_batch_cree_candidats_enisa(admin_client, db_session):
    await _create_tree(admin_client, default=True)

    resp = await admin_client.post("/api/v1/evaluate", json={
        "vulnerabilities": [
            {"cve_id": "CVE-2026-2001", "cvss_score": 9.9, "asset_id": "srv-a"},
            {"cve_id": "CVE-2026-2002", "cvss_score": 1.0, "asset_id": "srv-b"},
        ],
    })
    assert resp.status_code == 200, resp.text

    events = (await db_session.execute(select(EnisaEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].cve_id == "CVE-2026-2001"
    assert events[0].affected_assets == [{"asset_id": "srv-a"}]
