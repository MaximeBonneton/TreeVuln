"""
Tests pour la protection anti-brute-force du login (S-14, Task 3.9).

Reprend les exigences de l'audit :
- clé de verrouillage combinée (ip, username) ;
- purge des entrées expirées (pas de fuite mémoire) ;
- consultation du verrou sans création d'entrée (l'ancien defaultdict
  créait une entrée pour CHAQUE username testé, même sans échec) ;
- borne dure du nombre d'entrées suivies.

L'état étant module-level, chaque test le remet à zéro (fixture autouse).
"""

import time

import pytest
from fastapi import HTTPException

from app.api.routes import auth as auth_routes


@pytest.fixture(autouse=True)
def _clean_tracker():
    auth_routes._login_failures.clear()
    yield
    auth_routes._login_failures.clear()


def _fail_n_times(ip: str, username: str, n: int) -> None:
    for _ in range(n):
        auth_routes._record_login_failure(ip, username)


class TestLockout:
    def test_locked_after_max_failures(self):
        _fail_n_times("203.0.113.1", "admin", auth_routes._MAX_FAILURES)
        with pytest.raises(HTTPException) as exc:
            auth_routes._check_login_rate("203.0.113.1", "admin")
        assert exc.value.status_code == 429

    def test_not_locked_below_threshold(self):
        _fail_n_times("203.0.113.1", "admin", auth_routes._MAX_FAILURES - 1)
        auth_routes._check_login_rate("203.0.113.1", "admin")  # ne doit pas lever

    def test_lockout_is_scoped_by_ip(self):
        """5 échecs depuis une IP ne verrouillent pas le même username
        depuis une autre IP (clé combinée ip+username)."""
        _fail_n_times("203.0.113.1", "admin", auth_routes._MAX_FAILURES)
        auth_routes._check_login_rate("203.0.113.99", "admin")  # ne doit pas lever

    def test_lockout_is_scoped_by_username(self):
        _fail_n_times("203.0.113.1", "admin", auth_routes._MAX_FAILURES)
        auth_routes._check_login_rate("203.0.113.1", "operator")  # ne doit pas lever

    def test_lockout_expires_and_entry_is_removed(self):
        _fail_n_times("203.0.113.1", "admin", auth_routes._MAX_FAILURES)
        # Simule l'expiration : vieillit artificiellement l'entrée
        key = ("203.0.113.1", "admin")
        count, _ = auth_routes._login_failures[key]
        auth_routes._login_failures[key] = (
            count,
            time.monotonic() - auth_routes._LOCKOUT_SECONDS - 1,
        )

        auth_routes._check_login_rate("203.0.113.1", "admin")  # ne doit pas lever
        assert key not in auth_routes._login_failures

    def test_successful_login_clears_failures(self):
        _fail_n_times("203.0.113.1", "admin", 3)
        auth_routes._clear_login_failures("203.0.113.1", "admin")
        assert ("203.0.113.1", "admin") not in auth_routes._login_failures


class TestMemoryBounds:
    def test_check_does_not_create_entries(self):
        """Consulter le verrou pour un couple inconnu ne doit PAS créer
        d'entrée (l'ancien defaultdict croissait à chaque username testé)."""
        for i in range(100):
            auth_routes._check_login_rate("203.0.113.1", f"user-{i}")
        assert len(auth_routes._login_failures) == 0

    def test_expired_entries_are_purged_on_record(self):
        """Les entrées expirées sont purgées au fil de l'eau : pas de
        croissance non bornée avec des usernames aléatoires."""
        # 50 entrées expirées
        for i in range(50):
            auth_routes._login_failures[("203.0.113.1", f"old-{i}")] = (
                1,
                time.monotonic() - auth_routes._LOCKOUT_SECONDS - 1,
            )

        auth_routes._record_login_failure("203.0.113.1", "fresh")

        assert ("203.0.113.1", "fresh") in auth_routes._login_failures
        assert len(auth_routes._login_failures) == 1

    def test_tracker_size_is_hard_bounded(self):
        """Même avec des clés toutes actives (non expirées), le tracker ne
        dépasse jamais la borne dure."""
        limit = auth_routes._MAX_TRACKED_KEYS
        for i in range(limit + 50):
            auth_routes._record_login_failure("203.0.113.1", f"user-{i}")
        assert len(auth_routes._login_failures) <= limit
