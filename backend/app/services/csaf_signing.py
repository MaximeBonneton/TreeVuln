"""Signature OpenPGP détachée des documents CSAF (Phase 1 CRA).

La clé privée (armored, déchiffrée depuis app_settings par l'appelant)
est importée dans un homedir gnupg éphémère : un répertoire temporaire
créé pour l'opération et détruit immédiatement après. Aucune clé ne
persiste sur le disque du conteneur.
"""
import hashlib
import logging
import tempfile

import gnupg

logger = logging.getLogger(__name__)


class SigningError(Exception):
    """Erreur de signature ou de clé OpenPGP invalide."""


def get_key_fingerprint(armored_key: str) -> str:
    """Retourne l'empreinte (40 hex) d'une clé privée armored.

    Raises:
        SigningError: si la clé n'est pas importable.
    """
    with tempfile.TemporaryDirectory(prefix="treevuln-gpg-") as home:
        gpg = gnupg.GPG(gnupghome=home)
        result = gpg.import_keys(armored_key)
        if not result.fingerprints:
            raise SigningError("Clé OpenPGP invalide : import impossible")
        return result.fingerprints[0]


def sign_detached(content: bytes, armored_key: str, passphrase: str | None) -> str:
    """Signe `content` (signature détachée armored) avec la clé fournie.

    Raises:
        SigningError: clé invalide, passphrase incorrecte ou échec gpg.
    """
    with tempfile.TemporaryDirectory(prefix="treevuln-gpg-") as home:
        gpg = gnupg.GPG(gnupghome=home)
        result = gpg.import_keys(armored_key)
        if not result.fingerprints:
            raise SigningError("Clé OpenPGP invalide : import impossible")

        signed = gpg.sign(
            content,
            keyid=result.fingerprints[0],
            detach=True,
            passphrase=passphrase,
        )
        signature = str(signed)
        if not signature:
            # signed.stderr contient le détail gpg (mauvaise passphrase, etc.)
            logger.error("Échec de signature gpg : %s", signed.stderr)
            raise SigningError("Échec de la signature OpenPGP")
        return signature


def compute_hashes(content: bytes) -> tuple[str, str]:
    """Empreintes (sha256 hex, sha512 hex) du contenu."""
    return (
        hashlib.sha256(content).hexdigest(),
        hashlib.sha512(content).hexdigest(),
    )
