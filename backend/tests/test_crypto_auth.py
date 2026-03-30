"""
Unit tests for crypto.py (Fernet encryption with module-level key cache).
"""

import pytest

from app.crypto import decrypt_secret, encrypt_secret, set_encryption_key, _reset_key, _get_key


# --- Tests crypto.py ---


class TestEncryptDecrypt:
    """Tests for Fernet encryption/decryption."""

    def setup_method(self):
        set_encryption_key("test-admin-key")

    def teardown_method(self):
        _reset_key()

    def test_round_trip(self):
        """An encrypted then decrypted secret returns the original text."""
        secret = "my-webhook-secret-123"
        encrypted = encrypt_secret(secret)
        decrypted = decrypt_secret(encrypted)
        assert decrypted == secret

    def test_encrypted_has_prefix(self):
        """The encrypted secret starts with 'enc:'."""
        encrypted = encrypt_secret("test")
        assert encrypted.startswith("enc:")

    def test_different_keys_produce_different_ciphertexts(self):
        """Two different keys produce different ciphertexts."""
        secret = "same-secret"
        set_encryption_key("key-1")
        enc1 = encrypt_secret(secret)
        set_encryption_key("key-2")
        enc2 = encrypt_secret(secret)
        assert enc1 != enc2

    def test_wrong_key_fails(self):
        """Decryption with a wrong key raises an error."""
        set_encryption_key("key-1")
        encrypted = encrypt_secret("secret")
        set_encryption_key("key-2")
        with pytest.raises(ValueError, match="invalid key"):
            decrypt_secret(encrypted)

    def test_plaintext_retrocompatibility(self):
        """A secret without the 'enc:' prefix is returned as-is (backward compatibility)."""
        plaintext = "old-plaintext-secret"
        result = decrypt_secret(plaintext)
        assert result == plaintext

    def test_empty_string_retrocompatibility(self):
        """An empty string is returned as-is."""
        assert decrypt_secret("") == ""

    def test_encrypt_empty_string(self):
        """An empty string can be encrypted and decrypted."""
        encrypted = encrypt_secret("")
        assert decrypt_secret(encrypted) == ""

    def test_encrypt_unicode(self):
        """Unicode characters are supported."""
        secret = "clé-sécurisée-éàü-日本語"
        encrypted = encrypt_secret(secret)
        assert decrypt_secret(encrypted) == secret


class TestCryptoModuleCache:
    """Tests for the module-level encryption key cache."""

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
