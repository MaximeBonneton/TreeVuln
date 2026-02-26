"""
Routes API pour la gestion des webhooks sortants.
Toutes les routes sont scopées par tree_id pour la sécurité.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import WebhookServiceDep
from app.models.webhook import Webhook
from app.schemas.webhook import (
    WebhookCreate,
    WebhookLogResponse,
    WebhookResponse,
    WebhookTestResult,
    WebhookUpdate,
)

router = APIRouter()


def _to_response(w: Webhook) -> WebhookResponse:
    """Convertit un webhook ORM en réponse API (masque le secret)."""
    return WebhookResponse(
        id=w.id,
        tree_id=w.tree_id,
        name=w.name,
        url=w.url,
        has_secret=bool(w.secret),
        headers=dict(w.headers) if w.headers else {},
        events=list(w.events) if w.events else [],
        is_active=w.is_active,
        created_at=w.created_at,
        updated_at=w.updated_at,
    )


@router.get("/tree/{tree_id}/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    tree_id: int,
    webhook_service: WebhookServiceDep,
):
    """Liste les webhooks configurés pour un arbre."""
    webhooks = await webhook_service.list_webhooks(tree_id)
    return [_to_response(w) for w in webhooks]


@router.post(
    "/tree/{tree_id}/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    tree_id: int,
    data: WebhookCreate,
    webhook_service: WebhookServiceDep,
):
    """Crée un nouveau webhook pour un arbre."""
    webhook = await webhook_service.create_webhook(tree_id, data)
    return _to_response(webhook)


@router.put("/tree/{tree_id}/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    tree_id: int,
    webhook_id: int,
    data: WebhookUpdate,
    webhook_service: WebhookServiceDep,
):
    """Met à jour un webhook."""
    webhook = await webhook_service.update_webhook(webhook_id, data)
    if not webhook or webhook.tree_id != tree_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook non trouvé",
        )
    return _to_response(webhook)


@router.delete(
    "/tree/{tree_id}/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_webhook(
    tree_id: int,
    webhook_id: int,
    webhook_service: WebhookServiceDep,
):
    """Supprime un webhook."""
    # Vérifie l'appartenance au tree
    webhook = await webhook_service.get_webhook(webhook_id)
    if not webhook or webhook.tree_id != tree_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook non trouvé",
        )
    await webhook_service.delete_webhook(webhook_id)


@router.post(
    "/tree/{tree_id}/webhooks/{webhook_id}/test",
    response_model=WebhookTestResult,
)
async def test_webhook(
    tree_id: int,
    webhook_id: int,
    webhook_service: WebhookServiceDep,
):
    """Envoie un payload de test au webhook."""
    # Vérifie l'appartenance au tree
    webhook = await webhook_service.get_webhook(webhook_id)
    if not webhook or webhook.tree_id != tree_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook non trouvé",
        )
    return await webhook_service.test_webhook(webhook_id)


@router.get(
    "/tree/{tree_id}/webhooks/{webhook_id}/logs",
    response_model=list[WebhookLogResponse],
)
async def get_webhook_logs(
    tree_id: int,
    webhook_id: int,
    webhook_service: WebhookServiceDep,
    limit: int = Query(default=50, ge=1, le=1000),
):
    """Récupère l'historique des envois d'un webhook."""
    # Vérifie l'appartenance au tree
    webhook = await webhook_service.get_webhook(webhook_id)
    if not webhook or webhook.tree_id != tree_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook non trouvé",
        )
    return await webhook_service.get_logs(webhook_id, limit)
