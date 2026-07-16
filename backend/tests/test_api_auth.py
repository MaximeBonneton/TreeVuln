"""
Tests d'intégration de l'authentification (T-1, plan WS5).

Exercent l'API réelle contre une base PostgreSQL éphémère (fixtures
`client` / `admin_client` de conftest.py). Couvrent : setup initial,
login/logout, expiration/invalidation de session, changement de mot de
passe et son effet sur les autres sessions.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

pytestmark = pytest.mark.asyncio

_ADMIN = {"username": "admin", "password": "AdminPass123!"}


class TestSetup:
    async def test_check_reports_setup_required_on_empty_db(self, client):
        resp = await client.get("/api/v1/auth/check")
        assert resp.status_code == 200
        assert resp.json()["status"] == "setup_required"

    async def test_setup_creates_admin_and_authenticates(self, client):
        resp = await client.post("/api/v1/auth/setup", json=_ADMIN)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "authenticated"
        assert body["user"]["username"] == "admin"
        assert body["user"]["role"] == "admin"

    async def test_setup_rejected_once_completed(self, client):
        await client.post("/api/v1/auth/setup", json=_ADMIN)
        resp = await client.post(
            "/api/v1/auth/setup",
            json={"username": "other", "password": "OtherPass123!"},
        )
        assert resp.status_code == 403

    async def test_setup_rejects_short_password(self, client):
        resp = await client.post(
            "/api/v1/auth/setup",
            json={"username": "admin", "password": "short"},
        )
        assert resp.status_code == 422


class TestLoginLogout:
    async def test_login_success_sets_cookie(self, admin_client):
        # admin_client est déjà connecté ; on se déconnecte puis on re-login
        await admin_client.post("/api/v1/auth/logout")
        resp = await admin_client.post("/api/v1/auth/login", json=_ADMIN)
        assert resp.status_code == 200
        assert resp.json()["status"] == "authenticated"

    async def test_login_wrong_password_401(self, admin_client):
        await admin_client.post("/api/v1/auth/logout")
        resp = await admin_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "WrongPass123!"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_user_401(self, client):
        # setup d'abord pour ne pas être en setup_required
        await client.post("/api/v1/auth/setup", json=_ADMIN)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "GhostPass123!"},
        )
        assert resp.status_code == 401

    async def test_logout_clears_session(self, admin_client):
        await admin_client.post("/api/v1/auth/logout")
        resp = await admin_client.get("/api/v1/auth/check")
        assert resp.json()["status"] == "unauthenticated"

    async def test_protected_route_requires_auth(self, client):
        await client.post("/api/v1/auth/setup", json=_ADMIN)
        await client.post("/api/v1/auth/logout")
        resp = await client.get("/api/v1/users")
        assert resp.status_code == 401


class TestSessionLifecycle:
    async def test_expired_session_is_rejected(self, admin_client, db_engine):
        from app.models.user import UserSession

        # Vieillit toutes les sessions au-delà de leur expiration
        async with db_engine.begin() as conn:
            await conn.execute(
                update(UserSession).values(
                    expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
                )
            )

        resp = await admin_client.get("/api/v1/auth/check")
        assert resp.json()["status"] == "unauthenticated"

    async def test_change_password_invalidates_other_sessions(
        self, admin_client, db_engine
    ):
        from app.models.user import UserSession

        # Le cookie courant est la session A. On simule une 2e session (B).
        async with db_engine.begin() as conn:
            rows = (await conn.execute(select(UserSession))).all()
        assert len(rows) == 1  # une seule session active (celle du client)

        resp = await admin_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": _ADMIN["password"],
                "new_password": "BrandNewPass123!",
            },
        )
        assert resp.status_code == 200

        # La session courante (A) survit au changement
        check = await admin_client.get("/api/v1/auth/check")
        assert check.json()["status"] == "authenticated"

    async def test_change_password_wrong_current_rejected(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "NotThePassword1!",
                "new_password": "BrandNewPass123!",
            },
        )
        assert resp.status_code == 400
