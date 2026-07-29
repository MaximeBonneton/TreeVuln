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


# Hashs générés par l'ancienne implémentation passlib (CryptContext bcrypt),
# figés ici pour garantir que les comptes existants restent utilisables
# après la migration vers bcrypt direct.
PASSLIB_HASH_SHORT = "$2b$12$5P1Oen3y3RTBgOla/cErwennvK6.Ft0CwvJVwQBSrSshfJd5kp7.6"  # "motdepasse-test"
PASSLIB_HASH_LONG = "$2b$12$3shY25Z8e7cbeVNFhqsDSOeggVno07D5yEoo8ui8iImCg60mVUO6S"  # "L" * 100


class TestPasslibMigration:
    def test_no_passlib_left(self):
        """Le module ne doit plus dépendre de passlib (projet abandonné)."""
        import app.services.user_service as us

        assert not hasattr(us, "pwd_context")
        import inspect

        source = inspect.getsource(us)
        assert "import passlib" not in source
        assert "from passlib" not in source

    def test_verify_legacy_passlib_hash(self):
        """Un hash produit par passlib doit encore être vérifiable."""
        assert verify_password("motdepasse-test", PASSLIB_HASH_SHORT)
        assert not verify_password("mauvais-mdp", PASSLIB_HASH_SHORT)

    def test_verify_legacy_long_password(self):
        """passlib tronquait silencieusement à 72 octets ; un mot de passe
        long existant doit rester vérifiable après migration."""
        assert verify_password("L" * 100, PASSLIB_HASH_LONG)

    def test_hash_long_password(self):
        """Le hachage d'un mot de passe > 72 octets ne doit pas lever
        d'erreur et doit rester vérifiable (comportement passlib conservé)."""
        hashed = hash_password("P" * 100)
        assert verify_password("P" * 100, hashed)

    def test_verify_invalid_hash_returns_false(self):
        """Un hash corrompu ou vide ne doit pas lever d'exception."""
        assert not verify_password("whatever", "")
        assert not verify_password("whatever", "not-a-bcrypt-hash")
