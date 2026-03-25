"""Fernet encryption for secrets stored in the database.

The encryption key is loaded once at startup (lifespan)
and cached in a module variable. The encrypt_secret()
and decrypt_secret() functions use this key internally.
"""
import hashlib
import base64

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:"
_encryption_key: str | None = None


def set_encryption_key(key: str) -> None:
    """Set the encryption key in memory cache (called at startup)."""
    global _encryption_key
    _encryption_key = key


def _reset_key() -> None:
    """Reset the key (for tests only)."""
    global _encryption_key
    _encryption_key = None


def _get_key() -> str:
    if _encryption_key is None:
        raise RuntimeError("Encryption key not initialized. Call set_encryption_key() first.")
    return _encryption_key


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a Fernet key (32 bytes base64) from a raw key."""
    digest = hashlib.sha256((raw_key + ":treevuln-secret-encryption").encode()).digest()
    return base64.urlsafe_b64encode(digest)


def derive_key_from_admin_key(admin_key: str) -> str:
    """Derive and return the Fernet key from the legacy ADMIN_API_KEY (migration)."""
    return _derive_fernet_key(admin_key).decode()


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret with the cached key. Returns 'enc:...'."""
    key = _get_key()
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    encrypted = f.encrypt(plaintext.encode()).decode()
    return f"{_PREFIX}{encrypted}"


def decrypt_secret(stored_value: str) -> str:
    """Decrypt a secret. Backward compatible with plaintext values."""
    if not stored_value.startswith(_PREFIX):
        return stored_value
    key = _get_key()
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    try:
        return f.decrypt(stored_value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        raise ValueError("Unable to decrypt secret (invalid key?)")
