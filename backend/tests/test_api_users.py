"""
Tests d'intégration de la gestion des utilisateurs (T-1, plan WS5).

Couvrent : CRUD utilisateurs (admin), séparation admin/operator (403),
et les gardes « dernier admin » / auto-protection.
"""

import pytest

pytestmark = pytest.mark.asyncio

_ADMIN = {"username": "admin", "password": "AdminPass123!"}


async def _create_user(client, username, password="OperatorPass123!", role="operator"):
    resp = await client.post(
        "/api/v1/users",
        json={"username": username, "password": password, "role": role},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login_as(client, username, password):
    await client.post("/api/v1/auth/logout")
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text


async def _create_active_operator(client, username, password="OperatorPass123!"):
    """
    Crée un operator et finalise son changement de mot de passe forcé, de
    sorte qu'il soit pleinement actif. Laisse le client connecté en tant que
    cet operator. Les comptes créés par un admin ont must_change_pwd=True :
    sans cette étape, require_auth renvoie 403 (« Password change required »)
    pour toute route autre que change-password/logout, ce qui masquerait un
    vrai contrôle de rôle.
    """
    tmp_password = "TempPass123!"
    await _create_user(client, username, password=tmp_password, role="operator")
    await _login_as(client, username, tmp_password)
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": tmp_password, "new_password": password},
    )
    assert resp.status_code == 200, resp.text


class TestUserCrud:
    async def test_create_and_list_users(self, admin_client):
        await _create_user(admin_client, "op1")
        resp = await admin_client.get("/api/v1/users")
        assert resp.status_code == 200
        usernames = {u["username"] for u in resp.json()}
        assert {"admin", "op1"} <= usernames

    async def test_create_duplicate_username_409(self, admin_client):
        await _create_user(admin_client, "op1")
        resp = await admin_client.post(
            "/api/v1/users",
            json={"username": "op1", "password": "OperatorPass123!", "role": "operator"},
        )
        assert resp.status_code == 409

    async def test_update_user_role(self, admin_client):
        user = await _create_user(admin_client, "op1")
        resp = await admin_client.put(
            f"/api/v1/users/{user['id']}", json={"role": "admin"}
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    async def test_delete_user(self, admin_client):
        user = await _create_user(admin_client, "op1")
        resp = await admin_client.delete(f"/api/v1/users/{user['id']}")
        assert resp.status_code == 204
        listing = await admin_client.get("/api/v1/users")
        assert "op1" not in {u["username"] for u in listing.json()}

    async def test_reset_password_forces_change_at_next_login(self, admin_client):
        user = await _create_user(admin_client, "op1")
        resp = await admin_client.post(
            f"/api/v1/users/{user['id']}/reset-password",
            json={"new_password": "ResetPass123!"},
        )
        assert resp.status_code == 200

        await _login_as(admin_client, "op1", "ResetPass123!")
        check = await admin_client.get("/api/v1/auth/check")
        assert check.json()["status"] == "must_change_password"

    async def test_update_unknown_user_404(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"role": "admin"},
        )
        assert resp.status_code == 404


class TestRoleSeparation:
    async def test_operator_cannot_list_users(self, admin_client):
        await _create_active_operator(admin_client, "op1")
        resp = await admin_client.get("/api/v1/users")
        assert resp.status_code == 403

    async def test_operator_cannot_create_users(self, admin_client):
        await _create_active_operator(admin_client, "op1")
        resp = await admin_client.post(
            "/api/v1/users",
            json={"username": "op2", "password": "OperatorPass123!", "role": "operator"},
        )
        assert resp.status_code == 403

    async def test_operator_can_evaluate(self, admin_client):
        """Un operator garde l'accès en évaluation (lecture métier)."""
        await _create_active_operator(admin_client, "op1")
        resp = await admin_client.post(
            "/api/v1/evaluate/single",
            json={"vulnerability": {"cve_id": "CVE-2024-1", "cvss_score": 5.0}},
        )
        # Pas d'arbre par défaut => 404, mais surtout PAS 403 (accès autorisé)
        assert resp.status_code != 403


class TestLastAdminGuards:
    async def test_cannot_delete_last_admin(self, admin_client):
        listing = await admin_client.get("/api/v1/users")
        admin = next(u for u in listing.json() if u["username"] == "admin")
        resp = await admin_client.delete(f"/api/v1/users/{admin['id']}")
        assert resp.status_code == 400

    async def test_cannot_demote_last_admin(self, admin_client):
        listing = await admin_client.get("/api/v1/users")
        admin = next(u for u in listing.json() if u["username"] == "admin")
        resp = await admin_client.put(
            f"/api/v1/users/{admin['id']}", json={"role": "operator"}
        )
        assert resp.status_code == 400

    async def test_cannot_delete_own_account(self, admin_client):
        # Crée un 2e admin pour que la garde "dernier admin" ne s'applique pas
        second = await _create_user(admin_client, "admin2", role="admin")
        listing = await admin_client.get("/api/v1/users")
        me = next(u for u in listing.json() if u["username"] == "admin")
        resp = await admin_client.delete(f"/api/v1/users/{me['id']}")
        assert resp.status_code == 400
        assert second["role"] == "admin"

    async def test_can_delete_admin_when_another_exists(self, admin_client):
        second = await _create_user(admin_client, "admin2", role="admin")
        resp = await admin_client.delete(f"/api/v1/users/{second['id']}")
        assert resp.status_code == 204
