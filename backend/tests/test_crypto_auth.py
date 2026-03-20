"""
Tests unitaires pour crypto.py (chiffrement Fernet avec clé en cache module).
"""

import pytest

from app.crypto import decrypt_secret, encrypt_secret, set_encryption_key, _reset_key, _get_key


# --- Tests crypto.py ---


class TestEncryptDecrypt:
    """Tests du chiffrement/déchiffrement Fernet."""

    def setup_method(self):
        set_encryption_key("test-admin-key")

    def teardown_method(self):
        _reset_key()

    def test_round_trip(self):
        """Un secret chiffré puis déchiffré retourne le texte original."""
        secret = "my-webhook-secret-123"
        encrypted = encrypt_secret(secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == secret

    def test_encrypted_has_prefix(self):
        """Le secret chiffré commence par 'enc:'."""
        encrypted = encrypt_secret("test")
        assert encrypted.startswith("enc:")

    def test_different_keys_produce_different_ciphertexts(self):
        """Deux clés différentes produisent des chiffrés différents."""
        secret = "same-secret"
        set_encryption_key("key-1")
        enc1 = encrypt_secret(secret)
        set_encryption_key("key-2")
        enc2 = encrypt_secret(secret)
        assert enc1 != enc2

    def test_wrong_key_fails(self):
        """Le déchiffrement avec une mauvaise clé lève une erreur."""
        set_encryption_key("key-1")
        encrypted = encrypt_secret("secret")
        set_encryption_key("key-2")
        with pytest.raises(ValueError, match="clé invalide"):
            decrypt_secret(encrypted)

    def test_plaintext_retrocompatibility(self):
        """Un secret sans préfixe 'enc:' est retourné tel quel (rétrocompatibilité)."""
        plaintext = "old-plaintext-secret"
        result = decrypt_secret(plaintext)
        assert result == plaintext

    def test_empty_string_retrocompatibility(self):
        """Une chaîne vide est retournée telle quelle."""
        assert decrypt_secret("") == ""

    def test_encrypt_empty_string(self):
        """Une chaîne vide peut être chiffrée et déchiffrée."""
        encrypted = encrypt_secret("")
        assert decrypt_secret(encrypted) == ""

    def test_encrypt_unicode(self):
        """Les caractères unicode sont supportés."""
        secret = "clé-sécurisée-éàü-日本語"
        encrypted = encrypt_secret(secret)
        assert decrypt_secret(encrypted) == secret


class TestCryptoModuleCache:
    """Tests du cache module pour la clé de chiffrement."""

    def setup_method(self):
        _reset_key()

    def teardown_method(self):
        _reset_key()

    def test_set_and_get_key(self):
        set_encryption_key("test-key-value")
        assert _get_key() == "test-key-value"

    def test_encrypt_decrypt_with_cached_key(self):
        set_encryption_key("my-secret-key-for-testing")
        encrypted = encrypt_secret("hello")
        assert encrypted.startswith("enc:")
        assert decrypt_secret(encrypted) == "hello"

    def test_encrypt_without_key_raises(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            encrypt_secret("hello")
