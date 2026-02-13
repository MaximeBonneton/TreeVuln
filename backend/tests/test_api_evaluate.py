"""
Tests d'intégration pour les endpoints d'évaluation.
Utilise httpx.AsyncClient avec override des dépendances FastAPI.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_asset_service, get_tree_service
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
    """Crée un objet Tree mocké avec un arbre simple."""
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
    """Crée un mock de TreeService."""
    service = AsyncMock()
    service.get_tree = AsyncMock(return_value=tree)
    service.get_tree_structure = MagicMock(
        return_value=TreeStructure.model_validate(tree.structure)
    )
    return service


def _make_mock_asset_service():
    """Crée un mock d'AssetService."""
    service = AsyncMock()
    service.get_lookup_cache = AsyncMock(return_value={})
    return service


@pytest.fixture
def mock_services():
    """Fixture qui override les dépendances avec des mocks."""
    tree = _make_simple_tree_model()
    tree_service = _make_mock_tree_service(tree)
    asset_service = _make_mock_asset_service()

    app.dependency_overrides[get_tree_service] = lambda: tree_service
    app.dependency_overrides[get_asset_service] = lambda: asset_service

    yield tree_service, asset_service

    app.dependency_overrides.clear()


@pytest.fixture
async def client(mock_services):
    """Client HTTP async pour les tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestEvaluateSingle:
    """Tests pour POST /api/v1/evaluate/single."""

    @pytest.mark.asyncio
    async def test_evaluate_single_critical(self, client: AsyncClient):
        """CVSS >= 9.0 devrait retourner Act."""
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
        """CVSS < 9.0 devrait retourner Track."""
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
        """include_path=false ne retourne pas de chemin."""
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
        """Batch de 3 vulnérabilités."""
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
        """Batch vide retourne un résultat vide."""
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


class TestEvaluateNoTree:
    """Tests quand aucun arbre n'est configuré."""

    @pytest.mark.asyncio
    async def test_evaluate_single_no_tree(self):
        """Retourne 404 si aucun arbre par défaut."""
        tree_service = AsyncMock()
        tree_service.get_tree = AsyncMock(return_value=None)
        asset_service = _make_mock_asset_service()

        app.dependency_overrides[get_tree_service] = lambda: tree_service
        app.dependency_overrides[get_asset_service] = lambda: asset_service

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
