"""
Service pour la gestion des assets.
Support multi-arbres: chaque asset appartient à un arbre spécifique.
"""

from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, Tree
from app.schemas.asset import AssetCreate, AssetUpdate


class AssetService:
    """Service de gestion du référentiel des assets."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_default_tree_id(self) -> int:
        """Récupère l'ID de l'arbre par défaut."""
        result = await self.db.execute(select(Tree).where(Tree.is_default == True))
        tree = result.scalar_one_or_none()
        if not tree:
            raise ValueError("Aucun arbre par défaut configuré")
        return tree.id

    async def _resolve_tree_id(self, tree_id: int | None) -> int:
        """Résout l'ID de l'arbre (utilise le défaut si non fourni)."""
        if tree_id is not None:
            return tree_id
        return await self._get_default_tree_id()

    async def get_asset(self, asset_id: str, tree_id: int | None = None) -> Asset | None:
        """
        Récupère un asset par son identifiant dans le contexte d'un arbre.

        Args:
            asset_id: Identifiant de l'asset
            tree_id: ID de l'arbre (défaut si non fourni)
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
        """Récupère un asset par sa clé primaire."""
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
        Liste les assets d'un arbre avec pagination et filtrage optionnel.

        Args:
            tree_id: ID de l'arbre (défaut si non fourni)
            limit: Nombre maximum d'assets
            offset: Offset pour la pagination
            criticality: Filtrer par criticité
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
        Crée un nouvel asset.

        Args:
            data: Données de l'asset
            tree_id: ID de l'arbre (défaut si non fourni, priorité sur data.tree_id)
        """
        # Résout l'ID de l'arbre: paramètre > data > défaut
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
        Met à jour un asset existant.

        Args:
            asset_id: Identifiant de l'asset
            data: Données de mise à jour
            tree_id: ID de l'arbre (défaut si non fourni)
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
        Supprime un asset.

        Args:
            asset_id: Identifiant de l'asset
            tree_id: ID de l'arbre (défaut si non fourni)
        """
        asset = await self.get_asset(asset_id, tree_id)
        if not asset:
            return False
        await self.db.delete(asset)
        await self.db.commit()
        return True

    async def bulk_upsert(
        self,
        assets: list[AssetCreate],
        tree_id: int | None = None,
    ) -> tuple[int, int]:
        """
        Import bulk avec upsert (insert ou update si existe).

        Args:
            assets: Liste des assets à importer
            tree_id: ID de l'arbre (défaut si non fourni)

        Returns:
            Tuple (created_count, updated_count)
        """
        if not assets:
            return 0, 0

        resolved_tree_id = await self._resolve_tree_id(tree_id)

        # Compte les assets existants avant l'upsert
        asset_ids = [a.asset_id for a in assets]
        existing_count_result = await self.db.execute(
            select(func.count()).where(
                Asset.tree_id == resolved_tree_id,
                Asset.asset_id.in_(asset_ids),
            )
        )
        existing_before = existing_count_result.scalar() or 0

        # Utilise INSERT ... ON CONFLICT pour l'upsert
        stmt = insert(Asset).values([
            {
                "tree_id": resolved_tree_id,
                "asset_id": a.asset_id,
                "name": a.name,
                "criticality": a.criticality,
                "tags": a.tags,
                "extra_data": a.extra_data,
            }
            for a in assets
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

        created = len(assets) - existing_before
        updated = existing_before
        return created, updated

    async def get_lookup_cache(
        self,
        tree_id: int | None = None,
        asset_ids: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Construit un cache de lookup pour le moteur d'inférence.

        Args:
            tree_id: ID de l'arbre (défaut si non fourni)
            asset_ids: Liste des asset_ids à charger (tous si None)

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
