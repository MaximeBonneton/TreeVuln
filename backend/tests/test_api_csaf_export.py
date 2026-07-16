"""Tests d'intégration de l'export CSAF (bundle ZIP signé)."""
import io
import json
import zipfile

import pytest

from tests.conftest import TEST_PASSPHRASE

pytestmark = pytest.mark.asyncio

PUBLISHER = {
    "name": "ACME Medical",
    "namespace": "https://acme-medical.example.com",
    "category": "vendor",
}

# Arbre : kev=true -> Act (affected), sinon -> Track (not_affected)
TREE_STRUCTURE = {
    "nodes": [
        {"id": "in-1", "type": "input", "label": "KEV",
         "config": {"field": "kev"},
         "conditions": [
             {"label": "active", "operator": "eq", "value": True},
             {"label": "no", "operator": "neq", "value": True},
         ]},
        {"id": "out-act", "type": "output", "label": "Act",
         "config": {"decision": "Act", "color": "#dc2626",
                    "vex_status": "affected"}},
        {"id": "out-track", "type": "output", "label": "Track",
         "config": {"decision": "Track", "color": "#22c55e",
                    "vex_status": "not_affected",
                    "vex_justification": "component_not_present"}},
    ],
    "edges": [
        {"id": "e1", "source": "in-1", "target": "out-act",
         "source_handle": "handle-0"},
        {"id": "e2", "source": "in-1", "target": "out-track",
         "source_handle": "handle-1"},
    ],
}


async def _setup_tree_and_assets(admin_client) -> int:
    """Crée un arbre par défaut avec vex_status + un asset, retourne tree_id."""
    resp = await admin_client.post(
        "/api/v1/tree",
        json={"name": "CSAF tree", "structure": TREE_STRUCTURE},
    )
    assert resp.status_code in (200, 201), resp.text
    tree_id = resp.json()["id"]
    resp = await admin_client.put(f"/api/v1/tree/{tree_id}/set-default")
    assert resp.status_code == 200, resp.text
    resp = await admin_client.post(
        f"/api/v1/assets?tree_id={tree_id}",
        json={"asset_id": "srv-prod-001", "name": "Production Web Server",
              "criticality": "Critical"},
    )
    assert resp.status_code in (200, 201), resp.text
    return tree_id


async def _configure_publisher(admin_client, with_key: bool = False, test_pgp_key=None):
    payload: dict = {"publisher": PUBLISHER}
    if with_key:
        payload["signing_key"] = test_pgp_key
        payload["signing_key_passphrase"] = TEST_PASSPHRASE
    resp = await admin_client.put("/api/v1/settings/csaf", json=payload)
    assert resp.status_code == 200, resp.text


BATCH = {
    "vulnerabilities": [
        {"cve_id": "CVE-2024-0001", "kev": True, "asset_id": "srv-prod-001"},
        {"cve_id": "CVE-2024-0002", "kev": False, "asset_id": "srv-prod-001"},
        # Exclu : asset inconnu
        {"cve_id": "CVE-2024-0003", "kev": True, "asset_id": "srv-inconnu"},
    ],
    "format": "csaf",
    "signed": False,
}


class TestCsafExport:
    async def test_export_csaf_non_signe(self, admin_client):
        await _setup_tree_and_assets(admin_client)
        await _configure_publisher(admin_client)

        resp = await admin_client.post("/api/v1/evaluate/export", json=BATCH)
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/zip"

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        json_name = next(n for n in names if n.endswith(".json")
                         and n != "exclusions.json")
        assert f"{json_name}.sha256" in names
        assert f"{json_name}.sha512" in names
        assert f"{json_name}.asc" not in names  # non signé
        assert "exclusions.json" in names

        doc = json.loads(zf.read(json_name))
        assert doc["document"]["category"] == "csaf_vex"
        cves = [v["cve"] for v in doc["vulnerabilities"]]
        assert cves == ["CVE-2024-0001", "CVE-2024-0002"]

        exclusions = json.loads(zf.read("exclusions.json"))
        assert len(exclusions) == 1
        assert exclusions[0]["reason"] == "unknown_asset: srv-inconnu"

    async def test_export_csaf_signe(self, admin_client, test_pgp_key):
        await _setup_tree_and_assets(admin_client)
        await _configure_publisher(admin_client, with_key=True,
                                   test_pgp_key=test_pgp_key)

        resp = await admin_client.post(
            "/api/v1/evaluate/export", json={**BATCH, "signed": True}
        )
        assert resp.status_code == 200, resp.text
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        asc = next(n for n in zf.namelist() if n.endswith(".asc"))
        assert zf.read(asc).startswith(b"-----BEGIN PGP SIGNATURE-----")

    async def test_hashes_correspondent_au_document(self, admin_client):
        await _setup_tree_and_assets(admin_client)
        await _configure_publisher(admin_client)

        resp = await admin_client.post("/api/v1/evaluate/export", json=BATCH)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        json_name = next(n for n in zf.namelist() if n.endswith(".json")
                         and n != "exclusions.json")
        import hashlib
        content = zf.read(json_name)
        sha256_line = zf.read(f"{json_name}.sha256").decode()
        assert sha256_line == f"{hashlib.sha256(content).hexdigest()}  {json_name}\n"

    async def test_sans_publisher_422(self, admin_client):
        await _setup_tree_and_assets(admin_client)
        resp = await admin_client.post("/api/v1/evaluate/export", json=BATCH)
        assert resp.status_code == 422
        assert "publisher" in resp.json()["detail"].lower()

    async def test_signed_sans_cle_409(self, admin_client):
        await _setup_tree_and_assets(admin_client)
        await _configure_publisher(admin_client)
        resp = await admin_client.post(
            "/api/v1/evaluate/export", json={**BATCH, "signed": True}
        )
        assert resp.status_code == 409

    async def test_aucun_item_exportable_422(self, admin_client):
        await _setup_tree_and_assets(admin_client)
        await _configure_publisher(admin_client)
        resp = await admin_client.post(
            "/api/v1/evaluate/export",
            json={
                "vulnerabilities": [
                    {"cve_id": "CVE-2024-0001", "kev": True,
                     "asset_id": "srv-inconnu"},
                ],
                "format": "csaf", "signed": False,
            },
        )
        assert resp.status_code == 422

    async def test_formats_csv_json_inchanges(self, admin_client):
        await _setup_tree_and_assets(admin_client)
        resp = await admin_client.post(
            "/api/v1/evaluate/export",
            json={"vulnerabilities": [{"cve_id": "CVE-2024-0001", "kev": True}],
                  "format": "csv"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
