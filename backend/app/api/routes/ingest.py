"""
Routes API pour les webhooks entrants (ingestion).
Reçoit des vulnérabilités depuis des sources externes, applique le mapping
et évalue automatiquement si configuré.
"""

import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Query, Request, status

from app.api.deps import AssetServiceDep, IngestServiceDep, TreeServiceDep, WebhookServiceDep
from app.config import settings
from app.crypto import decrypt_secret
from app.engine import InferenceEngine
from app.schemas.ingest import (
    IngestEndpointCreate,
    IngestEndpointResponse,
    IngestEndpointUpdate,
    IngestEndpointWithKeyResponse,
    IngestLogResponse,
    IngestResult,
)

# Route publique (authentifiée par X-API-Key)
public_router = APIRouter()

# Routes d'administration (protégées par RequireAdmin via api/__init__.py)
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
    x_api_key: str = Header(description="Clé API de l'endpoint d'ingestion"),
):
    """
    Reçoit et évalue des vulnérabilités via un endpoint d'ingestion.

    L'authentification se fait par header X-API-Key.
    Le payload est une liste de vulnérabilités au format JSON.
    """
    # Limite la taille du payload pour prévenir l'épuisement mémoire
    if len(payload) > settings.max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload trop grand ({len(payload)} éléments). Maximum : {settings.max_batch_size}",
        )

    endpoint = await ingest_service.get_endpoint_by_slug(slug)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{slug}' non trouvé ou désactivé",
        )

    # Déchiffre la clé stockée puis comparaison constant-time (timing attacks)
    try:
        stored_plain = (
            decrypt_secret(endpoint.api_key, settings.admin_api_key)
            if settings.admin_api_key
            else endpoint.api_key
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de déchiffrement de la clé API",
        )
    if not hmac.compare_digest(stored_plain, x_api_key):
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
        from app.services.webhook_dispatch import schedule_webhook_dispatch

        summary_payload = {
            "event": "on_ingest_complete",
            "source": slug,
            "received": result.received,
            "evaluated": result.evaluated,
            "errors": result.errors,
        }
        schedule_webhook_dispatch(
            endpoint.tree_id, "on_batch_complete", summary_payload
        )

    return result


# --- CRUD endpoints d'ingestion (admin) ---


@admin_router.get("/tree/{tree_id}/ingest-endpoints", response_model=list[IngestEndpointResponse])
async def list_ingest_endpoints(
    tree_id: int,
    ingest_service: IngestServiceDep,
):
    """Liste les endpoints d'ingestion d'un arbre (clé API masquée)."""
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
):
    """Crée un nouveau endpoint d'ingestion. Retourne la clé API en clair (une seule fois)."""
    endpoint, plain_key = await ingest_service.create_endpoint(tree_id, data)
    resp = IngestEndpointWithKeyResponse.model_validate(endpoint)
    resp.api_key = plain_key
    return resp


@admin_router.put("/ingest-endpoints/{endpoint_id}", response_model=IngestEndpointResponse)
async def update_ingest_endpoint(
    endpoint_id: int,
    data: IngestEndpointUpdate,
    ingest_service: IngestServiceDep,
):
    """Met à jour un endpoint d'ingestion (clé API masquée)."""
    endpoint = await ingest_service.update_endpoint(endpoint_id, data)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint non trouvé",
        )
    return IngestEndpointResponse.from_endpoint(endpoint)


@admin_router.delete("/ingest-endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@admin_router.post(
    "/ingest-endpoints/{endpoint_id}/regenerate-key",
    response_model=IngestEndpointWithKeyResponse,
)
async def regenerate_api_key(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
):
    """Régénère la clé API d'un endpoint. Retourne la clé API en clair (une seule fois)."""
    result = await ingest_service.regenerate_key(endpoint_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint non trouvé",
        )
    endpoint, plain_key = result
    resp = IngestEndpointWithKeyResponse.model_validate(endpoint)
    resp.api_key = plain_key
    return resp


@admin_router.get("/ingest-endpoints/{endpoint_id}/logs", response_model=list[IngestLogResponse])
async def get_ingest_logs(
    endpoint_id: int,
    ingest_service: IngestServiceDep,
    limit: int = Query(default=50, ge=1, le=1000),
):
    """Récupère l'historique de réception d'un endpoint."""
    return await ingest_service.get_logs(endpoint_id, limit)
