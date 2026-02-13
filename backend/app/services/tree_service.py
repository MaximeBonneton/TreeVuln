"""
Service pour la gestion des arbres de décision.
Support multi-arbres avec contextes isolés.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Asset, Tree, TreeVersion
from app.schemas.tree import (
    TreeApiConfig,
    TreeCreate,
    TreeDuplicateRequest,
    TreeListItem,
    TreeStructure,
    TreeUpdate,
)
from app.services.tree_validation import validate_tree_structure


class TreeService:
    """Service de gestion des arbres de décision."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tree(self, tree_id: int | None = None) -> Tree | None:
        """
        Récupère un arbre par ID ou l'arbre par défaut.
        """
        if tree_id:
            result = await self.db.execute(select(Tree).where(Tree.id == tree_id))
        else:
            # Récupère l'arbre par défaut
            result = await self.db.execute(select(Tree).where(Tree.is_default == True))
        return result.scalar_one_or_none()

    async def get_default_tree(self) -> Tree | None:
        """Récupère l'arbre par défaut."""
        result = await self.db.execute(select(Tree).where(Tree.is_default == True))
        return result.scalar_one_or_none()

    async def get_tree_by_slug(self, slug: str) -> Tree | None:
        """Récupère un arbre par son slug API."""
        result = await self.db.execute(
            select(Tree).where(Tree.api_slug == slug, Tree.api_enabled == True)
        )
        return result.scalar_one_or_none()

    async def list_trees(self) -> list[TreeListItem]:
        """Liste tous les arbres avec un résumé."""
        result = await self.db.execute(
            select(Tree).order_by(Tree.is_default.desc(), Tree.name)
        )
        trees = result.scalars().all()

        items = []
        for tree in trees:
            # Compte les nœuds dans la structure
            node_count = len(tree.structure.get("nodes", []))
            items.append(
                TreeListItem(
                    id=tree.id,
                    name=tree.name,
                    description=tree.description,
                    is_default=tree.is_default,
                    api_enabled=tree.api_enabled,
                    api_slug=tree.api_slug,
                    node_count=node_count,
                    created_at=tree.created_at,
                    updated_at=tree.updated_at,
                )
            )
        return items

    async def create_tree(self, data: TreeCreate, set_as_default: bool = False) -> Tree:
        """
        Crée un nouvel arbre.

        Args:
            data: Données de création
            set_as_default: Si True, définit ce nouvel arbre comme défaut
        """
        # Si on définit comme défaut, on retire le flag des autres arbres
        if set_as_default:
            await self.db.execute(
                select(Tree).where(Tree.is_default == True).with_for_update()
            )
            # Met à jour tous les arbres existants
            result = await self.db.execute(select(Tree).where(Tree.is_default == True))
            for existing in result.scalars().all():
                existing.is_default = False

        tree = Tree(
            name=data.name,
            description=data.description,
            structure=data.structure.model_dump(),
            is_default=set_as_default,
        )
        self.db.add(tree)
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def update_tree(
        self,
        tree_id: int,
        data: TreeUpdate,
        create_version: bool = True,
    ) -> Tree | None:
        """
        Met à jour un arbre et optionnellement crée une version.

        Args:
            tree_id: ID de l'arbre
            data: Données de mise à jour
            create_version: Si True, sauvegarde une version avant la mise à jour
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Crée une version si demandé et si la structure change
        if create_version and data.structure is not None:
            await self._create_version(tree, data.version_comment)

        # Met à jour les champs
        if data.name is not None:
            tree.name = data.name
        if data.description is not None:
            tree.description = data.description
        if data.structure is not None:
            tree.structure = data.structure.model_dump()

        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def delete_tree(self, tree_id: int) -> bool:
        """
        Supprime un arbre et ses versions/assets associés.
        Refuse de supprimer l'arbre par défaut.
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return False
        if tree.is_default:
            raise ValueError("Impossible de supprimer l'arbre par défaut")
        await self.db.delete(tree)
        await self.db.commit()
        return True

    async def _create_version(self, tree: Tree, comment: str | None = None) -> TreeVersion:
        """Crée une nouvelle version de l'arbre."""
        # Trouve le prochain numéro de version
        result = await self.db.execute(
            select(func.coalesce(func.max(TreeVersion.version_number), 0))
            .where(TreeVersion.tree_id == tree.id)
        )
        max_version = result.scalar() or 0

        version = TreeVersion(
            tree_id=tree.id,
            version_number=max_version + 1,
            structure_snapshot=tree.structure,
            comment=comment,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_versions(self, tree_id: int) -> list[TreeVersion]:
        """Récupère toutes les versions d'un arbre."""
        result = await self.db.execute(
            select(TreeVersion)
            .where(TreeVersion.tree_id == tree_id)
            .order_by(TreeVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, version_id: int) -> TreeVersion | None:
        """Récupère une version spécifique."""
        result = await self.db.execute(
            select(TreeVersion).where(TreeVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def restore_version(self, tree_id: int, version_id: int) -> Tree | None:
        """
        Restaure une version précédente de l'arbre.
        Crée une nouvelle version de l'état actuel avant restauration.
        """
        tree = await self.get_tree(tree_id)
        version = await self.get_version(version_id)

        if not tree or not version or version.tree_id != tree_id:
            return None

        # Sauvegarde l'état actuel
        await self._create_version(tree, f"Avant restauration vers v{version.version_number}")

        # Restaure
        tree.structure = version.structure_snapshot
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    def get_tree_structure(self, tree: Tree) -> TreeStructure:
        """Convertit la structure JSON en objet TreeStructure."""
        return TreeStructure.model_validate(tree.structure)

    async def set_default_tree(self, tree_id: int) -> Tree | None:
        """
        Définit un arbre comme arbre par défaut.
        Retire le flag des autres arbres.
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Retire le flag des autres arbres
        result = await self.db.execute(
            select(Tree).where(Tree.is_default == True, Tree.id != tree_id)
        )
        for other in result.scalars().all():
            other.is_default = False

        tree.is_default = True
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def update_api_config(self, tree_id: int, config: TreeApiConfig) -> Tree | None:
        """
        Met à jour la configuration API d'un arbre.

        Args:
            tree_id: ID de l'arbre
            config: Configuration API (enable, slug)
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Vérifie l'unicité du slug si fourni
        if config.api_slug:
            existing = await self.db.execute(
                select(Tree).where(
                    Tree.api_slug == config.api_slug,
                    Tree.id != tree_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Le slug '{config.api_slug}' est déjà utilisé")

        tree.api_enabled = config.api_enabled
        tree.api_slug = config.api_slug if config.api_enabled else None

        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def duplicate_tree(
        self,
        tree_id: int,
        request: TreeDuplicateRequest,
    ) -> Tree | None:
        """
        Duplique un arbre existant.

        Args:
            tree_id: ID de l'arbre à dupliquer
            request: Options de duplication (nom, inclure assets)

        Returns:
            Le nouvel arbre dupliqué ou None si l'arbre source n'existe pas
        """
        # Charge l'arbre avec ses assets
        result = await self.db.execute(
            select(Tree).options(selectinload(Tree.assets)).where(Tree.id == tree_id)
        )
        source_tree = result.scalar_one_or_none()
        if not source_tree:
            return None

        # Crée le nouvel arbre
        new_tree = Tree(
            name=request.new_name,
            description=source_tree.description,
            structure=source_tree.structure.copy(),
            is_default=False,
            api_enabled=False,
            api_slug=None,
        )
        self.db.add(new_tree)
        await self.db.flush()  # Pour obtenir l'ID

        # Duplique les assets si demandé
        if request.include_assets:
            for asset in source_tree.assets:
                new_asset = Asset(
                    tree_id=new_tree.id,
                    asset_id=asset.asset_id,
                    name=asset.name,
                    criticality=asset.criticality,
                    tags=asset.tags.copy(),
                    extra_data=asset.extra_data.copy(),
                )
                self.db.add(new_asset)

        await self.db.commit()
        await self.db.refresh(new_tree)
        return new_tree
