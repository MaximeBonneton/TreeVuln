"""
Routes API pour les webhooks entrants (ingestion).
Reçoit des vulnérabilités depuis des sources externes, applique le mapping
et évalue automatiquement si configuré.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Header, Request, status

from app.api.deps import AssetServiceDep, IngestServiceDep, TreeServiceDep, WebhookServiceDep
from app.engine import InferenceEngine
from app.schemas.ingest import (
    IngestEndpointCreate,
    IngestEndpointResponse,
    IngestEndpointUpdate,
    IngestLogResponse,
    IngestResult,
)

router = APIRouter()


@router.post("/ingest/{slug}", response_model=IngestResult)
async def ingest_vulnerabilities(
    slug: str,
    payload: list[dict[str, Any]],
    request: Request,
    ingest_service: IngestServiceDep,
    tree_service: TreeServiceDep,
    asset_service: AssetServiceDep,
    webhook_service: WebhookServiceDep,
    x_api_key: str = Header(description="Clé API de l'endpoint d'ingestion"),
):
    """
    Reçoit et évalue des vulnérabilités via un endpoint d'ingestion.

    L'authentification se fait par header X-API-Key.
    Le payload est une liste de vulnérabilités au format JSON.
    """
    endpoint = await ingest_service.get_endpoint_by_slug(slug)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{slug}' non trouvé ou désactivé",
        )

    # Vérification de la clé API
    if endpoint.api_key != x_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide",
        )

    # Charge l'arbre et le moteur
    tree = await tree_service.get_tree(endpoint.tree_id)
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arbre associé non trouvé",
        )

    structure = tree_service.get_tree_structure(tree)
    engine = InferenceEngine(structure)

    # Charge les lookups
    lookups: dict[str, dict[str, dict[str, Any]]] = {}
    if "assets" in engine.get_lookup_tables():
        lookups["assets"] = await asset_service.get_lookup_cache(tree.id)

    # Récupère l'IP source
    source_ip = request.client.host if request.client else None

    # Ingère et évalue
    result = await ingest_service.ingest(
        endpoint, payload, engine, lookups, source_ip
    )

    # Déclenche les webhooks sortants si évaluation automatique
    if endpoint.auto_evaluate and result.evaluated > 0:
        import asyncio
        summary_payload = {
            "event": "on_ingest_complete",
            "source": slug,
            "received": result.received,
            "evaluated": result.evaluated,
            "errors": result.errors,
        }
        asyncio.create_task(
            webhook_service.fire_webhooks(endpoint.tree_id, "on_batch_complete", summary_payload)
        )

    return result


# --- CRUD endpoints d'ingestion ---


@router.get("/tree/{tree_id}/ingest-endpoints", response_model=list[IngestEndpointResponse])
async def list_ingest_endpoints(
    tree_id: int,
    ingest_service: IngestServiceDep,
):
    """Liste les endpoints d'ingestion d'un arbre."""
    return await ingest_service.list_endpoints(tree_id)


@router.post(
    "/tree/{tree_id}/ingest-endpoints",
    response_model=IngestEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ingest_endpoint(
    tree_id: int,
    data: IngestEndpointCreate,
    ingest_service: IngestServiceDep,
):
    """Crée un nouveau endpoint d'ingestion."""
    return await ingest_service.create_endpoint(tree_id, data)


@router.put("/ingest-endpoints/{endpoint_id}", response_model=IngestEndpointResponse)
async def update_ingest_endpoint(
    endpoint_id: int,
    data: IngestEndpointUpdate,
    ingest_service: IngestServiceDep,
):
    """Met à jour un endpoint d'ingestion."""
    endpoint = await ingest_service.update_endpoint(endpoint_id, data)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint non trouvé",
        )
    return endpoint


@router.delete("/ingest-endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingest_endpoint(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
):
    """Supprime un endpoint d'ingestion."""
    deleted = await ingest_service.delete_endpoint(endpoint_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint non trouvé",
        )


@router.post(
    "/ingest-endpoints/{endpoint_id}/regenerate-key",
    response_model=IngestEndpointResponse,
)
async def regenerate_api_key(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
):
    """Régénère la clé API d'un endpoint."""
    endpoint = await ingest_service.regenerate_key(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint non trouvé",
        )
    return endpoint


@router.get("/ingest-endpoints/{endpoint_id}/logs", response_model=list[IngestLogResponse])
async def get_ingest_logs(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
    limit: int = 50,
):
    """Récupère l'historique de réception d'un endpoint."""
    return await ingest_service.get_logs(endpoint_id, limit)
