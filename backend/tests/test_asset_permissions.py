"""
Tests pour la séparation des rôles sur les routes assets (S-15, Task 3.10).

Un operator peut LIRE le référentiel d'assets (nécessaire à l'évaluation)
mais toute écriture (create/update/delete/bulk/import) est réservée aux
admins : le référentiel d'assets pilote les décisions SSVC (criticité),
le modifier revient à modifier les décisions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_asset_service, require_auth
from app.main import app


def _fake_user(role: str) -> MagicMock:
    user = MagicMock()
    user.role = role
    user.must_change_pwd = False
    return user


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    service.get_assets = AsyncMock(return_value=[])
    return service


@pytest.fixture
def as_operator(mock_service: AsyncMock):
    app.dependency_overrides[require_auth] = lambda: _fake_user("operator")
    app.dependency_overrides[get_asset_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def as_admin(mock_service: AsyncMock):
    app.dependency_overrides[require_auth] = lambda: _fake_user("admin")
    app.dependency_overrides[get_asset_service] = lambda: mock_service
    yield
    app.dependency_overrides.clear()


_VALID_ASSET = {"asset_id": "srv-test-001", "name": "Test", "criticality": "High"}


class TestOperatorCannotWriteAssets:
    @pytest.mark.asyncio
    async def test_create_asset_forbidden(self, as_operator):
        async with _client() as client:
            response = await client.post("/api/v1/assets", json=_VALID_ASSET)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_asset_forbidden(self, as_operator):
        async with _client() as client:
            response = await client.put(
                "/api/v1/assets/srv-test-001", json={"criticality": "Low"}
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_asset_forbidden(self, as_operator):
        async with _client() as client:
            response = await client.delete("/api/v1/assets/srv-test-001")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_create_forbidden(self, as_operator):
        async with _client() as client:
            response = await client.post(
                "/api/v1/assets/bulk", json={"assets": [_VALID_ASSET]}
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_import_preview_forbidden(self, as_operator):
        async with _client() as client:
            response = await client.post(
                "/api/v1/assets/import/preview",
                files={"file": ("assets.csv", b"asset_id\nsrv-1\n", "text/csv")},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_import_forbidden(self, as_operator):
        async with _client() as client:
            response = await client.post(
                "/api/v1/assets/import",
                files={"file": ("assets.csv", b"asset_id\nsrv-1\n", "text/csv")},
            )
        assert response.status_code == 403


class TestOperatorCanStillRead:
    @pytest.mark.asyncio
    async def test_list_assets_allowed(self, as_operator):
        async with _client() as client:
            response = await client.get("/api/v1/assets")
        assert response.status_code == 200


class TestAdminCanWrite:
    @pytest.mark.asyncio
    async def test_bulk_create_passes_role_check(self, as_admin):
        # Liste vide : la route répond sans toucher au service, ce qui
        # isole le test au contrôle de rôle.
        async with _client() as client:
            response = await client.post("/api/v1/assets/bulk", json={"assets": []})
        assert response.status_code == 200
        body = response.json()
        assert body["created"] == 0
        assert body["updated"] == 0
