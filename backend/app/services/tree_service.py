"""
Service for managing decision trees.
Multi-tree support with isolated contexts.
"""

from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Asset, Tree, TreeVersion
from app.schemas.tree import (
    TreeApiConfig,
    TreeCreate,
    TreeDuplicateRequest,
    TreeExportFile,
    TreeImportRequest,
    TreeListItem,
    TreeStructure,
    TreeUpdate,
)
from app.services.tree_validation import validate_tree_structure


class TreeService:
    """Decision tree management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tree(self, tree_id: int | None = None) -> Tree | None:
        """
        Retrieve a tree by ID or the default tree.
        """
        if tree_id:
            result = await self.db.execute(select(Tree).where(Tree.id == tree_id))
        else:
            # Retrieve the default tree
            result = await self.db.execute(select(Tree).where(Tree.is_default == True))
        return result.scalar_one_or_none()

    async def get_default_tree(self) -> Tree | None:
        """Retrieve the default tree."""
        result = await self.db.execute(select(Tree).where(Tree.is_default == True))
        return result.scalar_one_or_none()

    async def get_tree_by_slug(self, slug: str) -> Tree | None:
        """Retrieve a tree by its API slug."""
        result = await self.db.execute(
            select(Tree).where(Tree.api_slug == slug, Tree.api_enabled == True)
        )
        return result.scalar_one_or_none()

    async def list_trees(self) -> list[TreeListItem]:
        """List all trees with a summary."""
        result = await self.db.execute(
            select(Tree).order_by(Tree.is_default.desc(), Tree.name)
        )
        trees = result.scalars().all()

        items = []
        for tree in trees:
            # Count nodes in the structure
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
        Create a new tree.

        Args:
            data: Creation data
            set_as_default: If True, sets this new tree as default
        """
        # Si ce nouvel arbre doit devenir le défaut, on retire d'abord le flag
        # des autres arbres via un UPDATE atomique (verrouille les lignes concernées
        # jusqu'au commit, ce qui sérialise les appels concurrents).
        if set_as_default:
            await self.db.execute(
                update(Tree).where(Tree.is_default == True).values(is_default=False)
            )

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
        Update a tree and optionally create a version.

        Args:
            tree_id: Tree ID
            data: Update data
            create_version: If True, saves a version before the update
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Create a version if requested and if the structure changes
        if create_version and data.structure is not None:
            await self._create_version(tree, data.version_comment)

        # Update fields
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
        Delete a tree and its associated versions/assets.
        Refuses to delete the default tree.
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return False
        if tree.is_default:
            raise ValueError("Cannot delete the default tree")
        await self.db.delete(tree)
        await self.db.commit()
        return True

    async def _create_version(self, tree: Tree, comment: str | None = None) -> TreeVersion:
        """Create a new version of the tree."""
        # Find the next version number
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
        """Retrieve all versions of a tree."""
        result = await self.db.execute(
            select(TreeVersion)
            .where(TreeVersion.tree_id == tree_id)
            .order_by(TreeVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, version_id: int) -> TreeVersion | None:
        """Retrieve a specific version."""
        result = await self.db.execute(
            select(TreeVersion).where(TreeVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def restore_version(self, tree_id: int, version_id: int) -> Tree | None:
        """
        Restore a previous version of the tree.
        Creates a new version of the current state before restoration.
        """
        tree = await self.get_tree(tree_id)
        version = await self.get_version(version_id)

        if not tree or not version or version.tree_id != tree_id:
            return None

        # Save current state
        await self._create_version(tree, f"Before restoration to v{version.version_number}")

        # Restore
        tree.structure = version.structure_snapshot
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    def get_tree_structure(self, tree: Tree) -> TreeStructure:
        """Convert JSON structure to TreeStructure object."""
        return TreeStructure.model_validate(tree.structure)

    async def set_default_tree(self, tree_id: int) -> Tree | None:
        """
        Set a tree as the default tree.
        Removes the flag from other trees.

        Opération atomique en deux UPDATE dans la même transaction :
        1) on retire le flag par défaut de tous les arbres qui l'ont actuellement,
        2) on le pose sur l'arbre ciblé.
        Les verrous de lignes pris par ces UPDATE sérialisent les appels concurrents
        (un deuxième appel bloque jusqu'au commit/rollback du premier), et l'index
        unique partiel en base garantit l'unicité même en cas de bug applicatif.
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Étape 1 : retire le flag par défaut de tous les arbres actuellement par défaut
        await self.db.execute(
            update(Tree).where(Tree.is_default == True).values(is_default=False)
        )
        # Étape 2 : positionne le nouvel arbre par défaut
        await self.db.execute(
            update(Tree).where(Tree.id == tree_id).values(is_default=True)
        )

        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def update_api_config(self, tree_id: int, config: TreeApiConfig) -> Tree | None:
        """
        Update the API configuration for a tree.

        Args:
            tree_id: Tree ID
            config: API configuration (enable, slug)
        """
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Verify slug uniqueness if provided
        if config.api_slug:
            existing = await self.db.execute(
                select(Tree).where(
                    Tree.api_slug == config.api_slug,
                    Tree.id != tree_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Slug '{config.api_slug}' is already in use")

        tree.api_enabled = config.api_enabled
        tree.api_slug = config.api_slug if config.api_enabled else None

        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    # --- Decision-as-Code (export/import) ---

    async def export_tree(self, tree_id: int) -> TreeExportFile | None:
        """Export a complete tree in Decision-as-Code format."""
        tree = await self.get_tree(tree_id)
        if not tree:
            return None

        # Copy the structure to avoid mutating the original
        structure = deepcopy(tree.structure) if tree.structure else {"nodes": [], "edges": [], "metadata": {}}

        # Extract field_mapping from metadata and remove it from the structure
        # to avoid duplication (single source of truth in the file)
        field_mapping = None
        if structure.get("metadata", {}).get("field_mapping"):
            field_mapping = structure["metadata"].pop("field_mapping")

        return TreeExportFile.model_validate({
            "format": "treevuln-decision-tree",
            "version": 1,
            "exported_at": datetime.now(timezone.utc),
            "tree": {
                "name": tree.name,
                "description": tree.description,
                "structure": structure,
                "field_mapping": field_mapping,
            },
        })

    async def import_tree(self, data: TreeImportRequest) -> Tree:
        """Import a tree from a Decision-as-Code file."""
        # Generate a unique name if necessary
        name = await self._unique_import_name(data.tree.name)

        # Inject field_mapping into metadata if present
        structure_data = data.tree.structure.model_dump()
        if data.tree.field_mapping:
            if "metadata" not in structure_data or structure_data["metadata"] is None:
                structure_data["metadata"] = {}
            structure_data["metadata"]["field_mapping"] = data.tree.field_mapping.model_dump()

        # Create the tree via the existing flow
        create_data = TreeCreate(
            name=name,
            description=data.tree.description,
            structure=TreeStructure.model_validate(structure_data),
        )
        return await self.create_tree(create_data)

    async def _unique_import_name(self, base_name: str) -> str:
        """Generate a unique name by adding a suffix if necessary."""
        stmt = select(Tree.name).where(Tree.name.like(f"{base_name}%"))
        result = await self.db.execute(stmt)
        existing_names = {row[0] for row in result.fetchall()}

        if base_name not in existing_names:
            return base_name

        candidate = f"{base_name} (imported)"
        if candidate not in existing_names:
            return candidate

        counter = 2
        while f"{base_name} (imported {counter})" in existing_names:
            counter += 1
        return f"{base_name} (imported {counter})"

    async def duplicate_tree(
        self,
        tree_id: int,
        request: TreeDuplicateRequest,
    ) -> Tree | None:
        """
        Duplicate an existing tree.

        Args:
            tree_id: ID of the tree to duplicate
            request: Duplication options (name, include assets)

        Returns:
            The new duplicated tree or None if the source tree does not exist
        """
        # Load the tree with its assets
        result = await self.db.execute(
            select(Tree).options(selectinload(Tree.assets)).where(Tree.id == tree_id)
        )
        source_tree = result.scalar_one_or_none()
        if not source_tree:
            return None

        # Create the new tree
        new_tree = Tree(
            name=request.new_name,
            description=source_tree.description,
            structure=source_tree.structure.copy(),
            is_default=False,
            api_enabled=False,
            api_slug=None,
        )
        self.db.add(new_tree)
        await self.db.flush()  # To get the ID

        # Duplicate assets if requested
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
