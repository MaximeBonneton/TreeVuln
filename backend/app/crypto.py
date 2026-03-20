"""Chiffrement Fernet pour les secrets en base de données.

La clé de chiffrement est chargée une seule fois au démarrage (lifespan)
et mise en cache dans une variable module. Les fonctions encrypt_secret()
et decrypt_secret() utilisent cette clé en interne.
"""
import hashlib
import base64

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:"
_encryption_key: str | None = None


def set_encryption_key(key: str) -> None:
    """Définit la clé de chiffrement en cache mémoire (appelé au startup)."""
    global _encryption_key
    _encryption_key = key


def _reset_key() -> None:
    """Reset la clé (pour les tests uniquement)."""
    global _encryption_key
    _encryption_key = None


def _get_key() -> str:
    if _encryption_key is None:
        raise RuntimeError("Encryption key not initialized. Call set_encryption_key() first.")
    return _encryption_key


def _derive_fernet_key(raw_key: str) -> bytes:
    """Dérive une clé Fernet (32 bytes base64) à partir d'une clé brute."""
    digest = hashlib.sha256((raw_key + ":treevuln-secret-encryption").encode()).digest()
    return base64.urlsafe_b64encode(digest)


def derive_key_from_admin_key(admin_key: str) -> str:
    """Dérive et retourne la clé Fernet à partir de l'ancienne ADMIN_API_KEY (migration)."""
    return _derive_fernet_key(admin_key).decode()


def encrypt_secret(plaintext: str) -> str:
    """Chiffre un secret avec la clé en cache. Retourne 'enc:...'."""
    key = _get_key()
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    encrypted = f.encrypt(plaintext.encode()).decode()
    return f"{_PREFIX}{encrypted}"


def decrypt_secret(stored_value: str) -> str:
    """Déchiffre un secret. Rétrocompatible avec les valeurs en clair."""
    if not stored_value.startswith(_PREFIX):
        return stored_value
    key = _get_key()
    fernet_key = _derive_fernet_key(key)
    f = Fernet(fernet_key)
    try:
        return f.decrypt(stored_value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        raise ValueError("Impossible de déchiffrer le secret (clé invalide ?)")
