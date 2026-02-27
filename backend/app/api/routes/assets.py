"""
Routes API pour la gestion des assets.
Support multi-arbres: chaque asset appartient à un arbre spécifique.
Support import bulk depuis CSV/JSON.
"""

import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.api.deps import AssetServiceDep
from app.filename_validation import sanitize_filename
from app.schemas.asset import (
    AssetBulkCreate,
    AssetBulkResponse,
    AssetColumnMapping,
    AssetCreate,
    AssetImportResponse,
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
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
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


def _parse_upload_file(content: bytes, filename: str) -> list[dict]:
    """Parse un fichier CSV ou JSON en liste de dictionnaires."""
    if filename.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "assets" in data:
            return data["assets"]
        raise ValueError("Le JSON doit être un tableau ou un objet avec une clé 'assets'")

    if filename.endswith(".csv"):
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    raise ValueError("Format non supporté. Utilisez CSV ou JSON.")


@router.post("/import/preview")
async def preview_import(file: UploadFile):
    """
    Scanne un fichier CSV/JSON et retourne les colonnes détectées.
    Utile pour configurer le mapping avant import.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier manquant",
        )

    content = await file.read()
    try:
        rows = _parse_upload_file(content, safe_name)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de parsing: {e}",
        )

    if not rows:
        return {"columns": [], "row_count": 0, "preview": []}

    columns = list(rows[0].keys())
    preview = rows[:5]  # 5 premières lignes pour prévisualisation

    return {
        "columns": columns,
        "row_count": len(rows),
        "preview": preview,
    }


@router.post("/import", response_model=AssetImportResponse)
async def import_assets(
    file: UploadFile,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="ID de l'arbre cible. Si non fourni, utilise l'arbre par défaut.",
    ),
    col_asset_id: str = Query(
        default="asset_id",
        description="Nom de la colonne pour l'identifiant de l'asset",
    ),
    col_name: str | None = Query(
        default=None,
        description="Nom de la colonne pour le nom de l'asset",
    ),
    col_criticality: str | None = Query(
        default=None,
        description="Nom de la colonne pour la criticité",
    ),
):
    """
    Importe des assets depuis un fichier CSV ou JSON.

    Le mapping des colonnes est configuré via les query params.
    Les assets existants (même asset_id dans le même arbre) sont mis à jour.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom de fichier manquant",
        )

    if not (safe_name.endswith(".csv") or safe_name.endswith(".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être au format CSV ou JSON",
        )

    content = await file.read()
    try:
        rows = _parse_upload_file(content, safe_name)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de parsing: {e}",
        )

    if not rows:
        return AssetImportResponse(
            total_rows=0, created=0, updated=0, errors=0,
        )

    column_mapping = {
        "asset_id": col_asset_id,
        "name": col_name,
        "criticality": col_criticality,
    }

    return await asset_service.import_from_rows(rows, column_mapping, tree_id)
