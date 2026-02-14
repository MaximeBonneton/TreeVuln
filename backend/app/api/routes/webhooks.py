"""
Routes API pour la gestion des webhooks sortants.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import WebhookServiceDep
from app.schemas.webhook import (
    WebhookCreate,
    WebhookLogResponse,
    WebhookResponse,
    WebhookTestResult,
    WebhookUpdate,
)

router = APIRouter()


@router.get("/tree/{tree_id}/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    tree_id: int,
    webhook_service: WebhookServiceDep,
):
    """Liste les webhooks configurés pour un arbre."""
    return await webhook_service.list_webhooks(tree_id)


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
    return await webhook_service.create_webhook(tree_id, data)


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    webhook_service: WebhookServiceDep,
):
    """Met à jour un webhook."""
    webhook = await webhook_service.update_webhook(webhook_id, data)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook non trouvé",
        )
    return webhook


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    webhook_service: WebhookServiceDep,
):
    """Supprime un webhook."""
    deleted = await webhook_service.delete_webhook(webhook_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook non trouvé",
        )


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResult)
async def test_webhook(
    webhook_id: int,
    webhook_service: WebhookServiceDep,
):
    """Envoie un payload de test au webhook."""
    return await webhook_service.test_webhook(webhook_id)


@router.get("/webhooks/{webhook_id}/logs", response_model=list[WebhookLogResponse])
async def get_webhook_logs(
    webhook_id: int,
    webhook_service: WebhookServiceDep,
    limit: int = 50,
):
    """Récupère l'historique des envois d'un webhook."""
    return await webhook_service.get_logs(webhook_id, limit)
