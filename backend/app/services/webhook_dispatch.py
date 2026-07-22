"""
Standalone outgoing webhook dispatch.

Creates its own DB session to be independent from the HTTP request lifecycle.
Designed for use with asyncio.create_task() (fire-and-forget).
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

RETRY_DELAYS = [1, 5, 15]  # seconds between retries

# Limit the number of concurrent webhook dispatches to prevent memory exhaustion
_MAX_CONCURRENT_DISPATCHES = 20
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_DISPATCHES)

# CPython ne garde qu'une référence FAIBLE aux tasks créées par create_task.
# Sans référence forte conservée ailleurs, une task peut être garbage-collectée
# en plein vol (webhook perdu aléatoirement). On conserve donc une référence
# forte ici jusqu'à la fin de la task (retirée via le done_callback).
_background_tasks: set[asyncio.Task[None]] = set()


def _event_matches(event: str, subscribed: list[str]) -> bool:
    """Le wildcard n'inclut pas les événements enisa_* (opt-in explicite)."""
    if event in subscribed:
        return True
    return "*" in subscribed and not event.startswith("enisa_")


def schedule_webhook_dispatch(
    tree_id: int,
    event: str,
    payload: dict[str, Any],
) -> asyncio.Task[None]:
    """Schedule a webhook dispatch bounded by a semaphore (fire-and-forget).

    Replaces direct usage of asyncio.create_task(dispatch_webhooks(...)).
    The semaphore limits to _MAX_CONCURRENT_DISPATCHES simultaneous tasks.
    La task est référencée dans _background_tasks pour éviter qu'elle soit
    garbage-collectée avant la fin de son exécution.
    """
    task = asyncio.create_task(_bounded_dispatch(tree_id, event, payload))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _bounded_dispatch(
    tree_id: int,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Wrapper that acquires the semaphore before dispatching."""
    async with _semaphore:
        await dispatch_webhooks(tree_id, event, payload)


async def dispatch_webhooks(
    tree_id: int,
    event: str,
    payload: dict[str, Any],
) -> None:
    """
    Trigger all active webhooks for a tree for an event.

    Creates its own DB session (independent from the HTTP request).
    Never propagates errors.
    """
    try:
        # Short session for the read query
        async with async_session_maker() as db:
            result = await db.execute(
                select(Webhook).where(
                    Webhook.tree_id == tree_id,
                    Webhook.is_active == True,  # noqa: E712
                )
            )
            webhooks = list(result.scalars().all())

        # Parallel sending — each webhook has its own session for retries
        tasks = []
        for webhook in webhooks:
            if _event_matches(event, webhook.events):
                tasks.append(_send_with_retry(webhook, event, payload))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    except Exception:
        logger.exception(
            "Fatal error in dispatch_webhooks (tree_id=%s, event=%s)",
            tree_id,
            event,
        )


async def _send_with_retry(
    webhook: Webhook,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Send a webhook with retries and logging. Each call creates its own DB session."""
    for attempt, delay in enumerate(RETRY_DELAYS):
        result = await _send_single(webhook, event, payload)

        # Log the send in a dedicated session
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
            logger.exception("Error logging webhook %s", webhook.name)

        if result["success"]:
            return

        # Don't wait after the last attempt
        if attempt < len(RETRY_DELAYS) - 1:
            await asyncio.sleep(delay)


async def _send_single(
    webhook: Webhook,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Send an HTTP request to a webhook."""
    from urllib.parse import urlparse

    from app.url_validation import validate_resolved_ip

    # DNS rebinding protection: verify resolved IP at send time
    hostname = urlparse(webhook.url).hostname
    if hostname:
        try:
            validate_resolved_ip(hostname)
        except ValueError as e:
            return {
                "success": False,
                "error_message": f"SSRF blocked: {e}",
                "duration_ms": 0,
            }

    body = json.dumps(payload, default=str, ensure_ascii=False)

    # User headers first, then security headers (cannot be overridden)
    headers: dict[str, str] = {
        **webhook.headers,
        "Content-Type": "application/json",
        "X-TreeVuln-Event": event,
    }

    # HMAC-SHA256 signature (decrypt the secret stored in DB)
    if webhook.secret:
        from app.crypto import decrypt_secret

        secret_plain = decrypt_secret(webhook.secret)
        signature = hmac.new(
            secret_plain.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-TreeVuln-Signature"] = f"sha256={signature}"

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
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
