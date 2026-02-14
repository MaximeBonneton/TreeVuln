"""
Service pour la gestion des webhooks sortants.
Envoie des notifications HTTP POST avec signature HMAC-SHA256.
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

RETRY_DELAYS = [1, 5, 15]  # secondes


class WebhookService:
    """Service de gestion des webhooks sortants."""

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
        """Crée un nouveau webhook."""
        webhook = Webhook(
            tree_id=tree_id,
            name=data.name,
            url=data.url,
            secret=data.secret,
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
            webhook.secret = data.secret
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
        """Envoie un payload de test à un webhook."""
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

        result = await self._send_webhook(webhook, "test", test_payload)
        return result

    async def fire_webhooks(
        self,
        tree_id: int,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Déclenche tous les webhooks actifs d'un arbre pour un événement donné.

        Args:
            tree_id: ID de l'arbre
            event: Nom de l'événement (on_act, on_attend, etc.)
            payload: Données à envoyer
        """
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.tree_id == tree_id,
                Webhook.is_active == True,
            )
        )
        webhooks = result.scalars().all()

        for webhook in webhooks:
            if event in webhook.events or "*" in webhook.events:
                try:
                    await self._send_webhook_with_retry(webhook, event, payload)
                except Exception:
                    logger.exception(
                        "Erreur fatale webhook %s (%s)", webhook.name, webhook.url
                    )

    async def _send_webhook_with_retry(
        self,
        webhook: Webhook,
        event: str,
        payload: dict[str, Any],
    ) -> WebhookTestResult:
        """Envoie un webhook avec retry (1s, 5s, 15s)."""
        last_result = None
        for attempt, delay in enumerate(RETRY_DELAYS):
            result = await self._send_webhook(webhook, event, payload)

            # Log l'envoi
            log = WebhookLog(
                webhook_id=webhook.id,
                event=event,
                status_code=result.status_code,
                request_body=payload,
                response_body=result.response_body,
                success=result.success,
                error_message=result.error_message,
                duration_ms=result.duration_ms,
            )
            self.db.add(log)
            await self.db.commit()

            if result.success:
                return result

            last_result = result

            # Ne pas attendre après le dernier essai
            if attempt < len(RETRY_DELAYS) - 1:
                import asyncio
                await asyncio.sleep(delay)

        return last_result or WebhookTestResult(success=False, error_message="Tous les essais ont échoué")

    async def _send_webhook(
        self,
        webhook: Webhook,
        event: str,
        payload: dict[str, Any],
    ) -> WebhookTestResult:
        """Envoie une requête HTTP à un webhook."""
        body = json.dumps(payload, default=str, ensure_ascii=False)

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-TreeVuln-Event": event,
            **webhook.headers,
        }

        # Signature HMAC-SHA256 si un secret est configuré
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
                response = await client.post(
                    webhook.url,
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
