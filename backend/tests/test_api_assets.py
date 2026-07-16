"""
Tests d'intégration des routes assets (T-2, plan WS5).

Couvrent : CRUD scopé par arbre, garde d'unicité (tree_id, asset_id),
filtrage, et import CSV en masse (preview + import + doublons).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _create_tree(client, name="Assets Tree"):
    resp = await client.post("/api/v1/tree", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestAssetCrud:
    async def test_create_and_list_asset(self, admin_client):
        tree_id = await _create_tree(admin_client)
        resp = await admin_client.post(
            f"/api/v1/assets?tree_id={tree_id}",
            json={"asset_id": "srv-1", "name": "Server 1", "criticality": "High"},
        )
        assert resp.status_code == 201, resp.text

        listing = await admin_client.get(f"/api/v1/assets?tree_id={tree_id}")
        assert listing.status_code == 200
        assert {a["asset_id"] for a in listing.json()} == {"srv-1"}

    async def test_duplicate_asset_id_conflict(self, admin_client):
        tree_id = await _create_tree(admin_client)
        payload = {"asset_id": "srv-1", "criticality": "High"}
        await admin_client.post(f"/api/v1/assets?tree_id={tree_id}", json=payload)
        resp = await admin_client.post(f"/api/v1/assets?tree_id={tree_id}", json=payload)
        assert resp.status_code == 409

    async def test_assets_are_scoped_by_tree(self, admin_client):
        tree_a = await _create_tree(admin_client, "A")
        tree_b = await _create_tree(admin_client, "B")
        await admin_client.post(
            f"/api/v1/assets?tree_id={tree_a}",
            json={"asset_id": "only-in-a", "criticality": "Low"},
        )
        listing_b = await admin_client.get(f"/api/v1/assets?tree_id={tree_b}")
        assert listing_b.json() == []

    async def test_update_and_delete_asset(self, admin_client):
        tree_id = await _create_tree(admin_client)
        await admin_client.post(
            f"/api/v1/assets?tree_id={tree_id}",
            json={"asset_id": "srv-1", "criticality": "Low"},
        )
        upd = await admin_client.put(
            f"/api/v1/assets/srv-1?tree_id={tree_id}",
            json={"criticality": "Critical"},
        )
        assert upd.status_code == 200
        assert upd.json()["criticality"] == "Critical"

        dele = await admin_client.delete(f"/api/v1/assets/srv-1?tree_id={tree_id}")
        assert dele.status_code == 204

    async def test_filter_by_criticality(self, admin_client):
        tree_id = await _create_tree(admin_client)
        await admin_client.post(
            f"/api/v1/assets?tree_id={tree_id}",
            json={"asset_id": "high-1", "criticality": "High"},
        )
        await admin_client.post(
            f"/api/v1/assets?tree_id={tree_id}",
            json={"asset_id": "low-1", "criticality": "Low"},
        )
        resp = await admin_client.get(
            f"/api/v1/assets?tree_id={tree_id}&criticality=High"
        )
        assert {a["asset_id"] for a in resp.json()} == {"high-1"}


class TestAssetImport:
    _CSV = b"asset_id,name,criticality\nsrv-1,Web,High\nsrv-2,DB,Critical\n"

    async def test_import_preview_detects_columns(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/assets/import/preview",
            files={"file": ("assets.csv", self._CSV, "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["row_count"] == 2
        assert "asset_id" in body["columns"]

    async def test_import_creates_assets(self, admin_client):
        tree_id = await _create_tree(admin_client)
        resp = await admin_client.post(
            f"/api/v1/assets/import?tree_id={tree_id}"
            "&col_asset_id=asset_id&col_name=name&col_criticality=criticality",
            files={"file": ("assets.csv", self._CSV, "text/csv")},
        )
        assert resp.status_code == 200, resp.text
        listing = await admin_client.get(f"/api/v1/assets?tree_id={tree_id}")
        assert {a["asset_id"] for a in listing.json()} == {"srv-1", "srv-2"}

    async def test_import_with_duplicate_rows_does_not_500(self, admin_client):
        """C-8 : deux lignes avec le même asset_id ne doivent pas planter."""
        tree_id = await _create_tree(admin_client)
        csv = b"asset_id,criticality\nsrv-dup,High\nsrv-dup,Low\n"
        resp = await admin_client.post(
            f"/api/v1/assets/import?tree_id={tree_id}&col_asset_id=asset_id&col_criticality=criticality",
            files={"file": ("dup.csv", csv, "text/csv")},
        )
        assert resp.status_code == 200, resp.text
        listing = await admin_client.get(f"/api/v1/assets?tree_id={tree_id}")
        assert {a["asset_id"] for a in listing.json()} == {"srv-dup"}
