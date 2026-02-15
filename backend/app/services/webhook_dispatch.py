"""
Dispatch standalone de webhooks sortants.

Crée sa propre session DB pour être indépendant du cycle de vie de la requête HTTP.
Conçu pour être utilisé avec asyncio.create_task() (fire-and-forget).
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from sqlalchemy import select

from app.database import async_session_maker
from app.models.webhook import Webhook, WebhookLog

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1, 5, 15]  # secondes entre les retries


async def dispatch_webhooks(
    tree_id: int,
    event: str,
    payload: dict[str, Any],
) -> None:
    """
    Déclenche tous les webhooks actifs d'un arbre pour un événement.

    Crée sa propre session DB (indépendante de la requête HTTP).
    Ne propage jamais d'erreur.
    """
    try:
        # Session courte pour la requête de lecture
        async with async_session_maker() as db:
            result = await db.execute(
                select(Webhook).where(
                    Webhook.tree_id == tree_id,
                    Webhook.is_active == True,  # noqa: E712
                )
            )
            webhooks = list(result.scalars().all())

        # Envoi parallèle — chaque webhook a sa propre session pour les retries
        tasks = []
        for webhook in webhooks:
            if event in webhook.events or "*" in webhook.events:
                tasks.append(_send_with_retry(webhook, event, payload))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    except Exception:
        logger.exception(
            "Erreur fatale dans dispatch_webhooks (tree_id=%s, event=%s)",
            tree_id,
            event,
        )


async def _send_with_retry(
    webhook: Webhook,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Envoie un webhook avec retries et logging. Chaque appel crée sa propre session DB."""
    for attempt, delay in enumerate(RETRY_DELAYS):
        result = await _send_single(webhook, event, payload)

        # Log l'envoi dans une session dédiée
        try:
            async with async_session_maker() as db:
                log = WebhookLog(
                    webhook_id=webhook.id,
                    event=event,
                    status_code=result.get("status_code"),
                    request_body=payload,
                    response_body=result.get("response_body"),
                    success=result["success"],
                    error_message=result.get("error_message"),
                    duration_ms=result.get("duration_ms"),
                )
                db.add(log)
                await db.commit()
        except Exception:
            logger.exception("Erreur log webhook %s", webhook.name)

        if result["success"]:
            return

        # Ne pas attendre après le dernier essai
        if attempt < len(RETRY_DELAYS) - 1:
            await asyncio.sleep(delay)


async def _send_single(
    webhook: Webhook,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Envoie une requête HTTP à un webhook."""
    body = json.dumps(payload, default=str, ensure_ascii=False)

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-TreeVuln-Event": event,
        **webhook.headers,
    }

    # Signature HMAC-SHA256
    if webhook.secret:
        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-TreeVuln-Signature"] = f"sha256={signature}"

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook.url, content=body, headers=headers)

        duration_ms = int((time.monotonic() - start) * 1000)
        success = 200 <= response.status_code < 300

        return {
            "success": success,
            "status_code": response.status_code,
            "response_body": response.text[:5000] if response.text else None,
            "duration_ms": duration_ms,
            "error_message": None if success else f"HTTP {response.status_code}",
        }
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "success": False,
            "error_message": str(e),
            "duration_ms": duration_ms,
        }
