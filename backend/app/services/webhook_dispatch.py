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

# Limite le nombre de dispatches webhook concurrents pour éviter l'épuisement mémoire
_MAX_CONCURRENT_DISPATCHES = 20
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_DISPATCHES)


def schedule_webhook_dispatch(
    tree_id: int,
    event: str,
    payload: dict[str, Any],
) -> asyncio.Task[None]:
    """Planifie un dispatch webhook borné par un sémaphore (fire-and-forget).

    Remplace l'usage direct de asyncio.create_task(dispatch_webhooks(...)).
    Le sémaphore limite à _MAX_CONCURRENT_DISPATCHES tâches simultanées.
    """
    return asyncio.create_task(_bounded_dispatch(tree_id, event, payload))


async def _bounded_dispatch(
    tree_id: int,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Wrapper qui acquiert le sémaphore avant de dispatcher."""
    async with _semaphore:
        await dispatch_webhooks(tree_id, event, payload)


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
    """Envoie une requête HTTP à un webhook avec protection SSRF par IP pinning."""
    from urllib.parse import urlparse, urlunparse

    from app.url_validation import resolve_and_validate_url

    try:
        url, resolved_ips = resolve_and_validate_url(webhook.url)
    except ValueError as e:
        return {
            "success": False,
            "error_message": f"URL bloquée (SSRF): {e}",
        }

    body = json.dumps(payload, default=str, ensure_ascii=False)

    # Headers utilisateur d'abord, puis headers de sécurité (ne peuvent pas être surchargés)
    headers: dict[str, str] = {
        **webhook.headers,
        "Content-Type": "application/json",
        "X-TreeVuln-Event": event,
    }

    # Signature HMAC-SHA256 (déchiffre le secret stocké en BDD)
    if webhook.secret:
        from app.config import settings as _settings
        from app.crypto import decrypt_secret

        secret_plain = decrypt_secret(webhook.secret, _settings.admin_api_key) if _settings.admin_api_key else webhook.secret
        signature = hmac.new(
            secret_plain.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-TreeVuln-Signature"] = f"sha256={signature}"

    # IP pinning pour HTTP : connecte à l'IP résolue et validée (prévient le DNS rebinding)
    # HTTPS est protégé nativement : la vérification du certificat TLS empêche
    # la connexion à une IP privée rebindée (le cert ne matchera pas le hostname)
    parsed = urlparse(url)
    request_url = url
    if parsed.scheme == "http" and resolved_ips:
        port = parsed.port or 80
        request_url = urlunparse(parsed._replace(netloc=f"{resolved_ips[0]}:{port}"))
        headers["Host"] = parsed.hostname or ""

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.post(request_url, content=body, headers=headers)

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
