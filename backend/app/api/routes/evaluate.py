"""
API routes for vulnerability evaluation.
Multi-tree support with dedicated endpoints per slug.
CSV/JSON export support for results.
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import AssetServiceDep, TreeServiceDep, read_upload_with_limit
from app.filename_validation import sanitize_filename
from app.config import settings
from app.engine import BatchProcessor, InferenceEngine
from app.engine.export import export_csv, export_json
from app.models import Tree
from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    ExportRequest,
    SingleEvaluationRequest,
)
from app.schemas.tree import TreeStructure
from app.schemas.vulnerability import VulnerabilityInput
from app.services.webhook_dispatch import schedule_webhook_dispatch

router = APIRouter()


async def _get_engine_and_lookups(
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    tree_id: int | None = None,
    asset_ids: list[str] | None = None,
) -> tuple[InferenceEngine, dict[str, dict[str, dict[str, Any]]], int]:
    """
    Helper to get the engine and lookups.

    Args:
        tree_service: Tree service
        asset_service: Asset service
        tree_id: Specific tree ID (default if not provided)
        asset_ids: List of asset_ids to load

    Returns:
        Tuple (engine, lookups, tree_id)
    """
    tree = await tree_service.get_tree(tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No decision tree configured",
        )

    structure = tree_service.get_tree_structure(tree)
    engine = InferenceEngine(structure)

    # Prepare lookup cache for assets (filtered by tree)
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    if "assets" in engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids)

    return engine, lookups, tree.id


async def _get_engine_for_tree(
    tree: Tree,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    asset_ids: list[str] | None = None,
) -> tuple[InferenceEngine, dict[str, dict[str, dict[str, Any]]]]:
    """Helper to get the engine for a specific tree."""
    structure = tree_service.get_tree_structure(tree)
    engine = InferenceEngine(structure)

    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    if "assets" in engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids)

    return engine, lookups


@router.post("/single", response_model=EvaluationResult)
async def evaluate_single(
    request: SingleEvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Evaluate a single vulnerability (real-time).

    Uses the default tree. For a specific tree, use /tree/{slug}/evaluate.
    """
    # Extract asset_ids for lookup
    asset_ids = []
    if request.vulnerability.asset_id:
        asset_ids.append(request.vulnerability.asset_id)

    engine, lookups, tree_id = await _get_engine_and_lookups(
        tree_service, asset_service, asset_ids=asset_ids
    )

    result = engine.evaluate(
        request.vulnerability,
        lookups,
        request.include_path,
    )

    # Fire webhooks in background (independent DB session)
    event = f"on_{result.decision.lower().replace('*', '_star')}"
    payload = {
        "event": event,
        "vuln_id": result.vuln_id,
        "decision": result.decision,
        "decision_color": result.decision_color,
    }
    schedule_webhook_dispatch(tree_id, event, payload)

    return result


@router.post("", response_model=EvaluationResponse)
async def evaluate_batch(
    request: EvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Evaluate a batch of vulnerabilities.

    Uses the default tree. Optimized to process up to 50,000 vulnerabilities.
    """
    if len(request.vulnerabilities) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch trop grand. Maximum: {settings.max_batch_size}",
        )

    tree = await tree_service.get_tree()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No decision tree configured",
        )

    structure = tree_service.get_tree_structure(tree)

    # Extract all asset_ids for lookup
    asset_ids = [
        v.asset_id for v in request.vulnerabilities
        if v.asset_id is not None
    ]

    # Prepare lookups (filtered by tree)
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        request.vulnerabilities,
        lookups,
        request.include_path,
    )

    # Fire webhooks in background (independent DB session)
    payload = {
        "event": "on_batch_complete",
        "total": response.total,
        "success_count": response.success_count,
        "error_count": response.error_count,
        "decision_summary": response.decision_summary,
    }
    schedule_webhook_dispatch(tree.id, "on_batch_complete", payload)

    return response


@router.post("/csv", response_model=EvaluationResponse)
async def evaluate_csv(
    file: UploadFile,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    include_path: bool = False,
):
    """
    Evaluate vulnerabilities from a CSV file.

    The CSV must have columns corresponding to the fields expected by the tree.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name or not safe_name.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be in CSV format",
        )

    content = await read_upload_with_limit(file)

    tree = await tree_service.get_tree()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No decision tree configured",
        )

    structure = tree_service.get_tree_structure(tree)

    # Parse CSV with Polars
    df = BatchProcessor.from_csv(content)

    if len(df) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(df)} rows). Maximum: {settings.max_batch_size}",
        )

    # Convert to list of VulnerabilityInput
    vulnerabilities = []
    for row in df.iter_rows(named=True):
        vuln = _row_to_vuln(row)
        vulnerabilities.append(vuln)

    # Prepare lookups (filtered by tree)
    asset_ids = [v.asset_id for v in vulnerabilities if v.asset_id]
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        vulnerabilities,
        lookups,
        include_path,
    )

    # Fire webhooks in background (independent DB session)
    payload = {
        "event": "on_batch_complete",
        "total": response.total,
        "success_count": response.success_count,
        "error_count": response.error_count,
        "decision_summary": response.decision_summary,
    }
    schedule_webhook_dispatch(tree.id, "on_batch_complete", payload)

    return response


# --- Export endpoints ---


def _build_export_response(
    response: EvaluationResponse,
    fmt: str,
    tree_name: str | None = None,
) -> StreamingResponse:
    """Build the StreamingResponse for CSV or JSON export."""
    timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "csv":
        return StreamingResponse(
            export_csv(response.results, include_path=True),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="results_{timestamp}.csv"'
            },
        )
    else:
        json_content = export_json(response, tree_name=tree_name)
        return StreamingResponse(
            iter([json_content]),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="results_{timestamp}.json"'
            },
        )


@router.post("/export")
async def export_batch(
    request: ExportRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Evaluate a batch of vulnerabilities and return a downloadable CSV or JSON file.
    """
    if len(request.vulnerabilities) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch trop grand. Maximum: {settings.max_batch_size}",
        )

    tree = await tree_service.get_tree()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No decision tree configured",
        )

    structure = tree_service.get_tree_structure(tree)

    asset_ids = [v.asset_id for v in request.vulnerabilities if v.asset_id is not None]
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        request.vulnerabilities,
        lookups,
        True,  # always include path for exports
    )

    return _build_export_response(response, request.format, tree.name)


@router.post("/export/csv")
async def export_csv_file(
    file: UploadFile,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    format: Literal["csv", "json"] = Query(default="csv"),
):
    """
    Evaluate a CSV file and return a downloadable CSV or JSON file.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name or not safe_name.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be in CSV format",
        )

    content = await read_upload_with_limit(file)

    tree = await tree_service.get_tree()
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No decision tree configured",
        )

    structure = tree_service.get_tree_structure(tree)
    df = BatchProcessor.from_csv(content)

    if len(df) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(df)} rows). Maximum: {settings.max_batch_size}",
        )

    vulnerabilities = [_row_to_vuln(row) for row in df.iter_rows(named=True)]

    asset_ids = [v.asset_id for v in vulnerabilities if v.asset_id]
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(vulnerabilities, lookups, True)

    return _build_export_response(response, format, tree.name)


# --- Dedicated endpoint per tree slug ---


@router.post("/tree/{slug}", response_model=EvaluationResult)
async def evaluate_by_slug(
    slug: str,
    request: SingleEvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Evaluate a vulnerability with a specific tree identified by its slug.

    The tree must have api_enabled=true and an api_slug configured.
    """
    tree = await tree_service.get_tree_by_slug(slug)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree '{slug}' not found or API disabled",
        )

    # Extract asset_ids for lookup
    asset_ids = []
    if request.vulnerability.asset_id:
        asset_ids.append(request.vulnerability.asset_id)

    engine, lookups = await _get_engine_for_tree(
        tree, tree_service, asset_service, asset_ids
    )

    result = engine.evaluate(
        request.vulnerability,
        lookups,
        request.include_path,
    )

    # Fire webhooks in background (independent DB session)
    event = f"on_{result.decision.lower().replace('*', '_star')}"
    payload = {
        "event": event,
        "vuln_id": result.vuln_id,
        "decision": result.decision,
        "decision_color": result.decision_color,
    }
    asyncio.create_task(dispatch_webhooks(tree.id, event, payload))

    return result


@router.post("/tree/{slug}/batch", response_model=EvaluationResponse)
async def evaluate_batch_by_slug(
    slug: str,
    request: EvaluationRequest,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
):
    """
    Evaluate a batch of vulnerabilities with a specific tree identified by its slug.

    The tree must have api_enabled=true and an api_slug configured.
    """
    if len(request.vulnerabilities) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch trop grand. Maximum: {settings.max_batch_size}",
        )

    tree = await tree_service.get_tree_by_slug(slug)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tree '{slug}' not found or API disabled",
        )

    structure = tree_service.get_tree_structure(tree)

    # Extract all asset_ids for lookup
    asset_ids = [
        v.asset_id for v in request.vulnerabilities
        if v.asset_id is not None
    ]

    # Prepare lookups (filtered by tree)
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    processor = BatchProcessor(structure, settings.batch_chunk_size)
    if "assets" in processor.engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id, asset_ids or None)

    response = await processor.process_batch(
        request.vulnerabilities,
        lookups,
        request.include_path,
    )

    # Fire webhooks in background (independent DB session)
    payload = {
        "event": "on_batch_complete",
        "total": response.total,
        "success_count": response.success_count,
        "error_count": response.error_count,
        "decision_summary": response.decision_summary,
    }
    schedule_webhook_dispatch(tree.id, "on_batch_complete", payload)

    return response


def _row_to_vuln(row: dict[str, Any]) -> VulnerabilityInput:
    """Convert a DataFrame row to VulnerabilityInput."""
    standard_fields = {
        "id", "cve_id", "cvss_score", "cvss_vector",
        "epss_score", "epss_percentile", "kev",
        "asset_id", "hostname", "ip_address",
    }
    standard_data = {k: v for k, v in row.items() if k in standard_fields}
    extra_data = {k: v for k, v in row.items() if k not in standard_fields}
    return VulnerabilityInput(**standard_data, extra=extra_data)
