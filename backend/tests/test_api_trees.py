"""
Tests d'intégration des routes arbres (T-2, plan WS5).

Couvrent : CRUD, versions/restore, duplication (avec assets), api-config,
set-default, et l'interdiction de suppression de l'arbre par défaut.
"""

import pytest

pytestmark = pytest.mark.asyncio


def _minimal_structure() -> dict:
    """Petit arbre valide : cvss_score >= 9 -> Act, sinon -> Track."""
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
            {
                "id": "out-act",
                "type": "output",
                "label": "Act",
                "config": {"decision": "Act", "color": "#ff0000"},
                "conditions": [],
            },
            {
                "id": "out-track",
                "type": "output",
                "label": "Track",
                "config": {"decision": "Track", "color": "#00ff00"},
                "conditions": [],
            },
        ],
        "edges": [
            {"id": "e0", "source": "input-cvss", "target": "out-act", "source_handle": "handle-0"},
            {"id": "e1", "source": "input-cvss", "target": "out-track", "source_handle": "handle-1"},
        ],
        "metadata": {},
    }


async def _create_tree(client, name="Tree A", default=False):
    resp = await client.post(
        "/api/v1/tree",
        json={"name": name, "structure": _minimal_structure()},
    )
    assert resp.status_code == 201, resp.text
    tree = resp.json()
    if default:
        r = await client.put(f"/api/v1/tree/{tree['id']}/set-default")
        assert r.status_code == 200
        tree = r.json()
    return tree


class TestTreeCrud:
    async def test_create_and_get(self, admin_client):
        tree = await _create_tree(admin_client)
        resp = await admin_client.get(f"/api/v1/tree?tree_id={tree['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Tree A"

    async def test_list_trees(self, admin_client):
        await _create_tree(admin_client, "Tree A")
        await _create_tree(admin_client, "Tree B")
        resp = await admin_client.get("/api/v1/trees")
        assert resp.status_code == 200
        assert {t["name"] for t in resp.json()} >= {"Tree A", "Tree B"}

    async def test_update_creates_version(self, admin_client):
        tree = await _create_tree(admin_client)
        # Une version n'est archivée que si la structure est incluse dans le PUT
        resp = await admin_client.put(
            f"/api/v1/tree/{tree['id']}",
            json={
                "name": "Renamed",
                "structure": _minimal_structure(),
                "version_comment": "rename",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

        versions = await admin_client.get(f"/api/v1/tree/{tree['id']}/versions")
        assert versions.status_code == 200
        assert len(versions.json()) >= 1

    async def test_operator_cannot_create_tree(self, admin_client):
        # crée puis dégrade la session en operator via un compte dédié
        await admin_client.post(
            "/api/v1/users",
            json={"username": "op1", "password": "TempPass123!", "role": "operator"},
        )
        await admin_client.post("/api/v1/auth/logout")
        await admin_client.post(
            "/api/v1/auth/login", json={"username": "op1", "password": "TempPass123!"}
        )
        await admin_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "TempPass123!", "new_password": "OperatorPass123!"},
        )
        resp = await admin_client.post(
            "/api/v1/tree", json={"name": "Nope", "structure": _minimal_structure()}
        )
        assert resp.status_code == 403


class TestVersionsAndRestore:
    async def test_restore_previous_version(self, admin_client):
        tree = await _create_tree(admin_client, "Original")
        # Modifie pour générer une version historique (structure incluse)
        await admin_client.put(
            f"/api/v1/tree/{tree['id']}",
            json={
                "name": "Modified",
                "structure": _minimal_structure(),
                "version_comment": "v2",
            },
        )
        versions = (await admin_client.get(f"/api/v1/tree/{tree['id']}/versions")).json()
        assert versions, "au moins une version doit exister"
        version_id = versions[-1]["id"]

        resp = await admin_client.post(
            f"/api/v1/tree/{tree['id']}/restore/{version_id}"
        )
        assert resp.status_code == 200


class TestDuplicateAndConfig:
    async def test_duplicate_tree(self, admin_client):
        tree = await _create_tree(admin_client, "Source")
        resp = await admin_client.post(
            f"/api/v1/tree/{tree['id']}/duplicate",
            json={"new_name": "Copy", "include_assets": False},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Copy"
        assert resp.json()["id"] != tree["id"]

    async def test_api_config_enable_slug(self, admin_client):
        tree = await _create_tree(admin_client)
        resp = await admin_client.put(
            f"/api/v1/tree/{tree['id']}/api-config",
            json={"api_enabled": True, "api_slug": "my-tree"},
        )
        assert resp.status_code == 200
        assert resp.json()["api_enabled"] is True
        assert resp.json()["api_slug"] == "my-tree"

    async def test_set_default_is_exclusive(self, admin_client):
        a = await _create_tree(admin_client, "A", default=True)
        b = await _create_tree(admin_client, "B", default=True)

        trees = (await admin_client.get("/api/v1/trees")).json()
        defaults = [t["id"] for t in trees if t["is_default"]]
        assert defaults == [b["id"]]
        assert a["id"] not in defaults


class TestDeleteGuards:
    async def test_cannot_delete_default_tree(self, admin_client):
        tree = await _create_tree(admin_client, "Default", default=True)
        resp = await admin_client.delete(f"/api/v1/tree/{tree['id']}")
        assert resp.status_code == 400

    async def test_delete_non_default_tree(self, admin_client):
        await _create_tree(admin_client, "Keeper", default=True)
        victim = await _create_tree(admin_client, "Victim")
        resp = await admin_client.delete(f"/api/v1/tree/{victim['id']}")
        assert resp.status_code == 204
