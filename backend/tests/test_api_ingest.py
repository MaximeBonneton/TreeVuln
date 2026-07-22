"""
Tests d'intégration de l'ingestion et du field mapping (T-2, plan WS5).

Ingestion : création d'endpoint (clé API en clair une seule fois),
authentification X-API-Key, auto-évaluation. Field mapping : scan
CSV/JSON avec inférence de types, champs CVSS virtuels.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.enisa import EnisaEvent

pytestmark = pytest.mark.asyncio


def _tree_structure() -> dict:
    return {
        "nodes": [
            {
                "id": "input-cvss",
                "type": "input",
                "label": "CVSS",
                "config": {"field": "cvss_score"},
                "conditions": [
                    {"operator": "gte", "value": 9.0, "label": "Critical"},
                    {"operator": "lt", "value": 9.0, "label": "Low"},
                ],
            },
            {"id": "out-act", "type": "output", "label": "Act",
             "config": {"decision": "Act", "color": "#f00"}, "conditions": []},
            {"id": "out-track", "type": "output", "label": "Track",
             "config": {"decision": "Track", "color": "#0f0"}, "conditions": []},
        ],
        "edges": [
            {"id": "e0", "source": "input-cvss", "target": "out-act", "source_handle": "handle-0"},
            {"id": "e1", "source": "input-cvss", "target": "out-track", "source_handle": "handle-1"},
        ],
        "metadata": {},
    }


async def _create_tree(client):
    resp = await client.post(
        "/api/v1/tree", json={"name": "Ingest Tree", "structure": _tree_structure()}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestIngestEndpoint:
    async def test_create_endpoint_returns_api_key_once(self, admin_client):
        tree_id = await _create_tree(admin_client)
        resp = await admin_client.post(
            f"/api/v1/tree/{tree_id}/ingest-endpoints",
            json={"name": "SIEM", "slug": "siem-1", "field_mapping": {}},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["api_key"], "la clé API doit être renvoyée en clair à la création"

        # Le listing masque la clé (has_api_key seulement)
        listing = await admin_client.get(f"/api/v1/tree/{tree_id}/ingest-endpoints")
        assert listing.status_code == 200
        assert listing.json()[0]["has_api_key"] is True
        assert "api_key" not in listing.json()[0]

    async def test_ingest_requires_valid_api_key(self, admin_client):
        tree_id = await _create_tree(admin_client)
        await admin_client.post(
            f"/api/v1/tree/{tree_id}/ingest-endpoints",
            json={"name": "SIEM", "slug": "siem-2", "field_mapping": {}},
        )
        resp = await admin_client.post(
            "/api/v1/ingest/siem-2",
            json=[{"cve_id": "CVE-1", "cvss_score": 9.5}],
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 403

    async def test_ingest_auto_evaluates(self, admin_client):
        tree_id = await _create_tree(admin_client)
        created = await admin_client.post(
            f"/api/v1/tree/{tree_id}/ingest-endpoints",
            json={"name": "SIEM", "slug": "siem-3", "field_mapping": {}, "auto_evaluate": True},
        )
        api_key = created.json()["api_key"]

        resp = await admin_client.post(
            "/api/v1/ingest/siem-3",
            json=[
                {"cve_id": "CVE-1", "cvss_score": 9.5},
                {"cve_id": "CVE-2", "cvss_score": 4.0},
            ],
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["received"] == 2
        assert body["evaluated"] == 2
        assert body["errors"] == 0

    async def test_ingest_unknown_slug_404(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/ingest/does-not-exist",
            json=[{"cve_id": "CVE-1"}],
            headers={"X-API-Key": "whatever"},
        )
        assert resp.status_code == 404


class TestIngestEnisaWiring:
    """Vérifie le hook record_candidates branché sur l'auto-évaluation
    d'ingestion (Task 4), y compris la reconstruction des vulns mappées
    (transform_payload) que _ingest_entries_sync ne renvoie pas telles
    quelles dans IngestResult (compatibilité API)."""

    @pytest.fixture(autouse=True)
    def _patch_session_maker(self, db_engine, monkeypatch):
        import app.services.enisa_service as svc

        maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        monkeypatch.setattr(svc, "async_session_maker", maker)

    def _notifiable_structure(self) -> dict:
        structure = _tree_structure()
        structure["nodes"][1]["config"]["enisa_notifiable"] = True  # out-act
        return structure

    async def test_ingest_auto_evaluate_cree_candidat_enisa(self, admin_client, db_session):
        resp = await admin_client.post(
            "/api/v1/tree", json={"name": "Enisa Ingest Tree", "structure": self._notifiable_structure()}
        )
        assert resp.status_code == 201, resp.text
        tree_id = resp.json()["id"]

        created = await admin_client.post(
            f"/api/v1/tree/{tree_id}/ingest-endpoints",
            json={
                "name": "SIEM",
                "slug": "siem-enisa",
                # Mapping depuis des noms de champs sources vers les champs TreeVuln
                "field_mapping": {"vulnId": "cve_id", "score": "cvss_score", "assetRef": "asset_id"},
                "auto_evaluate": True,
            },
        )
        assert created.status_code == 201, created.text
        api_key = created.json()["api_key"]

        resp = await admin_client.post(
            "/api/v1/ingest/siem-enisa",
            json=[{"vulnId": "CVE-2026-9001", "score": 9.9, "assetRef": "srv-prod-001"}],
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["evaluated"] == 1

        events = (await db_session.execute(select(EnisaEvent))).scalars().all()
        assert len(events) == 1
        assert events[0].cve_id == "CVE-2026-9001"
        assert events[0].tree_id == tree_id
        assert events[0].affected_assets == [{"asset_id": "srv-prod-001"}]
        assert events[0].evaluation_context["cvss_score"] == 9.9

    async def test_ingest_sans_flag_enisa_ne_cree_rien(self, admin_client, db_session):
        """Un arbre sans nœud enisa_notifiable ne doit créer aucun événement."""
        tree_id = await _create_tree(admin_client)
        created = await admin_client.post(
            f"/api/v1/tree/{tree_id}/ingest-endpoints",
            json={"name": "SIEM", "slug": "siem-no-flag", "field_mapping": {}, "auto_evaluate": True},
        )
        api_key = created.json()["api_key"]

        resp = await admin_client.post(
            "/api/v1/ingest/siem-no-flag",
            json=[{"cve_id": "CVE-2026-9002", "cvss_score": 9.9}],
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200, resp.text

        events = (await db_session.execute(select(EnisaEvent))).scalars().all()
        assert events == []


class TestFieldMappingScan:
    async def test_scan_csv_infers_types(self, admin_client):
        csv = b"cve_id,cvss_score,kev\nCVE-1,9.8,true\nCVE-2,4.0,false\n"
        resp = await admin_client.post(
            "/api/v1/mapping/scan",
            files={"file": ("vulns.csv", csv, "text/csv")},
        )
        assert resp.status_code == 200, resp.text
        fields = {f["name"]: f["type"] for f in resp.json()["fields"]}
        assert fields["cve_id"] == "string"
        assert fields["cvss_score"] == "number"
        assert fields["kev"] == "boolean"

    async def test_scan_json_array(self, admin_client):
        data = b'[{"cve_id": "CVE-1", "epss_score": 0.5}, {"cve_id": "CVE-2", "epss_score": 0.1}]'
        resp = await admin_client.post(
            "/api/v1/mapping/scan",
            files={"file": ("vulns.json", data, "application/json")},
        )
        assert resp.status_code == 200, resp.text
        fields = {f["name"] for f in resp.json()["fields"]}
        assert {"cve_id", "epss_score"} <= fields

    async def test_cvss_fields_definitions(self, admin_client):
        resp = await admin_client.get("/api/v1/mapping/cvss-fields")
        assert resp.status_code == 200
        names = {f["name"] for f in resp.json()}
        assert "cvss_av" in names  # attack vector virtuel
