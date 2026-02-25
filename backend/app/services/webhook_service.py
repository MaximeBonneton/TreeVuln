"""
Service pour la gestion des webhooks sortants.
CRUD + test avec signature HMAC-SHA256.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook, WebhookLog
from app.schemas.webhook import WebhookCreate, WebhookTestResult, WebhookUpdate

logger = logging.getLogger(__name__)


class WebhookService:
    """Service de gestion des webhooks sortants (CRUD + test)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_webhooks(self, tree_id: int) -> list[Webhook]:
        """Liste les webhooks d'un arbre."""
        result = await self.db.execute(
            select(Webhook)
            .where(Webhook.tree_id == tree_id)
            .order_by(Webhook.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_webhook(self, webhook_id: int) -> Webhook | None:
        """Récupère un webhook par son ID."""
        result = await self.db.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        return result.scalar_one_or_none()

    async def create_webhook(self, tree_id: int, data: WebhookCreate) -> Webhook:
        """Crée un nouveau webhook (secret chiffré en BDD)."""
        from app.config import settings
        from app.crypto import encrypt_secret

        stored_secret = None
        if data.secret and settings.admin_api_key:
            stored_secret = encrypt_secret(data.secret, settings.admin_api_key)
        elif data.secret:
            stored_secret = data.secret

        webhook = Webhook(
            tree_id=tree_id,
            name=data.name,
            url=data.url,
            secret=stored_secret,
            headers=data.headers,
            events=data.events,
            is_active=data.is_active,
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def update_webhook(self, webhook_id: int, data: WebhookUpdate) -> Webhook | None:
        """Met à jour un webhook."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return None

        if data.name is not None:
            webhook.name = data.name
        if data.url is not None:
            webhook.url = data.url
        if data.secret is not None:
            # Chaîne vide = supprimer le secret
            if data.secret:
                from app.config import settings
                from app.crypto import encrypt_secret

                if settings.admin_api_key:
                    webhook.secret = encrypt_secret(data.secret, settings.admin_api_key)
                else:
                    webhook.secret = data.secret
            else:
                webhook.secret = None
        if data.headers is not None:
            webhook.headers = data.headers
        if data.events is not None:
            webhook.events = data.events
        if data.is_active is not None:
            webhook.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def delete_webhook(self, webhook_id: int) -> bool:
        """Supprime un webhook."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return False
        await self.db.delete(webhook)
        await self.db.commit()
        return True

    async def get_logs(self, webhook_id: int, limit: int = 50) -> list[WebhookLog]:
        """Récupère les logs d'envoi d'un webhook."""
        result = await self.db.execute(
            select(WebhookLog)
            .where(WebhookLog.webhook_id == webhook_id)
            .order_by(WebhookLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def test_webhook(self, webhook_id: int) -> WebhookTestResult:
        """Envoie un payload de test à un webhook et enregistre le résultat."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return WebhookTestResult(
                success=False,
                error_message="Webhook non trouvé",
            )

        test_payload = {
            "event": "test",
            "message": "Test webhook depuis TreeVuln",
            "webhook_name": webhook.name,
            "timestamp": time.time(),
        }

        result = await _send_webhook(webhook, "test", test_payload)

        # Enregistre le log du test
        log = WebhookLog(
            webhook_id=webhook.id,
            event="test",
            status_code=result.status_code,
            request_body=test_payload,
            response_body=result.response_body,
            success=result.success,
            error_message=result.error_message,
            duration_ms=result.duration_ms,
        )
        self.db.add(log)
        await self.db.commit()

        return result


async def _send_webhook(
    webhook: Webhook,
    event: str,
    payload: dict[str, Any],
) -> WebhookTestResult:
    """Envoie une requête HTTP à un webhook avec protection SSRF par IP pinning."""
    from urllib.parse import urlparse, urlunparse

    from app.url_validation import resolve_and_validate_url

    try:
        url, resolved_ips = resolve_and_validate_url(webhook.url)
    except ValueError as e:
        return WebhookTestResult(
            success=False,
            error_message=f"URL bloquée (SSRF): {e}",
        )

    body = json.dumps(payload, default=str, ensure_ascii=False)

    # Headers utilisateur d'abord, puis headers de sécurité (ne peuvent pas être surchargés)
    headers: dict[str, str] = {
        **webhook.headers,
        "Content-Type": "application/json",
        "X-TreeVuln-Event": event,
    }

    # Signature HMAC-SHA256 si un secret est configuré
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

    # IP pinning pour HTTP (prévient le DNS rebinding TOCTOU)
    parsed = urlparse(url)
    request_url = url
    if parsed.scheme == "http" and resolved_ips:
        port = parsed.port or 80
        request_url = urlunparse(parsed._replace(netloc=f"{resolved_ips[0]}:{port}"))
        headers["Host"] = parsed.hostname or ""

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.post(
                request_url,
                content=body,
                headers=headers,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        success = 200 <= response.status_code < 300
        response_text = response.text[:5000] if response.text else None

        return WebhookTestResult(
            success=success,
            status_code=response.status_code,
            response_body=response_text,
            duration_ms=duration_ms,
            error_message=None if success else f"HTTP {response.status_code}",
        )
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return WebhookTestResult(
            success=False,
            error_message=str(e),
            duration_ms=duration_ms,
        )
