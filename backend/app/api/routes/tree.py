"""
API routes for managing decision trees.
Multi-tree support with isolated contexts.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.api.deps import TreeServiceDep, require_role
from app.filename_validation import sanitize_filename
from app.models import Tree
from app.schemas.tree import (
    TreeApiConfig,
    TreeCreate,
    TreeDuplicateRequest,
    TreeImportRequest,
    TreeListItem,
    TreeResponse,
    TreeStructure,
    TreeUpdate,
    TreeVersionResponse,
)
from app.schemas.diagnostic import DiagnosticRequest, DiagnosticResult
from app.services.tree_diagnostics import diagnose_tree
from app.services.tree_validation import validate_tree_structure

router = APIRouter()


def _tree_response_with_warnings(tree: Tree) -> TreeResponse:
    """Build a TreeResponse with structure validation."""
    structure = TreeStructure.model_validate(tree.structure)
    warnings = validate_tree_structure(structure)
    response = TreeResponse.model_validate(tree)
    response.warnings = warnings
    return response


# --- Multi-trees ---


@router.get("s", response_model=list[TreeListItem])
async def list_trees(tree_service: TreeServiceDep):
    """
    List all decision trees.

    Returns a summary of each tree (without the full structure).
    """
    return await tree_service.list_trees()


@router.get("", response_model=TreeResponse | None)
async def get_tree(
    tree_service: TreeServiceDep,
    tree_id: int | None = None,
):
    """
    Retrieve a decision tree.

    If tree_id is not provided, returns the default tree.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        return None
    return _tree_response_with_warnings(tree)


@router.post("", response_model=TreeResponse, status_code=status.HTTP_201_CREATED)
async def create_tree(
    data: TreeCreate,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """Create a new decision tree."""
    tree = await tree_service.create_tree(data)
    return _tree_response_with_warnings(tree)


# --- Decision-as-Code (export/import) ---
# IMPORTANT: /import must come before /{tree_id} to prevent
# FastAPI from parsing "import" as an int (tree_id)


@router.post("/import", response_model=TreeResponse, status_code=status.HTTP_201_CREATED)
async def import_tree(
    data: TreeImportRequest,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """Import a tree from a Decision-as-Code file (JSON)."""
    tree = await tree_service.import_tree(data)
    return _tree_response_with_warnings(tree)


@router.get("/{tree_id}/export")
async def export_tree(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """Export a tree in Decision-as-Code format (JSON)."""
    result = await tree_service.export_tree(tree_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )

    # Sanitized filename via existing module
    raw_name = f"{result.tree.name}_tree.json"
    filename = sanitize_filename(raw_name) or "tree_export.json"

    return Response(
        content=result.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{tree_id}", response_model=TreeResponse)
async def update_tree(
    tree_id: int,
    data: TreeUpdate,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
    create_version: bool = True,
):
    """
    Update a decision tree.

    Args:
        tree_id: Tree ID
        data: Update data
        create_version: If True (default), creates a backup version
    """
    tree = await tree_service.update_tree(tree_id, data, create_version)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )
    return _tree_response_with_warnings(tree)


@router.delete("/{tree_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tree(
    tree_id: int,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """
    Delete a decision tree.

    The default tree cannot be deleted.
    """
    try:
        deleted = await tree_service.delete_tree(tree_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tree {tree_id} not found",
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
    _=require_role("admin"),
):
    """
    Duplicate a decision tree.

    Creates a copy of the tree with optionally its associated assets.
    """
    tree = await tree_service.duplicate_tree(tree_id, request)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )
    return tree


@router.put("/{tree_id}/api-config", response_model=TreeResponse)
async def update_api_config(
    tree_id: int,
    config: TreeApiConfig,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """
    Configure dedicated API access for a tree.

    Allows enabling/disabling the /tree/{slug}/evaluate endpoint.
    """
    try:
        tree = await tree_service.update_api_config(tree_id, config)
        if not tree:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tree {tree_id} not found",
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
    _=require_role("admin"),
):
    """
    Set a tree as the default tree.

    The default tree is used by /api/v1/evaluate when no tree is specified.
    """
    tree = await tree_service.set_default_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )
    return tree


@router.get("/{tree_id}/structure", response_model=TreeStructure)
async def get_tree_structure(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """Retrieve only the tree structure (for the frontend)."""
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )
    return tree_service.get_tree_structure(tree)


# --- Versioning ---


@router.get("/{tree_id}/versions", response_model=list[TreeVersionResponse])
async def list_versions(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """List all versions of a tree."""
    versions = await tree_service.get_versions(tree_id)
    return versions


@router.get("/versions/{version_id}", response_model=TreeVersionResponse)
async def get_version(
    version_id: int,
    tree_service: TreeServiceDep,
):
    """Retrieve a specific version."""
    version = await tree_service.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_id} not found",
        )
    return version


@router.post("/{tree_id}/restore/{version_id}", response_model=TreeResponse)
async def restore_version(
    tree_id: int,
    version_id: int,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """
    Restore a previous version of the tree.

    The current state is saved as a new version before restoration.
    """
    tree = await tree_service.restore_version(tree_id, version_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tree or version not found",
        )
    return tree


@router.post("/diagnose", response_model=DiagnosticResult)
async def diagnose_tree_endpoint(
    request: DiagnosticRequest,
):
    """Analyze a tree and return diagnostics."""
    return diagnose_tree(request.structure)
