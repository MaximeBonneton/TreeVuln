"""
Utilitaires de chiffrement pour les secrets stockés en base de données.

Utilise Fernet (AES-128-CBC + HMAC-SHA256) avec une clé dérivée de ADMIN_API_KEY.
Les secrets chiffrés sont préfixés par "enc:" pour la rétrocompatibilité
avec les secrets en clair existants.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_PREFIX = "enc:"


def _derive_key(admin_key: str) -> bytes:
    """Dérive une clé Fernet à partir de la clé d'administration."""
    raw = hashlib.sha256(
        (admin_key + ":treevuln-secret-encryption").encode()
    ).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_secret(plaintext: str, admin_key: str) -> str:
    """Chiffre un secret pour le stockage en base de données.

    Returns:
        Le secret chiffré, préfixé par "enc:".
    """
    key = _derive_key(admin_key)
    f = Fernet(key)
    encrypted = f.encrypt(plaintext.encode()).decode()
    return f"{_PREFIX}{encrypted}"


def decrypt_secret(stored_value: str, admin_key: str) -> str:
    """Déchiffre un secret stocké en base de données.

    Gère la rétrocompatibilité : si le secret ne commence pas par "enc:",
    il est considéré comme un secret en clair (migration depuis l'ancienne version).

    Returns:
        Le secret en clair.
    """
    if not stored_value.startswith(_PREFIX):
        return stored_value

    key = _derive_key(admin_key)
    f = Fernet(key)
    try:
        return f.decrypt(stored_value[len(_PREFIX) :].encode()).decode()
    except InvalidToken:
        logger.error("Impossible de déchiffrer un secret (clé changée ?)")
        raise ValueError("Déchiffrement du secret impossible — la clé a peut-être changé")
