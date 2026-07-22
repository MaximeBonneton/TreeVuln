"""Tests d'intégration des routes de settings CSAF."""
import pytest

pytestmark = pytest.mark.asyncio

VALID_PUBLISHER = {
    "name": "ACME Medical",
    "namespace": "https://acme-medical.example.com",
    "category": "vendor",
}


async def _make_operator_client(client, admin_client):
    """Crée un opérateur pleinement actif et retourne un client connecté.

    Les comptes créés par un admin ont must_change_pwd=True : il faut
    finaliser le changement de mot de passe forcé, sinon require_auth
    renvoie 403 pour toute autre route (même pattern que test_api_users).
    """
    tmp_password = "Op3rator!tmp"
    final_password = "Op3rator!pass"
    resp = await admin_client.post(
        "/api/v1/users",
        json={"username": "operator1", "password": tmp_password, "role": "operator"},
    )
    assert resp.status_code in (200, 201), resp.text
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "operator1", "password": tmp_password},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": tmp_password, "new_password": final_password},
    )
    assert resp.status_code == 200, resp.text
    return client


class TestGetCsafSettings:
    async def test_get_sans_auth_401(self, client):
        resp = await client.get("/api/v1/settings/csaf")
        assert resp.status_code == 401

    async def test_get_vide_par_defaut(self, admin_client):
        resp = await admin_client.get("/api/v1/settings/csaf")
        assert resp.status_code == 200
        body = resp.json()
        assert body["publisher"] is None
        assert body["has_signing_key"] is False
        assert body["signing_key_fingerprint"] is None

    async def test_get_accessible_operator(self, client, admin_client):
        operator = await _make_operator_client(client, admin_client)
        resp = await operator.get("/api/v1/settings/csaf")
        assert resp.status_code == 200


class TestPutCsafSettings:
    async def test_put_publisher_admin(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/settings/csaf", json={"publisher": VALID_PUBLISHER}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["publisher"]["name"] == "ACME Medical"
        assert body["has_signing_key"] is False

    async def test_put_interdit_operator(self, client, admin_client):
        operator = await _make_operator_client(client, admin_client)
        resp = await operator.put(
            "/api/v1/settings/csaf", json={"publisher": VALID_PUBLISHER}
        )
        assert resp.status_code == 403

    async def test_put_namespace_invalide_422(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/settings/csaf",
            json={"publisher": {**VALID_PUBLISHER, "namespace": "pas-une-url"}},
        )
        assert resp.status_code == 422

    async def test_import_cle_retourne_empreinte(self, admin_client, test_pgp_key):
        from tests.conftest import TEST_PASSPHRASE

        resp = await admin_client.put(
            "/api/v1/settings/csaf",
            json={
                "publisher": VALID_PUBLISHER,
                "signing_key": test_pgp_key,
                "signing_key_passphrase": TEST_PASSPHRASE,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_signing_key"] is True
        assert len(body["signing_key_fingerprint"]) == 40
        # La clé privée n'apparaît jamais dans la réponse
        assert "signing_key" not in body

    async def test_cle_stockee_chiffree(self, admin_client, db_session, test_pgp_key):
        from tests.conftest import TEST_PASSPHRASE

        from app.services.settings_service import CSAF_SETTINGS_KEY, SettingsService

        await admin_client.put(
            "/api/v1/settings/csaf",
            json={
                "publisher": VALID_PUBLISHER,
                "signing_key": test_pgp_key,
                "signing_key_passphrase": TEST_PASSPHRASE,
            },
        )
        stored = await SettingsService(db_session).get_setting(CSAF_SETTINGS_KEY)
        assert stored["signing_key"].startswith("enc:")
        assert stored["signing_key_passphrase"].startswith("enc:")

    async def test_cle_invalide_400(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/settings/csaf",
            json={"publisher": VALID_PUBLISHER, "signing_key": "pas une clé"},
        )
        assert resp.status_code == 400

    async def test_remove_signing_key(self, admin_client, test_pgp_key):
        from tests.conftest import TEST_PASSPHRASE

        await admin_client.put(
            "/api/v1/settings/csaf",
            json={
                "publisher": VALID_PUBLISHER,
                "signing_key": test_pgp_key,
                "signing_key_passphrase": TEST_PASSPHRASE,
            },
        )
        resp = await admin_client.put(
            "/api/v1/settings/csaf", json={"remove_signing_key": True}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_signing_key"] is False
        # Le publisher est conservé (mise à jour partielle)
        assert body["publisher"]["name"] == "ACME Medical"


VALID_MANUFACTURER = {
    "name": "ACME Medical",
    "contact": "security@acme-medical.example.com",
    "product_identifiers": ["acme-pump-v2"],
}


class TestGetEnisaSettings:
    async def test_get_sans_auth_401(self, client):
        resp = await client.get("/api/v1/settings/enisa")
        assert resp.status_code == 401

    async def test_get_valeurs_par_defaut(self, admin_client):
        resp = await admin_client.get("/api/v1/settings/enisa")
        assert resp.status_code == 200
        body = resp.json()
        assert body["manufacturer"] is None
        assert body["reminder_thresholds"] == ["T-12h", "T-2h", "overdue"]

    async def test_get_accessible_operator(self, client, admin_client):
        operator = await _make_operator_client(client, admin_client)
        resp = await operator.get("/api/v1/settings/enisa")
        assert resp.status_code == 200


class TestPutEnisaSettings:
    async def test_put_manufacturer_admin(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/settings/enisa", json={"manufacturer": VALID_MANUFACTURER}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["manufacturer"]["name"] == "ACME Medical"

    async def test_put_interdit_operator(self, client, admin_client):
        operator = await _make_operator_client(client, admin_client)
        resp = await operator.put(
            "/api/v1/settings/enisa", json={"manufacturer": VALID_MANUFACTURER}
        )
        assert resp.status_code == 403

    async def test_put_seuil_invalide_400(self, admin_client):
        resp = await admin_client.put(
            "/api/v1/settings/enisa",
            json={"reminder_thresholds": ["T-12h", "pas-un-seuil"]},
        )
        assert resp.status_code == 400

    async def test_put_seuils_partiel_conserve_manufacturer(self, admin_client):
        await admin_client.put(
            "/api/v1/settings/enisa", json={"manufacturer": VALID_MANUFACTURER}
        )
        resp = await admin_client.put(
            "/api/v1/settings/enisa",
            json={"reminder_thresholds": ["overdue"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["reminder_thresholds"] == ["overdue"]
        assert body["manufacturer"]["name"] == "ACME Medical"
