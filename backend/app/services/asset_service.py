"""
Service for asset management.
Multi-tree support: each asset belongs to a specific tree.
"""

from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, Tree
from app.schemas.asset import AssetCreate, AssetImportError, AssetImportResponse, AssetUpdate


class AssetService:
    """Asset reference management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_default_tree_id(self) -> int:
        """Retrieve the default tree ID."""
        result = await self.db.execute(select(Tree).where(Tree.is_default == True))
        tree = result.scalar_one_or_none()
        if not tree:
            raise ValueError("No default tree configured")
        return tree.id

    async def _resolve_tree_id(self, tree_id: int | None) -> int:
        """Resolve the tree ID (uses default if not provided)."""
        if tree_id is not None:
            return tree_id
        return await self._get_default_tree_id()

    async def get_asset(self, asset_id: str, tree_id: int | None = None) -> Asset | None:
        """
        Retrieve an asset by its identifier in the context of a tree.

        Args:
            asset_id: Asset identifier
            tree_id: Tree ID (default if not provided)
        """
        resolved_tree_id = await self._resolve_tree_id(tree_id)
        result = await self.db.execute(
            select(Asset).where(
                Asset.asset_id == asset_id,
                Asset.tree_id == resolved_tree_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_asset_by_pk(self, pk: int) -> Asset | None:
        """Retrieve an asset by its primary key."""
        result = await self.db.execute(select(Asset).where(Asset.id == pk))
        return result.scalar_one_or_none()

    async def list_assets(
        self,
        tree_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
        criticality: str | None = None,
    ) -> list[Asset]:
        """
        List assets for a tree with pagination and optional filtering.

        Args:
            tree_id: Tree ID (default if not provided)
            limit: Maximum number of assets
            offset: Offset for pagination
            criticality: Filter by criticality
        """
        resolved_tree_id = await self._resolve_tree_id(tree_id)
        query = select(Asset).where(Asset.tree_id == resolved_tree_id)

        if criticality:
            query = query.where(Asset.criticality == criticality)

        query = query.offset(offset).limit(limit).order_by(Asset.asset_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_asset(self, data: AssetCreate, tree_id: int | None = None) -> Asset:
        """
        Create a new asset.

        Args:
            data: Asset data
            tree_id: Tree ID (default if not provided, priority over data.tree_id)
        """
        # Resolve tree ID: parameter > data > default
        final_tree_id = tree_id or data.tree_id
        resolved_tree_id = await self._resolve_tree_id(final_tree_id)

        asset = Asset(
            tree_id=resolved_tree_id,
            asset_id=data.asset_id,
            name=data.name,
            criticality=data.criticality,
            tags=data.tags,
            extra_data=data.extra_data,
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def update_asset(
        self,
        asset_id: str,
        data: AssetUpdate,
        tree_id: int | None = None,
    ) -> Asset | None:
        """
        Update an existing asset.

        Args:
            asset_id: Asset identifier
            data: Update data
            tree_id: Tree ID (default if not provided)
        """
        asset = await self.get_asset(asset_id, tree_id)
        if not asset:
            return None

        if data.name is not None:
            asset.name = data.name
        if data.criticality is not None:
            asset.criticality = data.criticality
        if data.tags is not None:
            asset.tags = data.tags
        if data.extra_data is not None:
            asset.extra_data = data.extra_data

        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def delete_asset(self, asset_id: str, tree_id: int | None = None) -> bool:
        """
        Delete an asset.

        Args:
            asset_id: Asset identifier
            tree_id: Tree ID (default if not provided)
        """
        asset = await self.get_asset(asset_id, tree_id)
        if not asset:
            return False
        await self.db.delete(asset)
        await self.db.commit()
        return True

    @staticmethod
    def _deduplicate_assets(assets: list[AssetCreate]) -> list[AssetCreate]:
        """
        Déduplique une liste d'assets par asset_id (dernier gagnant).

        Nécessaire car un INSERT ... ON CONFLICT DO UPDATE en un seul batch
        VALUES ne peut pas affecter deux fois la même ligne cible : si le
        fichier importé contient deux fois le même (tree_id, asset_id),
        PostgreSQL lève CardinalityViolation ("ON CONFLICT DO UPDATE command
        cannot affect row a second time"). Or les CSV d'inventaire contiennent
        très souvent des doublons (ex: agrégation multi-scan).
        """
        deduped: dict[str, AssetCreate] = {}
        for asset in assets:
            deduped[asset.asset_id] = asset
        return list(deduped.values())

    async def bulk_upsert(
        self,
        assets: list[AssetCreate],
        tree_id: int | None = None,
    ) -> tuple[int, int]:
        """
        Bulk import with upsert (insert or update if exists).

        Args:
            assets: List of assets to import
            tree_id: Tree ID (default if not provided)

        Returns:
            Tuple (created_count, updated_count)
        """
        if not assets:
            return 0, 0

        resolved_tree_id = await self._resolve_tree_id(tree_id)

        # Dédupliquer par asset_id AVANT l'INSERT (dernier gagnant) pour
        # éviter CardinalityViolation en cas de doublons dans le batch importé
        deduped_assets = self._deduplicate_assets(assets)

        # Count existing assets before upsert (sur la liste dédupliquée)
        asset_ids = [a.asset_id for a in deduped_assets]
        existing_count_result = await self.db.execute(
            select(func.count()).where(
                Asset.tree_id == resolved_tree_id,
                Asset.asset_id.in_(asset_ids),
            )
        )
        existing_before = existing_count_result.scalar() or 0

        # Use INSERT ... ON CONFLICT for upsert
        stmt = insert(Asset).values([
            {
                "tree_id": resolved_tree_id,
                "asset_id": a.asset_id,
                "name": a.name,
                "criticality": a.criticality,
                "tags": a.tags,
                "extra_data": a.extra_data,
            }
            for a in deduped_assets
        ])

        stmt = stmt.on_conflict_do_update(
            constraint="assets_tree_asset_unique",
            set_={
                "name": stmt.excluded.name,
                "criticality": stmt.excluded.criticality,
                "tags": stmt.excluded.tags,
                "extra_data": stmt.excluded.extra_data,
            },
        )

        await self.db.execute(stmt)
        await self.db.commit()

        # Compteurs cohérents avec la liste dédupliquée (nombre réel de lignes
        # affectées par l'upsert, pas le nombre brut d'entrées du fichier)
        created = len(deduped_assets) - existing_before
        updated = existing_before
        return created, updated

    async def import_from_rows(
        self,
        rows: list[dict[str, Any]],
        column_mapping: dict[str, str | None],
        tree_id: int | None = None,
    ) -> AssetImportResponse:
        """
        Import assets from parsed rows with column mapping.

        Args:
            rows: Raw data rows
            column_mapping: Mapping {asset_field: source_column}
            tree_id: Target tree ID

        Returns:
            Detailed import result
        """
        valid_assets: list[AssetCreate] = []
        error_details: list[AssetImportError] = []
        valid_criticalities = {"Low", "Medium", "High", "Critical"}

        asset_id_col = column_mapping.get("asset_id", "asset_id")
        name_col = column_mapping.get("name")
        criticality_col = column_mapping.get("criticality")

        for i, row in enumerate(rows, start=1):
            # Retrieve asset_id
            raw_asset_id = row.get(asset_id_col) if asset_id_col else None
            if not raw_asset_id or str(raw_asset_id).strip() == "":
                error_details.append(AssetImportError(
                    row=i,
                    error=f"Column '{asset_id_col}' empty or missing",
                ))
                continue

            asset_id_val = str(raw_asset_id).strip()

            # Retrieve name
            name_val = None
            if name_col and name_col in row:
                name_val = str(row[name_col]).strip() if row[name_col] else None

            # Retrieve and validate criticality
            criticality_val = "Medium"
            if criticality_col and criticality_col in row:
                raw_crit = str(row[criticality_col]).strip()
                # Normalize case
                crit_normalized = raw_crit.capitalize()
                if crit_normalized in valid_criticalities:
                    criticality_val = crit_normalized
                elif raw_crit:
                    error_details.append(AssetImportError(
                        row=i,
                        asset_id=asset_id_val,
                        error=f"Invalid criticality: '{raw_crit}'. Accepted values: {', '.join(sorted(valid_criticalities))}",
                    ))
                    continue

            valid_assets.append(AssetCreate(
                asset_id=asset_id_val,
                name=name_val,
                criticality=criticality_val,
            ))

        # Bulk upsert valid assets
        created = 0
        updated = 0
        if valid_assets:
            created, updated = await self.bulk_upsert(valid_assets, tree_id)

        return AssetImportResponse(
            total_rows=len(rows),
            created=created,
            updated=updated,
            errors=len(error_details),
            error_details=error_details,
        )

    async def get_lookup_cache(
        self,
        tree_id: int | None = None,
        asset_ids: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Build a lookup cache for the inference engine.

        Args:
            tree_id: Tree ID (default if not provided)
            asset_ids: List of asset_ids to load (all if None)

        Returns:
            Dict {asset_id: {field: value, ...}}
        """
        resolved_tree_id = await self._resolve_tree_id(tree_id)
        query = select(Asset).where(Asset.tree_id == resolved_tree_id)

        if asset_ids:
            query = query.where(Asset.asset_id.in_(asset_ids))

        result = await self.db.execute(query)
        assets = result.scalars().all()

        cache: dict[str, dict[str, Any]] = {}
        for asset in assets:
            cache[asset.asset_id] = {
                "id": asset.id,
                "asset_id": asset.asset_id,
                "name": asset.name,
                "criticality": asset.criticality,
                "tags": asset.tags,
                "extra_data": asset.extra_data,
            }
        return cache
