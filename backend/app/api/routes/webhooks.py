"""
API routes for managing outgoing webhooks.
All routes are scoped by tree_id for security.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import WebhookServiceDep, require_role
from app.models.webhook import Webhook
from app.schemas.webhook import (
    WebhookCreate,
    WebhookLogResponse,
    WebhookResponse,
    WebhookTestResult,
    WebhookUpdate,
)
from app.services.webhook_service import WebhookService

router = APIRouter()


async def _get_owned_webhook(
    webhook_service: WebhookService, tree_id: int, webhook_id: int
) -> Webhook:
    """
    Charge le webhook et vérifie son appartenance à l'arbre (404 sinon).

    Contrôle de sécurité commun à toutes les routes scopées par tree_id :
    centralisé ici pour qu'aucune route ne puisse l'oublier (C-7 existait
    précisément parce qu'un site d'appel avait omis ce contrôle).
    """
    webhook = await webhook_service.get_webhook(webhook_id)
    if not webhook or webhook.tree_id != tree_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    return webhook


def _to_response(w: Webhook) -> WebhookResponse:
    """Convert a webhook ORM object to API response (masks the secret)."""
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
    _=require_role("admin"),
):
    """List webhooks configured for a tree."""
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
    _=require_role("admin"),
):
    """Create a new webhook for a tree."""
    webhook = await webhook_service.create_webhook(tree_id, data)
    return _to_response(webhook)


@router.put("/tree/{tree_id}/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    tree_id: int,
    webhook_id: int,
    data: WebhookUpdate,
    webhook_service: WebhookServiceDep,
    _=require_role("admin"),
):
    """Update a webhook."""
    # Vérifie l'appartenance AVANT de muter (update_webhook committe)
    await _get_owned_webhook(webhook_service, tree_id, webhook_id)
    webhook = await webhook_service.update_webhook(webhook_id, data)
    if webhook is None:
        # TOCTOU (revue 2026-07-16 #7) : supprimé entre le contrôle et l'update
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
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
    _=require_role("admin"),
):
    """Delete a webhook."""
    await _get_owned_webhook(webhook_service, tree_id, webhook_id)
    await webhook_service.delete_webhook(webhook_id)


@router.post(
    "/tree/{tree_id}/webhooks/{webhook_id}/test",
    response_model=WebhookTestResult,
)
async def test_webhook(
    tree_id: int,
    webhook_id: int,
    webhook_service: WebhookServiceDep,
    _=require_role("admin"),
):
    """Send a test payload to the webhook."""
    await _get_owned_webhook(webhook_service, tree_id, webhook_id)
    return await webhook_service.test_webhook(webhook_id)


@router.get(
    "/tree/{tree_id}/webhooks/{webhook_id}/logs",
    response_model=list[WebhookLogResponse],
)
async def get_webhook_logs(
    tree_id: int,
    webhook_id: int,
    webhook_service: WebhookServiceDep,
    _=require_role("admin"),
    limit: int = Query(default=50, ge=1, le=1000),
):
    """Retrieve the send history of a webhook."""
    await _get_owned_webhook(webhook_service, tree_id, webhook_id)
    return await webhook_service.get_logs(webhook_id, limit)
