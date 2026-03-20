"""Tests unitaires pour le service utilisateur (hashing, validation)."""
import pytest
from app.services.user_service import hash_password, verify_password


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecurepassword")
        assert hashed != "mysecurepassword"
        assert verify_password("mysecurepassword", hashed)

    def test_wrong_password(self):
        hashed = hash_password("mysecurepassword")
        assert not verify_password("wrongpassword", hashed)

    def test_different_hashes(self):
        """bcrypt produit des hashes différents (salt aléatoire)."""
        h1 = hash_password("samepassword12")
        h2 = hash_password("samepassword12")
        assert h1 != h2

    def test_hash_format(self):
        """Le hash bcrypt commence par $2b$."""
        hashed = hash_password("testpassword12")
        assert hashed.startswith("$2b$")
