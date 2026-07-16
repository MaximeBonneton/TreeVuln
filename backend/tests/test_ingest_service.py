"""
Tests for the ingestion service.

B-13: la boucle CPU-bound d'évaluation (mapping + engine.evaluate) doit
être exécutée hors de l'event loop via asyncio.to_thread, sans changer
le comportement fonctionnel ni l'isolation d'erreur déjà en place.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engine.inference import InferenceEngine
from app.models.ingest import IngestEndpoint
from app.schemas.tree import TreeStructure
from app.services.ingest_service import IngestService, _ingest_entries_sync


class TestIngestEntriesSync:
    """Tests unitaires de la boucle sync extraite (exécutée en thread)."""

    def test_ingest_entries_sync_auto_evaluate(self, simple_tree_structure: TreeStructure):
        """Mapping + évaluation appliqués à chaque entrée quand auto_evaluate=True."""
        engine = InferenceEngine(simple_tree_structure)
        payload = [
            {"id": "v1", "cvss_score": 9.5},  # -> Act
            {"id": "v2", "cvss_score": 5.0},  # -> Track
        ]

        results, success_count, error_count = _ingest_entries_sync(
            payload, field_mapping={}, auto_evaluate=True, engine=engine, lookups={}
        )

        assert success_count == 2
        assert error_count == 0
        assert results[0]["decision"] == "Act"
        assert results[1]["decision"] == "Track"

    def test_ingest_entries_sync_isolates_errors(self, simple_tree_structure: TreeStructure):
        """Une entrée invalide ne fait pas échouer les autres (isolation déjà en place)."""
        engine = InferenceEngine(simple_tree_structure)
        payload = [
            {"id": "v1", "cvss_score": 9.5},
            {"id": "v2", "cvss_score": "not-a-number"},
        ]

        results, success_count, error_count = _ingest_entries_sync(
            payload, field_mapping={}, auto_evaluate=True, engine=engine, lookups={}
        )

        assert success_count == 1
        assert error_count == 1
        assert results[1]["status"] == "error"

    def test_ingest_entries_sync_no_auto_evaluate(self, simple_tree_structure: TreeStructure):
        """Sans auto_evaluate, les entrées sont juste réceptionnées (pas d'évaluation)."""
        engine = InferenceEngine(simple_tree_structure)
        payload = [{"id": "v1", "cvss_score": 9.5}]

        results, success_count, error_count = _ingest_entries_sync(
            payload, field_mapping={}, auto_evaluate=False, engine=engine, lookups={}
        )

        assert success_count == 1
        assert error_count == 0
        assert results[0]["status"] == "received"


class TestIngestServiceOffEventLoop:
    """B-13: IngestService.ingest délègue le travail CPU-bound à un thread."""

    @pytest.mark.asyncio
    async def test_ingest_uses_to_thread(
        self, simple_tree_structure: TreeStructure, monkeypatch
    ):
        """La boucle sync doit être invoquée via asyncio.to_thread, résultat inchangé."""
        import app.services.ingest_service as ingest_module

        engine = InferenceEngine(simple_tree_structure)
        endpoint = IngestEndpoint(
            id=1,
            tree_id=1,
            name="Test endpoint",
            slug="test-endpoint",
            api_key="k",
            field_mapping={},
            is_active=True,
            auto_evaluate=True,
        )

        db = AsyncMock()
        db.add = MagicMock()  # AsyncSession.add() est synchrone dans SQLAlchemy
        service = IngestService(db)

        calls: list[object] = []
        real_to_thread = asyncio.to_thread

        async def spy_to_thread(func, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(ingest_module.asyncio, "to_thread", spy_to_thread)

        payload = [
            {"id": "v1", "cvss_score": 9.5},
            {"id": "v2", "cvss_score": 5.0},
        ]
        result = await service.ingest(endpoint, payload, engine, lookups={})

        assert len(calls) == 1
        assert calls[0] is ingest_module._ingest_entries_sync

        assert result.received == 2
        assert result.evaluated == 2
        assert result.errors == 0

        # Le log d'ingestion est toujours écrit (comportement inchangé)
        db.add.assert_called_once()
        db.commit.assert_awaited()
