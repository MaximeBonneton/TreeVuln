"""
Tests unitaires pour crypto.py (chiffrement Fernet) et auth.py (sessions HMAC).
"""

import time

import pytest

from app.crypto import decrypt_secret, encrypt_secret


# --- Tests crypto.py ---


class TestEncryptDecrypt:
    """Tests du chiffrement/déchiffrement Fernet."""

    def test_round_trip(self):
        """Un secret chiffré puis déchiffré retourne le texte original."""
        secret = "my-webhook-secret-123"
        admin_key = "test-admin-key"
        encrypted = encrypt_secret(secret, admin_key)
        decrypted = decrypt_secret(encrypted, admin_key)
        assert decrypted == secret

    def test_encrypted_has_prefix(self):
        """Le secret chiffré commence par 'enc:'."""
        encrypted = encrypt_secret("test", "key")
        assert encrypted.startswith("enc:")

    def test_different_keys_produce_different_ciphertexts(self):
        """Deux clés différentes produisent des chiffrés différents."""
        secret = "same-secret"
        enc1 = encrypt_secret(secret, "key-1")
        enc2 = encrypt_secret(secret, "key-2")
        assert enc1 != enc2

    def test_wrong_key_fails(self):
        """Le déchiffrement avec une mauvaise clé lève une erreur."""
        encrypted = encrypt_secret("secret", "key-1")
        with pytest.raises(ValueError, match="clé a peut-être changé"):
            decrypt_secret(encrypted, "key-2")

    def test_plaintext_retrocompatibility(self):
        """Un secret sans préfixe 'enc:' est retourné tel quel (rétrocompatibilité)."""
        plaintext = "old-plaintext-secret"
        result = decrypt_secret(plaintext, "any-key")
        assert result == plaintext

    def test_empty_string_retrocompatibility(self):
        """Une chaîne vide est retournée telle quelle."""
        assert decrypt_secret("", "key") == ""

    def test_encrypt_empty_string(self):
        """Une chaîne vide peut être chiffrée et déchiffrée."""
        encrypted = encrypt_secret("", "key")
        assert decrypt_secret(encrypted, "key") == ""

    def test_encrypt_unicode(self):
        """Les caractères unicode sont supportés."""
        secret = "clé-sécurisée-éàü-日本語"
        encrypted = encrypt_secret(secret, "key")
        assert decrypt_secret(encrypted, "key") == secret


# --- Tests auth.py (sessions HMAC) ---


class TestSessionToken:
    """Tests de la création et validation de tokens de session."""

    def test_create_and_validate(self):
        """Un token créé est valide immédiatement."""
        from app.api.routes.auth import create_session_token, validate_session_token

        admin_key = "test-admin-key-32chars-minimum!!"
        token = create_session_token(admin_key)
        assert validate_session_token(token, admin_key) is True

    def test_wrong_key_invalid(self):
        """Un token validé avec une mauvaise clé est rejeté."""
        from app.api.routes.auth import create_session_token, validate_session_token

        token = create_session_token("key-1")
        assert validate_session_token(token, "key-2") is False

    def test_tampered_token_invalid(self):
        """Un token modifié est rejeté."""
        from app.api.routes.auth import create_session_token, validate_session_token

        token = create_session_token("key")
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        assert validate_session_token(tampered, "key") is False

    def test_malformed_token_invalid(self):
        """Un token mal formé est rejeté sans erreur."""
        from app.api.routes.auth import validate_session_token

        assert validate_session_token("", "key") is False
        assert validate_session_token("no-dot-here", "key") is False
        assert validate_session_token("abc.def.ghi", "key") is False

    def test_token_format(self):
        """Le token a le format 'payload_b64.signature'."""
        from app.api.routes.auth import create_session_token

        token = create_session_token("key")
        parts = token.split(".")
        assert len(parts) == 2
        assert len(parts[0]) > 0  # payload
        assert len(parts[1]) == 64  # SHA-256 hex = 64 chars

    def test_expired_token_invalid(self):
        """Un token expiré est rejeté."""
        from app.api.routes.auth import validate_session_token

        import base64
        import hashlib
        import hmac
        import json

        # Créer un token expiré manuellement
        admin_key = "key"
        payload = json.dumps({"iat": int(time.time()) - 100000, "exp": int(time.time()) - 1})
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
        signature = hmac.new(admin_key.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        expired_token = f"{payload_b64}.{signature}"

        assert validate_session_token(expired_token, admin_key) is False
