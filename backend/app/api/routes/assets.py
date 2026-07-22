"""
API routes for managing assets.
Multi-tree support: each asset belongs to a specific tree.
Bulk import support from CSV/JSON.
"""

import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.api.deps import AssetServiceDep, SbomServiceDep, read_upload_with_limit, require_role
from app.engine.sbom import parse_sbom_file
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
from app.schemas.sbom import (
    SbomComponentResponse,
    SbomDetailResponse,
    SbomResponse,
    SbomSummaryItem,
)

router = APIRouter()


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="Tree ID. If not provided, uses the default tree.",
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    criticality: str | None = None,
):
    """
    List assets of a tree with pagination and optional filtering.

    Args:
        tree_id: Tree ID (default if not provided)
        limit: Maximum number of assets to return (default: 100)
        offset: Offset for pagination
        criticality: Filter by criticality (Low, Medium, High, Critical)
    """
    assets = await asset_service.list_assets(tree_id, limit, offset, criticality)
    return assets


@router.get("/sbom/summary", response_model=list[SbomSummaryItem])
async def get_sbom_summary(
    sbom_service: SbomServiceDep,
    tree_id: int = Query(
        description="Tree ID (obligatoire : pas d'accès privé à la résolution "
        "de l'arbre par défaut depuis cette route).",
    ),
):
    """Assets de l'arbre ayant un SBOM (badges de l'UI)."""
    return await sbom_service.get_tree_summary(tree_id)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="Tree ID. If not provided, uses the default tree.",
    ),
):
    """
    Retrieve an asset by its identifier in the context of a tree.
    """
    asset = await asset_service.get_asset(asset_id, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )
    return asset


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="Tree ID. If not provided, uses the default tree or data.tree_id.",
    ),
    # S-15 : le référentiel d'assets pilote les décisions (criticité) —
    # écriture réservée aux admins, lecture ouverte aux operators.
    _=require_role("admin"),
):
    """
    Create a new asset in the context of a tree.

    Uniqueness is enforced by the (tree_id, asset_id) pair.
    """
    # Check if asset already exists in this tree
    existing = await asset_service.get_asset(data.asset_id, tree_id or data.tree_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset '{data.asset_id}' already exists in this tree",
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
        description="Tree ID. If not provided, uses the default tree.",
    ),
    _=require_role("admin"),
):
    """Update an existing asset in the context of a tree."""
    asset = await asset_service.update_asset(asset_id, data, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="Tree ID. If not provided, uses the default tree.",
    ),
    _=require_role("admin"),
):
    """Delete an asset in the context of a tree."""
    deleted = await asset_service.delete_asset(asset_id, tree_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )


@router.post("/bulk", response_model=AssetBulkResponse)
async def bulk_create_assets(
    data: AssetBulkCreate,
    asset_service: AssetServiceDep,
    tree_id: int | None = Query(
        default=None,
        description="Tree ID. If not provided, uses the default tree or data.tree_id.",
    ),
    _=require_role("admin"),
):
    """
    Bulk import of assets (upsert) in the context of a tree.

    Existing assets are updated, new ones are created.
    """
    if not data.assets:
        return AssetBulkResponse(created=0, updated=0)

    # Use tree_id from query param, otherwise from body
    final_tree_id = tree_id or data.tree_id
    created, updated = await asset_service.bulk_upsert(data.assets, final_tree_id)
    return AssetBulkResponse(created=created, updated=updated)


def _parse_upload_file(content: bytes, filename: str) -> list[dict]:
    """Parse a CSV or JSON file into a list of dictionaries."""
    if filename.endswith(".json"):
        data = json.loads(content.decode("utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "assets" in data:
            return data["assets"]
        raise ValueError("JSON must be an array or an object with an 'assets' key")

    if filename.endswith(".csv"):
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    raise ValueError("Unsupported format. Use CSV or JSON.")


@router.post("/import/preview")
async def preview_import(file: UploadFile, _=require_role("admin")):
    """
    Scan a CSV/JSON file and return detected columns.
    Useful for configuring mapping before import.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename missing",
        )

    content = await read_upload_with_limit(file)
    try:
        rows = _parse_upload_file(content, safe_name)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parsing error: {e}",
        )

    if not rows:
        return {"columns": [], "row_count": 0, "preview": []}

    columns = list(rows[0].keys())
    preview = rows[:5]  # First 5 rows for preview

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
        description="Target tree ID. If not provided, uses the default tree.",
    ),
    col_asset_id: str = Query(
        default="asset_id",
        description="Column name for the asset identifier",
    ),
    col_name: str | None = Query(
        default=None,
        description="Column name for the asset name",
    ),
    col_criticality: str | None = Query(
        default=None,
        description="Column name for criticality",
    ),
    _=require_role("admin"),
):
    """
    Import assets from a CSV or JSON file.

    Column mapping is configured via query params.
    Existing assets (same asset_id in the same tree) are updated.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename missing",
        )

    if not (safe_name.endswith(".csv") or safe_name.endswith(".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be in CSV or JSON format",
        )

    content = await read_upload_with_limit(file)
    try:
        rows = _parse_upload_file(content, safe_name)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parsing error: {e}",
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


@router.post(
    "/{asset_id}/sbom", response_model=SbomResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_sbom(
    asset_id: str,
    file: UploadFile,
    asset_service: AssetServiceDep,
    sbom_service: SbomServiceDep,
    tree_id: int | None = Query(default=None),
    _=require_role("admin"),
):
    """Importe (ou remplace) le SBOM d'un asset. CycloneDX/SPDX JSON."""
    asset = await asset_service.get_asset(asset_id, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )

    content = await read_upload_with_limit(file)
    try:
        parsed = parse_sbom_file(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not parsed.components:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No usable component found in the SBOM",
        )

    sbom = await sbom_service.replace_sbom(
        asset.id, parsed, sanitize_filename(file.filename)
    )
    response = SbomResponse.model_validate(sbom)
    response.warnings = parsed.warnings
    return response


@router.get("/{asset_id}/sbom", response_model=SbomDetailResponse)
async def get_asset_sbom(
    asset_id: str,
    asset_service: AssetServiceDep,
    sbom_service: SbomServiceDep,
    tree_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Méta du SBOM d'un asset + page de composants."""
    asset = await asset_service.get_asset(asset_id, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )
    sbom = await sbom_service.get_sbom(asset.id)
    if not sbom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' has no SBOM",
        )
    components, total = await sbom_service.get_components(sbom.id, limit, offset)
    # Construction explicite (pas de model_validate(sbom) global) : le modèle
    # ORM Sbom porte une relation "components" paresseuse qui, si on la laisse
    # être lue par from_attributes, déclenche un lazy-load synchrone hors
    # contexte async (MissingGreenlet). On ne lit ici que les colonnes scalaires.
    return SbomDetailResponse(
        format=sbom.format,
        spec_version=sbom.spec_version,
        filename=sbom.filename,
        component_count=sbom.component_count,
        imported_at=sbom.imported_at,
        components=[SbomComponentResponse.model_validate(c) for c in components],
        total_components=total,
    )


@router.delete("/{asset_id}/sbom", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_sbom(
    asset_id: str,
    asset_service: AssetServiceDep,
    sbom_service: SbomServiceDep,
    tree_id: int | None = Query(default=None),
    _=require_role("admin"),
):
    """Supprime le SBOM d'un asset."""
    asset = await asset_service.get_asset(asset_id, tree_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )
    deleted = await sbom_service.delete_sbom(asset.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' has no SBOM",
        )
