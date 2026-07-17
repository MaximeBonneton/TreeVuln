"""Tests d'intégration des routes SBOM (/assets/{asset_id}/sbom)."""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio

FIXTURES = Path(__file__).parent / "fixtures"


async def _create_tree_and_asset(admin_client) -> int:
    resp = await admin_client.post(
        "/api/v1/tree",
        json={"name": "SBOM tree", "structure": {"nodes": [], "edges": []}},
    )
    assert resp.status_code in (200, 201), resp.text
    tree_id = resp.json()["id"]
    resp = await admin_client.post(
        f"/api/v1/assets?tree_id={tree_id}",
        json={"asset_id": "srv-app-001", "name": "App Server", "criticality": "High"},
    )
    assert resp.status_code in (200, 201), resp.text
    return tree_id


def _upload_files(fixture: str = "sbom_cyclonedx.json"):
    content = (FIXTURES / fixture).read_bytes()
    return {"file": (fixture, content, "application/json")}


class TestUploadSbom:
    async def test_upload_cyclonedx(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        resp = await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}",
            files=_upload_files(),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["format"] == "cyclonedx"
        assert body["spec_version"] == "1.5"
        assert body["component_count"] == 3
        assert len(body["warnings"]) == 1  # composant sans nom ignoré

    async def test_upload_spdx(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        resp = await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}",
            files=_upload_files("sbom_spdx.json"),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["format"] == "spdx"

    async def test_reimport_remplace(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}", files=_upload_files()
        )
        resp = await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}",
            files=_upload_files("sbom_spdx.json"),
        )
        assert resp.status_code == 201
        # Le GET reflète le dernier import (remplacement complet)
        resp = await admin_client.get(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        body = resp.json()
        assert body["format"] == "spdx"
        assert body["component_count"] == 2

    async def test_asset_inconnu_404(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        resp = await admin_client.post(
            f"/api/v1/assets/srv-inconnu/sbom?tree_id={tree_id}", files=_upload_files()
        )
        assert resp.status_code == 404

    async def test_format_inconnu_400(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        resp = await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}",
            files={"file": ("x.json", json.dumps({"a": 1}).encode(), "application/json")},
        )
        assert resp.status_code == 400

    async def test_sans_composant_400(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        empty = json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5"}).encode()
        resp = await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}",
            files={"file": ("empty.json", empty, "application/json")},
        )
        assert resp.status_code == 400
        # L'échec ne doit rien avoir remplacé : toujours pas de SBOM
        resp = await admin_client.get(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        assert resp.status_code == 404


class TestGetSbom:
    async def test_get_avec_composants_pagines(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}", files=_upload_files()
        )
        resp = await admin_client.get(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}&limit=2&offset=0"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_components"] == 3
        assert len(body["components"]) == 2
        assert {"purl", "name", "version", "component_type"} <= set(body["components"][0])

    async def test_get_sans_sbom_404(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        resp = await admin_client.get(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        assert resp.status_code == 404


class TestDeleteSbom:
    async def test_delete(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}", files=_upload_files()
        )
        resp = await admin_client.delete(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        assert resp.status_code == 204
        resp = await admin_client.get(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        assert resp.status_code == 404

    async def test_delete_sans_sbom_404(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        resp = await admin_client.delete(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        assert resp.status_code == 404


class TestSummary:
    async def test_resume_par_arbre(self, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        # 2e asset sans SBOM : absent du résumé
        await admin_client.post(
            f"/api/v1/assets?tree_id={tree_id}",
            json={"asset_id": "srv-app-002", "criticality": "Low"},
        )
        await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}", files=_upload_files()
        )
        resp = await admin_client.get(f"/api/v1/assets/sbom/summary?tree_id={tree_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["asset_id"] == "srv-app-001"
        assert body[0]["component_count"] == 3


class TestPermissions:
    async def test_upload_interdit_operator(self, client, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        # Créer et activer un operator (pattern test_api_settings)
        from tests.test_api_settings import _make_operator_client

        operator = await _make_operator_client(client, admin_client)
        resp = await operator.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}", files=_upload_files()
        )
        assert resp.status_code == 403

    async def test_lecture_ouverte_operator(self, client, admin_client):
        tree_id = await _create_tree_and_asset(admin_client)
        await admin_client.post(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}", files=_upload_files()
        )
        from tests.test_api_settings import _make_operator_client

        operator = await _make_operator_client(client, admin_client)
        resp = await operator.get(
            f"/api/v1/assets/srv-app-001/sbom?tree_id={tree_id}"
        )
        assert resp.status_code == 200
