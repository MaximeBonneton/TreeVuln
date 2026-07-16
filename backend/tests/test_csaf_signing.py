"""Tests du service de signature OpenPGP des documents CSAF.

Une clé de test ed25519 est générée une fois par session dans un homedir
temporaire (rapide, pas d'entropie RSA à attendre).
"""
import hashlib
import tempfile
from pathlib import Path

import gnupg
import pytest

from app.services.csaf_signing import (
    SigningError,
    compute_hashes,
    get_key_fingerprint,
    sign_detached,
)

TEST_PASSPHRASE = "test-passphrase"


@pytest.fixture(scope="session")
def test_pgp_key() -> str:
    """Génère une clé privée ed25519 armored, protégée par TEST_PASSPHRASE."""
    with tempfile.TemporaryDirectory() as home:
        gpg = gnupg.GPG(gnupghome=home)
        key_input = gpg.gen_key_input(
            key_type="EDDSA",
            key_curve="ed25519",
            name_real="TreeVuln Test",
            name_email="test@treevuln.local",
            passphrase=TEST_PASSPHRASE,
        )
        key = gpg.gen_key(key_input)
        assert key.fingerprint, f"Échec de génération de la clé de test : {key.stderr}"
        armored = gpg.export_keys(
            key.fingerprint, secret=True, passphrase=TEST_PASSPHRASE
        )
        assert "PRIVATE KEY" in armored
        return armored


class TestFingerprint:
    def test_fingerprint_extraite(self, test_pgp_key):
        fp = get_key_fingerprint(test_pgp_key)
        assert len(fp) == 40  # empreinte v4 : 40 hex

    def test_cle_invalide_leve_signing_error(self):
        with pytest.raises(SigningError):
            get_key_fingerprint("pas une clé PGP")


class TestSignDetached:
    def test_signature_armored_et_verifiable(self, test_pgp_key):
        content = b'{"document": {"category": "csaf_vex"}}'
        signature = sign_detached(content, test_pgp_key, TEST_PASSPHRASE)
        assert signature.startswith("-----BEGIN PGP SIGNATURE-----")

        # Vérification aller-retour dans un homedir indépendant
        with tempfile.TemporaryDirectory() as home:
            gpg = gnupg.GPG(gnupghome=home)
            gpg.import_keys(test_pgp_key)
            sig_path = Path(home) / "doc.json.asc"
            sig_path.write_text(signature)
            verified = gpg.verify_data(str(sig_path), content)
            assert verified.valid

    def test_mauvaise_passphrase_leve_signing_error(self, test_pgp_key):
        with pytest.raises(SigningError):
            sign_detached(b"data", test_pgp_key, "wrong-passphrase")

    def test_cle_invalide_leve_signing_error(self):
        with pytest.raises(SigningError):
            sign_detached(b"data", "pas une clé", None)


class TestComputeHashes:
    def test_hashes_corrects(self):
        content = b"hello csaf"
        sha256, sha512 = compute_hashes(content)
        assert sha256 == hashlib.sha256(content).hexdigest()
        assert sha512 == hashlib.sha512(content).hexdigest()
