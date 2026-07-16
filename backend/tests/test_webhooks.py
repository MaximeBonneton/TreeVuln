"""
Tests for outbound webhooks.
- Schema validation (URL, events)
- HMAC-SHA256 signature
- Payload construction
- Non-blocking dispatch (errors captured)
- Fire-and-forget task reference retention (C-6)
- Tree ownership verification before mutation (C-7)
"""

import asyncio
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookTestResult


# --- Schema validation tests ---


class TestWebhookSchemas:
    """Pydantic validation tests for webhooks."""

    def test_create_valid(self):
        data = WebhookCreate(
            name="Test",
            url="https://example.com/webhook",
            events=["on_act", "on_attend"],
        )
        assert data.name == "Test"
        assert data.url == "https://example.com/webhook"
        assert data.is_active is True
        assert data.secret is None
        assert data.headers == {}

    def test_create_with_all_fields(self):
        data = WebhookCreate(
            name="SIEM Alert",
            url="https://siem.corp.com/api/webhook",
            secret="my-secret-key",
            headers={"X-Custom-Token": "my-token-123"},
            events=["on_act"],
            is_active=False,
        )
        assert data.secret == "my-secret-key"
        assert data.headers == {"X-Custom-Token": "my-token-123"}
        assert data.is_active is False

    def test_create_invalid_url_no_protocol(self):
        with pytest.raises(ValueError, match="http:// or https://"):
            WebhookCreate(
                name="Test",
                url="example.com/webhook",
                events=["on_act"],
            )

    def test_create_invalid_url_ftp(self):
        with pytest.raises(ValueError, match="http:// or https://"):
            WebhookCreate(
                name="Test",
                url="ftp://example.com/webhook",
                events=["on_act"],
            )

    def test_create_http_url_allowed(self):
        data = WebhookCreate(
            name="Test",
            url="http://internal.corp.com/webhook",
            events=["on_act"],
        )
        assert data.url == "http://internal.corp.com/webhook"

    def test_create_invalid_event(self):
        with pytest.raises(ValueError, match="Invalid events"):
            WebhookCreate(
                name="Test",
                url="https://example.com",
                events=["on_act", "invalid_event"],
            )

    def test_create_empty_events(self):
        with pytest.raises(ValueError, match="At least one"):
            WebhookCreate(
                name="Test",
                url="https://example.com",
                events=[],
            )

    def test_create_wildcard_event(self):
        data = WebhookCreate(
            name="All events",
            url="https://example.com",
            events=["*"],
        )
        assert data.events == ["*"]

    def test_update_partial(self):
        data = WebhookUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.url is None
        assert data.events is None

    def test_update_invalid_url(self):
        with pytest.raises(ValueError, match="http:// or https://"):
            WebhookUpdate(url="not-a-url")

    def test_update_invalid_events(self):
        with pytest.raises(ValueError, match="Invalid events"):
            WebhookUpdate(events=["bad_event"])

    def test_update_valid_events(self):
        data = WebhookUpdate(events=["on_batch_complete"])
        assert data.events == ["on_batch_complete"]


# --- HMAC signature tests ---


class TestWebhookHMAC:
    """Tests for HMAC-SHA256 webhook signature."""

    def test_hmac_signature(self):
        """Verify that the HMAC signature is correct."""
        secret = "test-secret-key"
        payload = {"event": "on_act", "vuln_id": "CVE-2024-1234"}
        body = json.dumps(payload, default=str, ensure_ascii=False)

        expected = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        assert len(expected) == 64  # SHA-256 hex digest = 64 chars
        assert expected == hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def test_hmac_different_secrets(self):
        """Two different secrets produce different signatures."""
        body = b'{"test": true}'
        sig1 = hmac.new(b"secret1", body, hashlib.sha256).hexdigest()
        sig2 = hmac.new(b"secret2", body, hashlib.sha256).hexdigest()
        assert sig1 != sig2

    def test_hmac_different_bodies(self):
        """Two different payloads produce different signatures."""
        secret = b"same-secret"
        sig1 = hmac.new(secret, b'{"a": 1}', hashlib.sha256).hexdigest()
        sig2 = hmac.new(secret, b'{"a": 2}', hashlib.sha256).hexdigest()
        assert sig1 != sig2


# --- Dispatch tests ---


class TestWebhookDispatch:
    """Tests for the webhook_dispatch module."""

    @pytest.mark.asyncio
    async def test_dispatch_catches_errors(self):
        """Dispatch must never propagate errors."""
        from app.services.webhook_dispatch import dispatch_webhooks

        # Mock async_session_maker to raise an exception
        with patch("app.services.webhook_dispatch.async_session_maker") as mock_session:
            mock_session.side_effect = Exception("DB connection failed")
            # Must NOT raise an exception
            await dispatch_webhooks(tree_id=999, event="on_act", payload={"test": True})

    @pytest.mark.asyncio
    async def test_send_single_success(self):
        """Test sending a webhook with an OK response."""
        from app.services.webhook_dispatch import _send_single

        webhook = MagicMock()
        webhook.url = "https://example.com/hook"
        webhook.secret = None
        webhook.headers = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"ok": true}'

        with patch("app.services.webhook_dispatch.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await _send_single(webhook, "on_act", {"test": True})

        assert result["success"] is True
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_send_single_failure(self):
        """Test sending a webhook with a network error."""
        from app.services.webhook_dispatch import _send_single

        webhook = MagicMock()
        webhook.url = "https://unreachable.example.com/hook"
        webhook.secret = None
        webhook.headers = {}

        with patch("app.services.webhook_dispatch.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = Exception("Connection refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await _send_single(webhook, "on_act", {"test": True})

        assert result["success"] is False
        assert "Connection refused" in result["error_message"]

    @pytest.mark.asyncio
    async def test_send_single_with_hmac(self):
        """Verify that the HMAC header is added when a secret is configured."""
        from app.services.webhook_dispatch import _send_single

        webhook = MagicMock()
        webhook.url = "https://example.com/hook"
        webhook.secret = "my-secret"
        webhook.headers = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("app.services.webhook_dispatch.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            await _send_single(webhook, "on_act", {"data": "test"})

            # Verify that the signature header was sent
            call_kwargs = mock_instance.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert "X-TreeVuln-Signature" in headers
            assert headers["X-TreeVuln-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_send_single_without_secret(self):
        """Verify that the HMAC header is NOT added without a secret."""
        from app.services.webhook_dispatch import _send_single

        webhook = MagicMock()
        webhook.url = "https://example.com/hook"
        webhook.secret = None
        webhook.headers = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"

        with patch("app.services.webhook_dispatch.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            await _send_single(webhook, "on_act", {"data": "test"})

            call_kwargs = mock_instance.post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert "X-TreeVuln-Signature" not in headers


# --- WebhookTestResult tests ---


class TestWebhookTestResult:
    """Tests for the WebhookTestResult schema."""

    def test_success_result(self):
        result = WebhookTestResult(
            success=True,
            status_code=200,
            response_body='{"ok": true}',
            duration_ms=150,
        )
        assert result.success is True
        assert result.error_message is None

    def test_failure_result(self):
        result = WebhookTestResult(
            success=False,
            error_message="Connection timeout",
            duration_ms=30000,
        )
        assert result.success is False
        assert result.status_code is None


# --- C-6: background task reference retention ---


class TestScheduleWebhookDispatchTaskRetention:
    """schedule_webhook_dispatch() must keep a strong reference to the task
    until it completes, otherwise CPython's asyncio can garbage-collect it
    mid-flight (only a weak reference is held internally)."""

    @pytest.mark.asyncio
    async def test_task_is_retained_while_running_and_discarded_after(self):
        """The task must be present in _background_tasks while running,
        then removed once it completes (via the done callback)."""
        from app.services import webhook_dispatch

        release = asyncio.Event()

        async def fake_dispatch(tree_id, event, payload):
            # Bloque jusqu'à ce que le test autorise la fin de la task
            await release.wait()

        with patch.object(webhook_dispatch, "dispatch_webhooks", side_effect=fake_dispatch):
            task = webhook_dispatch.schedule_webhook_dispatch(
                1, "on_act", {"test": True}
            )

            # Laisse la task démarrer et acquérir le sémaphore
            await asyncio.sleep(0)
            assert task in webhook_dispatch._background_tasks

            release.set()
            await task

            assert task not in webhook_dispatch._background_tasks

    @pytest.mark.asyncio
    async def test_returns_the_created_task(self):
        """schedule_webhook_dispatch must still return the asyncio.Task."""
        from app.services import webhook_dispatch

        with patch.object(webhook_dispatch, "dispatch_webhooks", new=AsyncMock()):
            task = webhook_dispatch.schedule_webhook_dispatch(
                1, "on_act", {"test": True}
            )
            assert isinstance(task, asyncio.Task)
            await task


# --- C-7: tree ownership must be verified before mutation ---


class TestWebhookUpdateOwnership:
    """PUT /tree/{tree_id}/webhooks/{webhook_id} must verify that the webhook
    belongs to tree_id BEFORE calling update_webhook (which commits), just
    like delete_webhook and test_webhook already do."""

    @pytest.mark.asyncio
    async def test_update_wrong_tree_returns_404_without_persisting(self):
        from app.api.deps import get_webhook_service, require_auth
        from app.main import app

        # Le webhook existe mais appartient à l'arbre B (tree_id=2)
        webhook = MagicMock()
        webhook.id = 42
        webhook.tree_id = 2

        mock_service = AsyncMock()
        mock_service.get_webhook = AsyncMock(return_value=webhook)
        mock_service.update_webhook = AsyncMock()

        fake_user = MagicMock()
        fake_user.role = "admin"
        fake_user.must_change_pwd = False

        app.dependency_overrides[get_webhook_service] = lambda: mock_service
        app.dependency_overrides[require_auth] = lambda: fake_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                # Tentative de modification via l'arbre A (tree_id=1)
                response = await client.put(
                    "/api/v1/tree/1/webhooks/42",
                    json={"name": "Hacked"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404
        # update_webhook (qui COMMIT) ne doit jamais être appelé
        mock_service.update_webhook.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_returns_404_when_webhook_deleted_concurrently(self):
        """Revue 2026-07-16 #7 (TOCTOU) : le webhook passe le contrôle
        d'appartenance puis est supprimé (par un autre admin ou une cascade
        de suppression d'arbre) avant update_webhook, qui retourne None.
        La route doit répondre 404 — pas un 500 via _to_response(None)."""
        from app.api.deps import get_webhook_service, require_auth
        from app.main import app

        # Le contrôle d'appartenance passe (bon tree_id)...
        webhook = MagicMock()
        webhook.id = 42
        webhook.tree_id = 1

        mock_service = AsyncMock()
        mock_service.get_webhook = AsyncMock(return_value=webhook)
        # ... mais le webhook a disparu au moment de l'update
        mock_service.update_webhook = AsyncMock(return_value=None)

        fake_user = MagicMock()
        fake_user.role = "admin"
        fake_user.must_change_pwd = False

        app.dependency_overrides[get_webhook_service] = lambda: mock_service
        app.dependency_overrides[require_auth] = lambda: fake_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.put(
                    "/api/v1/tree/1/webhooks/42",
                    json={"name": "Renamed"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_correct_tree_succeeds(self):
        from app.api.deps import get_webhook_service, require_auth
        from app.main import app

        from datetime import datetime, timezone

        webhook = MagicMock()
        webhook.id = 42
        webhook.tree_id = 1
        webhook.name = "Updated"
        webhook.url = "https://example.com/hook"
        webhook.secret = None
        webhook.headers = {}
        webhook.events = ["on_act"]
        webhook.is_active = True
        webhook.created_at = datetime.now(timezone.utc)
        webhook.updated_at = datetime.now(timezone.utc)

        mock_service = AsyncMock()
        mock_service.get_webhook = AsyncMock(return_value=webhook)
        mock_service.update_webhook = AsyncMock(return_value=webhook)

        fake_user = MagicMock()
        fake_user.role = "admin"
        fake_user.must_change_pwd = False

        app.dependency_overrides[get_webhook_service] = lambda: mock_service
        app.dependency_overrides[require_auth] = lambda: fake_user

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/v1/tree/1/webhooks/42",
                    json={"name": "Updated"},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        mock_service.update_webhook.assert_awaited_once()
