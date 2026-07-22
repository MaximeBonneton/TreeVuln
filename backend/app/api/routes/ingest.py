"""
API routes for incoming webhooks (ingestion).
Receives vulnerabilities from external sources, applies field mapping
and evaluates automatically if configured.
"""

import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Query, Request, status

from app.api.deps import AssetServiceDep, IngestServiceDep, TreeServiceDep, WebhookServiceDep, require_role
from app.config import settings
from app.crypto import decrypt_secret
from app.engine import InferenceEngine
from app.schemas.evaluation import EvaluationResult
from app.schemas.ingest import (
    IngestEndpointCreate,
    IngestEndpointResponse,
    IngestEndpointUpdate,
    IngestEndpointWithKeyResponse,
    IngestLogResponse,
    IngestResult,
)
from app.services.enisa_service import record_candidates
from app.services.ingest_service import transform_payload

# Public route (authenticated via X-API-Key)
public_router = APIRouter()

# Administration routes (protected by RequireAuth + require_role("admin") per-route)
admin_router = APIRouter()


@public_router.post("/ingest/{slug}", response_model=IngestResult)
async def ingest_vulnerabilities(
    slug: str,
    payload: list[dict[str, Any]],
    request: Request,
    ingest_service: IngestServiceDep,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    webhook_service: WebhookServiceDep,
    x_api_key: str = Header(description="API key for the ingestion endpoint"),
):
    """
    Receive and evaluate vulnerabilities via an ingestion endpoint.

    Authentication is done via the X-API-Key header.
    The payload is a list of vulnerabilities in JSON format.
    """
    # Limit payload size to prevent memory exhaustion
    if len(payload) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload too large ({len(payload)} items). Maximum: {settings.max_batch_size}",
        )

    endpoint = await ingest_service.get_endpoint_by_slug(slug)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{slug}' not found or disabled",
        )

    # Decrypt stored key then constant-time comparison (timing attacks)
    try:
        stored_plain = decrypt_secret(endpoint.api_key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key decryption error",
        )
    if not hmac.compare_digest(stored_plain, x_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    # Load the tree and engine
    tree = await tree_service.get_tree(endpoint.tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated tree not found",
        )

    structure = tree_service.get_tree_structure(tree)
    engine = InferenceEngine(structure)

    # Load lookups
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    if "assets" in engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id)

    # Get source IP
    source_ip = request.client.host if request.client else None

    # Ingest and evaluate
    result = await ingest_service.ingest(
        endpoint, payload, engine, lookups, source_ip
    )

    # Trigger outgoing webhooks if auto-evaluation is enabled
    if endpoint.auto_evaluate and result.evaluated > 0:
        from app.services.webhook_dispatch import schedule_webhook_dispatch

        summary_payload = {
            # Cohérent avec l'événement réellement dispatché ci-dessous
            # (on_batch_complete est la valeur reconnue par VALID_EVENTS).
            "event": "on_batch_complete",
            "source": slug,
            "received": result.received,
            "evaluated": result.evaluated,
            "errors": result.errors,
        }
        schedule_webhook_dispatch(
            endpoint.tree_id, "on_batch_complete", summary_payload
        )

    # Candidats ENISA (indépendant, n'affecte jamais la réponse). On
    # reconstruit les paires (résultat, vuln mappée) à partir du payload
    # brut et du mapping de l'endpoint : _ingest_entries_sync ne renvoie
    # que des dicts (compatibilité de l'API d'ingestion), pas d'objets
    # EvaluationResult ni les vulns mappées.
    if endpoint.auto_evaluate:
        evaluated: list[tuple[EvaluationResult, dict[str, Any]]] = []
        for entry, result_dict in zip(payload, result.results):
            if "decision" not in result_dict:
                continue  # entrée en erreur avant évaluation
            mapped = transform_payload(entry, endpoint.field_mapping)
            evaluated.append((EvaluationResult.model_validate(result_dict), mapped))
        if evaluated:
            await record_candidates(endpoint.tree_id, structure.model_dump(), evaluated)

    return result


# --- CRUD ingestion endpoints (admin) ---


@admin_router.get("/tree/{tree_id}/ingest-endpoints", response_model=list[IngestEndpointResponse])
async def list_ingest_endpoints(
    tree_id: int,
    ingest_service: IngestServiceDep,
    _=require_role("admin"),
):
    """List ingestion endpoints for a tree (API key masked)."""
    endpoints = await ingest_service.list_endpoints(tree_id)
    return [IngestEndpointResponse.from_endpoint(ep) for ep in endpoints]


@admin_router.post(
    "/tree/{tree_id}/ingest-endpoints",
    response_model=IngestEndpointWithKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ingest_endpoint(
    tree_id: int,
    data: IngestEndpointCreate,
    ingest_service: IngestServiceDep,
    _=require_role("admin"),
):
    """Create a new ingestion endpoint. Returns the API key in plaintext (once only)."""
    endpoint, plain_key = await ingest_service.create_endpoint(tree_id, data)
    resp = IngestEndpointWithKeyResponse.model_validate(endpoint)
    resp.api_key = plain_key
    return resp


@admin_router.put("/ingest-endpoints/{endpoint_id}", response_model=IngestEndpointResponse)
async def update_ingest_endpoint(
    endpoint_id: int,
    data: IngestEndpointUpdate,
    ingest_service: IngestServiceDep,
    _=require_role("admin"),
):
    """Update an ingestion endpoint (API key masked)."""
    endpoint = await ingest_service.update_endpoint(endpoint_id, data)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )
    return IngestEndpointResponse.from_endpoint(endpoint)


@admin_router.delete("/ingest-endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingest_endpoint(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
    _=require_role("admin"),
):
    """Delete an ingestion endpoint."""
    deleted = await ingest_service.delete_endpoint(endpoint_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )


@admin_router.post(
    "/ingest-endpoints/{endpoint_id}/regenerate-key",
    response_model=IngestEndpointWithKeyResponse,
)
async def regenerate_api_key(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
    _=require_role("admin"),
):
    """Regenerate an endpoint's API key. Returns the API key in plaintext (once only)."""
    result = await ingest_service.regenerate_key(endpoint_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )
    endpoint, plain_key = result
    resp = IngestEndpointWithKeyResponse.model_validate(endpoint)
    resp.api_key = plain_key
    return resp


@admin_router.get("/ingest-endpoints/{endpoint_id}/logs", response_model=list[IngestLogResponse])
async def get_ingest_logs(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
    _=require_role("admin"),
    limit: int = Query(default=50, ge=1, le=1000),
):
    """Retrieve the reception history of an endpoint."""
    return await ingest_service.get_logs(endpoint_id, limit)
