"""
Routes API pour la gestion des assets.
Support multi-arbres: chaque asset appartient à un arbre spécifique.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AssetServiceDep
from app.schemas.asset import (
    AssetBulkCreate,
    AssetBulkResponse,
    AssetCreate,
    AssetResponse,
    AssetUpdate,
)

router = APIRouter()


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre. Si non fourni, utilise l'arbre par défaut.",
    ),
    limit: int = 100,
    offset: int = 0,
    criticality: str | None = None,
):
    """
    Liste les assets d'un arbre avec pagination et filtrage optionnel.

    Args:
        tree_id: ID de l'arbre (défaut si non fourni)
        limit: Nombre maximum d'assets à retourner (défaut: 100)
        offset: Offset pour la pagination
        criticality: Filtrer par criticité (Low, Medium, High, Critical)
    """
    assets = await asset_service.list_assets(tree_id, limit, offset, criticality)
    return assets


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre. Si non fourni, utilise l'arbre par défaut.",
    ),
):
    """
    Récupère un asset par son identifiant dans le contexte d'un arbre.
    """
    asset = await asset_service.get_asset(asset_id, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' non trouvé",
        )
    return asset


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre. Si non fourni, utilise l'arbre par défaut ou data.tree_id.",
    ),
):
    """
    Crée un nouvel asset dans le contexte d'un arbre.

    L'unicité est vérifiée par couple (tree_id, asset_id).
    """
    # Vérifie si l'asset existe déjà dans cet arbre
    existing = await asset_service.get_asset(data.asset_id, tree_id or data.tree_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset '{data.asset_id}' existe déjà dans cet arbre",
        )
    asset = await asset_service.create_asset(data, tree_id)
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    data: AssetUpdate,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre. Si non fourni, utilise l'arbre par défaut.",
    ),
):
    """Met à jour un asset existant dans le contexte d'un arbre."""
    asset = await asset_service.update_asset(asset_id, data, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' non trouvé",
        )
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre. Si non fourni, utilise l'arbre par défaut.",
    ),
):
    """Supprime un asset dans le contexte d'un arbre."""
    deleted = await asset_service.delete_asset(asset_id, tree_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' non trouvé",
        )


@router.post("/bulk", response_model=AssetBulkResponse)
async def bulk_create_assets(
    data: AssetBulkCreate,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre. Si non fourni, utilise l'arbre par défaut ou data.tree_id.",
    ),
):
    """
    Import bulk d'assets (upsert) dans le contexte d'un arbre.

    Les assets existants sont mis à jour, les nouveaux sont créés.
    """
    if not data.assets:
        return AssetBulkResponse(created=0, updated=0)

    # Utilise tree_id du query param, sinon celui du body
    final_tree_id = tree_id or data.tree_id
    created, updated = await asset_service.bulk_upsert(data.assets, final_tree_id)
    return AssetBulkResponse(created=created, updated=updated)
