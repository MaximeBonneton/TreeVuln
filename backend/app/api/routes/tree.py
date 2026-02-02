"""
Routes API pour la gestion des arbres de décision.
Support multi-arbres avec contextes isolés.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import TreeServiceDep
from app.schemas.tree import (
    TreeApiConfig,
    TreeCreate,
    TreeDuplicateRequest,
    TreeListItem,
    TreeResponse,
    TreeStructure,
    TreeUpdate,
    TreeVersionResponse,
)

router = APIRouter()


# --- Multi-arbres ---


@router.get("s", response_model=list[TreeListItem])
async def list_trees(tree_service: TreeServiceDep):
    """
    Liste tous les arbres de décision.

    Retourne un résumé de chaque arbre (sans la structure complète).
    """
    return await tree_service.list_trees()


@router.get("", response_model=TreeResponse | None)
async def get_tree(
    tree_service: TreeServiceDep,
    tree_id: int | None = None,
):
    """
    Récupère un arbre de décision.

    Si tree_id n'est pas fourni, retourne l'arbre par défaut.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        return None
    return tree


@router.post("", response_model=TreeResponse, status_code=status.HTTP_201_CREATED)
async def create_tree(
    data: TreeCreate,
    tree_service: TreeServiceDep,
):
    """Crée un nouvel arbre de décision."""
    tree = await tree_service.create_tree(data)
    return tree


@router.put("/{tree_id}", response_model=TreeResponse)
async def update_tree(
    tree_id: int,
    data: TreeUpdate,
    tree_service: TreeServiceDep,
    create_version: bool = True,
):
    """
    Met à jour un arbre de décision.

    Args:
        tree_id: ID de l'arbre
        data: Données de mise à jour
        create_version: Si True (défaut), crée une version de sauvegarde
    """
    tree = await tree_service.update_tree(tree_id, data, create_version)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )
    return tree


@router.delete("/{tree_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tree(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """
    Supprime un arbre de décision.

    L'arbre par défaut ne peut pas être supprimé.
    """
    try:
        deleted = await tree_service.delete_tree(tree_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Arbre {tree_id} non trouvé",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{tree_id}/duplicate", response_model=TreeResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_tree(
    tree_id: int,
    request: TreeDuplicateRequest,
    tree_service: TreeServiceDep,
):
    """
    Duplique un arbre de décision.

    Crée une copie de l'arbre avec optionnellement ses assets associés.
    """
    tree = await tree_service.duplicate_tree(tree_id, request)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )
    return tree


@router.put("/{tree_id}/api-config", response_model=TreeResponse)
async def update_api_config(
    tree_id: int,
    config: TreeApiConfig,
    tree_service: TreeServiceDep,
):
    """
    Configure l'accès API dédié pour un arbre.

    Permet d'activer/désactiver l'endpoint /tree/{slug}/evaluate.
    """
    try:
        tree = await tree_service.update_api_config(tree_id, config)
        if not tree:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Arbre {tree_id} non trouvé",
            )
        return tree
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.put("/{tree_id}/set-default", response_model=TreeResponse)
async def set_default_tree(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """
    Définit un arbre comme arbre par défaut.

    L'arbre par défaut est utilisé par /api/v1/evaluate quand aucun arbre n'est spécifié.
    """
    tree = await tree_service.set_default_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )
    return tree


@router.get("/{tree_id}/structure", response_model=TreeStructure)
async def get_tree_structure(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """Récupère uniquement la structure de l'arbre (pour le frontend)."""
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arbre {tree_id} non trouvé",
        )
    return tree_service.get_tree_structure(tree)


# --- Versioning ---


@router.get("/{tree_id}/versions", response_model=list[TreeVersionResponse])
async def list_versions(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """Liste toutes les versions d'un arbre."""
    versions = await tree_service.get_versions(tree_id)
    return versions


@router.get("/versions/{version_id}", response_model=TreeVersionResponse)
async def get_version(
    version_id: int,
    tree_service: TreeServiceDep,
):
    """Récupère une version spécifique."""
    version = await tree_service.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_id} non trouvée",
        )
    return version


@router.post("/{tree_id}/restore/{version_id}", response_model=TreeResponse)
async def restore_version(
    tree_id: int,
    version_id: int,
    tree_service: TreeServiceDep,
):
    """
    Restaure une version précédente de l'arbre.

    L'état actuel est sauvegardé en tant que nouvelle version avant restauration.
    """
    tree = await tree_service.restore_version(tree_id, version_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arbre ou version non trouvé",
        )
    return tree
