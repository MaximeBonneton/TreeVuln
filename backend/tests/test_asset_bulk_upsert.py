"""
Tests unitaires pour le fix C-8 (audit 2026-07-16) : import d'assets tolérant
aux doublons.

Contexte : bulk_upsert() construisait un INSERT ... ON CONFLICT DO UPDATE avec
une ligne VALUES par entrée du fichier importé. Si le fichier contenait deux
fois le même (tree_id, asset_id) dans le même batch, PostgreSQL levait
CardinalityViolation ("ON CONFLICT DO UPDATE command cannot affect row a
second time") -> 500. Or les CSV d'inventaire contiennent très souvent des
doublons (ex: export multi-scan).

Le fix déduplique les entrées par asset_id AVANT l'INSERT (dernier gagnant),
et recalcule created/updated sur la liste dédupliquée.

Note : comme pour C-5/C-9, aucune fixture DB réelle (Postgres) n'existe encore
dans ce projet pour les tests backend - la session SQLAlchemy est mockée ici
(AsyncMock) et l'INSERT est intercepté via patch de `insert`. Ces tests
vérifient donc la logique de déduplication et la forme des appels, mais PAS
le comportement réel de PostgreSQL face à ON CONFLICT (contrainte réellement
testable seulement avec une vraie base).
"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.asset import AssetCreate
from app.services.asset_service import AssetService


def _make_service_with_mock_session() -> AssetService:
    """Construit un AssetService dont la session DB est entièrement mockée."""
    service = AssetService.__new__(AssetService)
    service.db = AsyncMock()
    return service


class TestDeduplicateAssets:
    """Tests de la fonction pure de déduplication par asset_id."""

    def test_dedup_last_wins(self):
        a1 = AssetCreate(asset_id="srv-1", name="First")
        a2 = AssetCreate(asset_id="srv-1", name="Second")
        a3 = AssetCreate(asset_id="srv-2", name="Other")

        result = AssetService._deduplicate_assets([a1, a2, a3])

        assert len(result) == 2
        by_id = {a.asset_id: a for a in result}
        assert by_id["srv-1"].name == "Second"  # dernière occurrence gagne
        assert by_id["srv-2"].name == "Other"

    def test_dedup_no_duplicates_preserves_all(self):
        a1 = AssetCreate(asset_id="srv-1")
        a2 = AssetCreate(asset_id="srv-2")

        result = AssetService._deduplicate_assets([a1, a2])

        assert len(result) == 2

    def test_dedup_empty_list(self):
        assert AssetService._deduplicate_assets([]) == []

    def test_dedup_three_occurrences_keeps_last(self):
        assets = [
            AssetCreate(asset_id="srv-1", criticality="Low"),
            AssetCreate(asset_id="srv-1", criticality="Medium"),
            AssetCreate(asset_id="srv-1", criticality="Critical"),
        ]

        result = AssetService._deduplicate_assets(assets)

        assert len(result) == 1
        assert result[0].criticality == "Critical"


class TestBulkUpsertDeduplication:
    """Tests du comportement de bulk_upsert face à des doublons dans le batch."""

    async def test_does_not_raise_and_inserts_one_row_per_duplicate_asset_id(self):
        """
        Reproduit le cas C-8 : deux entrées avec le même asset_id dans le même
        batch import. Sans dédup préalable, PostgreSQL lèverait
        CardinalityViolation. On vérifie ici qu'une seule ligne (la dernière)
        est passée à l'INSERT pour cet asset_id.
        """
        service = _make_service_with_mock_session()
        service._resolve_tree_id = AsyncMock(return_value=1)

        count_result = MagicMock()
        count_result.scalar.return_value = 0  # aucun asset déjà existant
        service.db.execute = AsyncMock(side_effect=[count_result, MagicMock()])
        service.db.commit = AsyncMock()

        assets = [
            AssetCreate(asset_id="srv-1", name="Old Name", criticality="Low"),
            AssetCreate(asset_id="srv-1", name="New Name", criticality="Critical"),
        ]

        with patch("app.services.asset_service.insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_insert.return_value = mock_stmt
            mock_stmt.values.return_value = mock_stmt
            mock_stmt.on_conflict_do_update.return_value = mock_stmt

            created, updated = await service.bulk_upsert(assets)

            values_arg = mock_stmt.values.call_args.args[0]
            assert len(values_arg) == 1
            assert values_arg[0]["asset_id"] == "srv-1"
            assert values_arg[0]["name"] == "New Name"
            assert values_arg[0]["criticality"] == "Critical"

        assert created == 1
        assert updated == 0

    async def test_counters_consistent_with_deduplicated_list(self):
        """
        created/updated doivent être calculés sur la liste dédupliquée, pas sur
        la liste brute (qui compterait les doublons en trop et fausserait le
        rapport d'import affiché à l'utilisateur).
        """
        service = _make_service_with_mock_session()
        service._resolve_tree_id = AsyncMock(return_value=1)

        count_result = MagicMock()
        count_result.scalar.return_value = 1  # 1 asset déjà existant (srv-1)
        service.db.execute = AsyncMock(side_effect=[count_result, MagicMock()])
        service.db.commit = AsyncMock()

        assets = [
            AssetCreate(asset_id="srv-1", name="A"),
            AssetCreate(asset_id="srv-1", name="B"),  # doublon -> dernier gagnant
            AssetCreate(asset_id="srv-2", name="C"),
        ]

        with patch("app.services.asset_service.insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_insert.return_value = mock_stmt
            mock_stmt.values.return_value = mock_stmt
            mock_stmt.on_conflict_do_update.return_value = mock_stmt

            created, updated = await service.bulk_upsert(assets)

        # 2 asset_id uniques après dédup (srv-1, srv-2), 1 déjà existant
        # -> 1 created, 1 updated (et non 3/1 ou 2/1 comme avec la liste brute)
        assert created == 1
        assert updated == 1

    async def test_empty_list_returns_zero_without_db_call(self):
        service = _make_service_with_mock_session()
        service.db.execute = AsyncMock()

        created, updated = await service.bulk_upsert([])

        assert (created, updated) == (0, 0)
        service.db.execute.assert_not_awaited()
