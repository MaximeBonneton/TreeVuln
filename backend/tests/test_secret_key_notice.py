"""
Tests pour la signalisation de SECRET_KEY absente (S-18, Task 3.14).

Sans SECRET_KEY, la clé de chiffrement Fernet est stockée dans la table
encryption_keys — à côté des données qu'elle protège : un dump de la base
suffit à déchiffrer tous les secrets. Le démarrage n'est pas bloqué
(décision d154bfc : ne pas casser les déploiements d'évaluation), mais le
niveau de log doit refléter la gravité : WARNING en debug/dev, ERROR
explicite en production (DEBUG=false).
"""

import logging

import pytest

from app import main as main_module


class TestSecretKeyNotice:
    def test_error_logged_in_production(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(main_module.settings, "debug", False)
        with caplog.at_level(logging.WARNING, logger="app.main"):
            main_module._log_db_encryption_key_notice()

        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert errors, "En production (DEBUG=false), l'absence de SECRET_KEY doit être une ERREUR"
        assert "SECRET_KEY" in errors[0].message

    def test_warning_only_in_debug(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(main_module.settings, "debug", True)
        with caplog.at_level(logging.WARNING, logger="app.main"):
            main_module._log_db_encryption_key_notice()

        assert not [r for r in caplog.records if r.levelno == logging.ERROR]
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "En dev, un WARNING doit rester présent"
        assert "SECRET_KEY" in warnings[0].message
