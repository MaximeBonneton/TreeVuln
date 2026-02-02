"""
Dépendances communes pour les routes API.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.asset_service import AssetService
from app.services.tree_service import TreeService

# Type alias pour les dépendances
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_tree_service(db: DBSession) -> AsyncGenerator[TreeService, None]:
    """Fournit une instance du service Tree."""
    yield TreeService(db)


async def get_asset_service(db: DBSession) -> AsyncGenerator[AssetService, None]:
    """Fournit une instance du service Asset."""
    yield AssetService(db)


TreeServiceDep = Annotated[TreeService, Depends(get_tree_service)]
AssetServiceDep = Annotated[AssetService, Depends(get_asset_service)]
