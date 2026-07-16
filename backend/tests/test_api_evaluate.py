"""
Integration tests for evaluation endpoints.
Uses httpx.AsyncClient with FastAPI dependency overrides.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_asset_service, get_tree_service, require_auth
from app.main import app
from app.schemas.tree import (
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    TreeStructure,
)


def _make_simple_tree_model():
    """Create a mocked Tree object with a simple tree."""
    structure = TreeStructure(
        nodes=[
            NodeSchema(
                id="input-cvss",
                type=NodeType.INPUT,
                label="CVSS Score",
                config={"field": "cvss_score"},
                conditions=[
                    NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Critical"),
                    NodeCondition(operator=ConditionOperator.LESS_THAN, value=9.0, label="Low"),
                ],
            ),
            NodeSchema(
                id="output-act",
                type=NodeType.OUTPUT,
                label="Act",
                config={"decision": "Act", "color": "#ff0000"},
            ),
            NodeSchema(
                id="output-track",
                type=NodeType.OUTPUT,
                label="Track",
                config={"decision": "Track", "color": "#00ff00"},
            ),
        ],
        edges=[
            EdgeSchema(id="e1", source="input-cvss", target="output-act", source_handle="handle-0", label="Critical"),
            EdgeSchema(id="e2", source="input-cvss", target="output-track", source_handle="handle-1", label="Low"),
        ],
    )

    tree = MagicMock()
    tree.id = 1
    tree.structure = structure.model_dump()
    tree.is_default = True
    return tree


def _make_mock_tree_service(tree):
    """Create a mock TreeService."""
    service = AsyncMock()
    service.get_tree = AsyncMock(return_value=tree)
    service.get_tree_structure = MagicMock(
        return_value=TreeStructure.model_validate(tree.structure)
    )
    return service


def _make_mock_asset_service():
    """Create a mock AssetService."""
    service = AsyncMock()
    service.get_lookup_cache = AsyncMock(return_value={})
    return service


def _make_fake_user():
    """Create a fake user to bypass authentication."""
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000001"
    user.username = "test-admin"
    user.role = "admin"
    user.is_active = True
    user.must_change_pwd = False
    return user


@pytest.fixture
def mock_services():
    """Fixture that overrides dependencies with mocks."""
    tree = _make_simple_tree_model()
    tree_service = _make_mock_tree_service(tree)
    asset_service = _make_mock_asset_service()
    fake_user = _make_fake_user()

    app.dependency_overrides[get_tree_service] = lambda: tree_service
    app.dependency_overrides[get_asset_service] = lambda: asset_service
    app.dependency_overrides[require_auth] = lambda: fake_user

    yield tree_service, asset_service

    app.dependency_overrides.clear()


@pytest.fixture
async def client(mock_services):
    """Async HTTP client for tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestEvaluateSingle:
    """Tests pour POST /api/v1/evaluate/single."""

    @pytest.mark.asyncio
    async def test_evaluate_single_critical(self, client: AsyncClient):
        """CVSS >= 9.0 should return Act."""
        response = await client.post(
            "/api/v1/evaluate/single",
            json={
                "vulnerability": {"id": "vuln-1", "cvss_score": 9.5},
                "include_path": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "Act"
        assert data["vuln_id"] == "vuln-1"
        assert len(data["path"]) == 2

    @pytest.mark.asyncio
    async def test_evaluate_single_low(self, client: AsyncClient):
        """CVSS < 9.0 should return Track."""
        response = await client.post(
            "/api/v1/evaluate/single",
            json={
                "vulnerability": {"id": "vuln-2", "cvss_score": 5.0},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "Track"

    @pytest.mark.asyncio
    async def test_evaluate_single_no_path(self, client: AsyncClient):
        """include_path=false does not return a path."""
        response = await client.post(
            "/api/v1/evaluate/single",
            json={
                "vulnerability": {"id": "vuln-3", "cvss_score": 9.5},
                "include_path": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "Act"
        assert data["path"] == []


class TestEvaluateBatch:
    """Tests pour POST /api/v1/evaluate."""

    @pytest.mark.asyncio
    async def test_evaluate_batch(self, client: AsyncClient):
        """Batch of 3 vulnerabilities."""
        response = await client.post(
            "/api/v1/evaluate",
            json={
                "vulnerabilities": [
                    {"id": "v1", "cvss_score": 9.5},
                    {"id": "v2", "cvss_score": 5.0},
                    {"id": "v3", "cvss_score": 10.0},
                ],
                "include_path": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success_count"] == 3
        assert data["error_count"] == 0

        decisions = [r["decision"] for r in data["results"]]
        assert decisions == ["Act", "Track", "Act"]

    @pytest.mark.asyncio
    async def test_evaluate_batch_empty(self, client: AsyncClient):
        """Empty batch returns an empty result."""
        response = await client.post(
            "/api/v1/evaluate",
            json={
                "vulnerabilities": [],
                "include_path": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestEvaluateBatchErrorIsolation:
    """B-12: une ligne invalide (JSON ou CSV) ne fait pas échouer tout le batch."""

    @pytest.mark.asyncio
    async def test_evaluate_batch_json_isolates_invalid_rows(self, client: AsyncClient):
        """Batch JSON de 3 lignes (1 bonne, 2 invalides) -> 200, pas de 500."""
        response = await client.post(
            "/api/v1/evaluate",
            json={
                "vulnerabilities": [
                    {"id": "v1", "cvss_score": 9.5},
                    {"id": "v2", "cvss_score": 11},  # hors [0, 10]
                    {"id": "v3", "cvss_score": "N/A"},  # non convertible
                ],
                "include_path": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success_count"] == 1
        assert data["error_count"] == 2

        decisions = [r["decision"] for r in data["results"]]
        assert decisions == ["Act", "Error", "Error"]
        assert data["results"][1]["vuln_id"] == "v2"
        assert data["results"][1]["error"] is not None
        assert data["results"][2]["vuln_id"] == "v3"
        assert data["results"][2]["error"] is not None

    @pytest.mark.asyncio
    async def test_evaluate_csv_isolates_invalid_rows(self, client: AsyncClient):
        """Batch CSV de 3 lignes (1 bonne, 2 invalides) -> 200, pas de 500."""
        csv_content = "id,cvss_score\nv1,9.5\nv2,11\nv3,N/A\n"
        response = await client.post(
            "/api/v1/evaluate/csv",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success_count"] == 1
        assert data["error_count"] == 2

    @pytest.mark.asyncio
    async def test_evaluate_csv_malformed_returns_400(self, client: AsyncClient):
        """CSV totalement illisible -> 400 (pas 500), message générique (pas de fuite Polars)."""
        response = await client.post(
            "/api/v1/evaluate/csv",
            files={"file": ("test.csv", b"", "text/csv")},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "CSV file could not be parsed"


class TestEvaluateNoTree:
    """Tests when no tree is configured."""

    @pytest.mark.asyncio
    async def test_evaluate_single_no_tree(self):
        """Returns 404 if no default tree exists."""
        tree_service = AsyncMock()
        tree_service.get_tree = AsyncMock(return_value=None)
        asset_service = _make_mock_asset_service()
        fake_user = _make_fake_user()

        app.dependency_overrides[get_tree_service] = lambda: tree_service
        app.dependency_overrides[get_asset_service] = lambda: asset_service
        app.dependency_overrides[require_auth] = lambda: fake_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/evaluate/single",
                    json={"vulnerability": {"id": "v1", "cvss_score": 9.0}},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
