"""
Tests unitaires pour le fix C-10 (audit 2026-07-16) : colonne secret webhook
en Text plutôt que String(255).

Contexte : Webhook.secret était déclaré String(255). encrypt_secret() (voir
app/crypto.py) produit "enc:" + un token Fernet dont la longueur ≈
4 + 1.37×(57 + len(plaintext)). Un secret plaintext un peu long (ex: 200
caractères, ce qui reste sous la limite max_length=255 du schéma
WebhookCreate.secret) chiffre en ~431 caractères, ce qui dépassait 255 et
provoquait un StringDataRightTruncation -> 500 à la création du webhook.

Le fix passe la colonne en Text (pas de limite de longueur).

Note : comme pour C-5/C-8/C-9, aucune fixture DB réelle (Postgres) n'existe
encore dans ce projet. On ne peut donc pas déclencher réellement un
StringDataRightTruncation ici (il n'apparaît qu'au flush SQL). On vérifie
donc :
1. par introspection du mapping SQLAlchemy que la colonne est bien Text,
2. que encrypt_secret() d'un plaintext de 200 caractères dépasse bien 255
   caractères (démontre que le bug était réel et que le seuil String(255)
   était insuffisant),
3. que create_webhook() (session mockée) stocke et permettrait de relire
   intégralement un secret chiffré long, sans troncature applicative.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import Text

from app.crypto import decrypt_secret, encrypt_secret, set_encryption_key, _reset_key
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate
from app.services.webhook_service import WebhookService


class TestWebhookSecretColumnIsText:
    """Vérifie que la colonne secret est déclarée Text (pas de limite arbitraire)."""

    def test_secret_column_type_is_text(self):
        column = Webhook.__table__.columns["secret"]
        assert isinstance(column.type, Text), (
            "Webhook.secret doit être de type Text (pas String(255)) car la "
            "valeur stockée est le secret CHIFFRÉ, qui dépasse 255 caractères "
            "pour un plaintext un peu long - voir fix C-10."
        )

    def test_secret_column_has_no_length_limit(self):
        column = Webhook.__table__.columns["secret"]
        # Text n'a pas d'attribut `length` significatif (contrairement à String)
        assert getattr(column.type, "length", None) is None


class TestEncryptedSecretExceedsOldColumnLimit:
    """Démontre que le secret chiffré dépasse la limite de 255 caractères de
    l'ancienne colonne String(255), pour un plaintext pourtant valide côté
    schéma (max_length=255)."""

    def setup_method(self):
        set_encryption_key("test-admin-key")

    def teardown_method(self):
        _reset_key()

    def test_encrypted_200_char_secret_exceeds_255_chars(self):
        plaintext = "x" * 200
        encrypted = encrypt_secret(plaintext)

        assert len(encrypted) > 255, (
            "Le secret chiffré doit dépasser 255 caractères pour reproduire "
            "le bug C-10 (StringDataRightTruncation sur String(255))."
        )
        # Round-trip complet : rien n'est perdu
        assert decrypt_secret(encrypted) == plaintext


class TestCreateWebhookStoresLongEncryptedSecretIntact:
    """
    Vérifie que create_webhook() stocke le secret chiffré long sans le
    tronquer applicativement, et qu'il reste déchiffrable intégralement.

    Session DB mockée (pas de fixture Postgres réelle disponible) : on ne
    peut pas vérifier ici que Postgres accepterait effectivement d'écrire
    cette valeur (c'est le rôle de la colonne Text), mais on vérifie que la
    couche service ne tronque rien avant l'écriture.
    """

    def setup_method(self):
        set_encryption_key("test-admin-key")

    def teardown_method(self):
        _reset_key()

    async def test_long_secret_round_trips_through_create_webhook(self):
        service = WebhookService.__new__(WebhookService)
        service.db = AsyncMock()
        service.db.add = lambda obj: None
        service.db.commit = AsyncMock()
        service.db.refresh = AsyncMock()

        long_plaintext = "s" * 200
        data = WebhookCreate(
            name="Long secret webhook",
            url="https://example.com/webhook",
            secret=long_plaintext,
            events=["on_act"],
        )

        webhook = await service.create_webhook(tree_id=1, data=data)

        assert webhook.secret is not None
        assert len(webhook.secret) > 255
        assert decrypt_secret(webhook.secret) == long_plaintext
