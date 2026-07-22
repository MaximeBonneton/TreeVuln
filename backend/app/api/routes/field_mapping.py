"""
API routes for managing field mapping.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import TreeServiceDep, read_upload_with_limit, require_role
from app.filename_validation import sanitize_filename
from app.engine.cvss import get_cvss_field_definitions
from app.engine.sbom import get_sbom_field_definitions
from app.schemas.field_mapping import (
    FieldDefinition,
    FieldMapping,
    FieldMappingUpdate,
    ScanResult,
)
from app.services import field_mapping_service

# Per-tree routes (mounted under /tree)
router = APIRouter()

# Global routes (mounted under /mapping)
global_router = APIRouter()


@router.get("/{tree_id}/mapping", response_model=FieldMapping | None)
async def get_mapping(
    tree_id: int,
    tree_service: TreeServiceDep,
):
    """
    Retrieve the field mapping for a tree.

    Returns null if no mapping is configured.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )

    structure = tree_service.get_tree_structure(tree)
    return field_mapping_service.get_mapping_from_tree_metadata(structure.metadata)


@router.put("/{tree_id}/mapping", response_model=FieldMapping)
async def update_mapping(
    tree_id: int,
    data: FieldMappingUpdate,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """
    Update the field mapping for a tree.

    The mapping is stored in the tree metadata.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )

    structure = tree_service.get_tree_structure(tree)

    # Retrieve existing mapping to get the version
    existing = field_mapping_service.get_mapping_from_tree_metadata(structure.metadata)
    new_version = (existing.version + 1) if existing else 1

    # Create the new mapping
    new_mapping = FieldMapping(
        fields=data.fields,
        source=data.source,
        version=new_version,
    )

    # Update the metadata
    structure.metadata = field_mapping_service.set_mapping_in_tree_metadata(
        structure.metadata, new_mapping
    )

    # Save without creating a version (metadata modification)
    from app.schemas.tree import TreeUpdate

    await tree_service.update_tree(
        tree_id,
        TreeUpdate(structure=structure),
        create_version=False,
    )

    return new_mapping


@router.post("/{tree_id}/mapping/import", response_model=FieldMapping)
async def import_mapping(
    tree_id: int,
    file: UploadFile = File(...),
    tree_service: TreeServiceDep = None,
    _=require_role("admin"),
):
    """
    Import a mapping from a JSON file.

    The file must contain an object with a list of FieldDefinition.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )

    # Read the file (with size limit)
    content = await read_upload_with_limit(file)
    try:
        import json

        mapping_data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {e}",
        )

    # Validate the mapping
    try:
        # Accept either a full FieldMapping or just a list of fields
        if isinstance(mapping_data, list):
            mapping_data = {"fields": mapping_data}
        imported_mapping = FieldMapping.model_validate(mapping_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mapping format: {e}",
        )

    # Update with the appropriate source
    structure = tree_service.get_tree_structure(tree)
    existing = field_mapping_service.get_mapping_from_tree_metadata(structure.metadata)
    new_version = (existing.version + 1) if existing else 1

    new_mapping = FieldMapping(
        fields=imported_mapping.fields,
        source=f"import:{sanitize_filename(file.filename) or 'unknown'}",
        version=new_version,
    )

    structure.metadata = field_mapping_service.set_mapping_in_tree_metadata(
        structure.metadata, new_mapping
    )

    from app.schemas.tree import TreeUpdate

    await tree_service.update_tree(
        tree_id,
        TreeUpdate(structure=structure),
        create_version=False,
    )

    return new_mapping


@router.delete("/{tree_id}/mapping", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    tree_id: int,
    tree_service: TreeServiceDep,
    _=require_role("admin"),
):
    """
    Delete the field mapping for a tree.

    Existing nodes keep their configurations but users will need
    to manually enter field names again.
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree {tree_id} not found",
        )

    structure = tree_service.get_tree_structure(tree)
    structure.metadata = field_mapping_service.remove_mapping_from_tree_metadata(
        structure.metadata
    )

    from app.schemas.tree import TreeUpdate

    await tree_service.update_tree(
        tree_id,
        TreeUpdate(structure=structure),
        create_version=False,
    )


@global_router.post("/scan", response_model=ScanResult)
async def scan_file(
    file: UploadFile = File(...),
):
    """
    Scan a CSV or JSON file to detect available fields.

    Analyzes up to 100 rows to infer types and collect examples.
    The result can be used to create or update a mapping.

    Supported formats:
    - CSV with headers
    - JSON (array of objects or object with a key containing an array)
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename required",
        )

    content = await read_upload_with_limit(file)
    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        )

    result = field_mapping_service.scan_file_content(content_str, safe_name)
    return result


@global_router.get("/cvss-fields", response_model=list[FieldDefinition])
async def get_cvss_fields():
    """
    Return the definitions of virtual fields (CVSS + SBOM).

    CVSS fields are extracted from cvss_vector during evaluation
    (CVSS 3.1 and 4.0) ; SBOM fields are computed from the asset's
    ingested SBOM (component presence matching).
    """
    return get_cvss_field_definitions() + get_sbom_field_definitions()
