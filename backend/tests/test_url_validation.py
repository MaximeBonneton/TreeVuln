"""
Tests pour la validation SSRF des URLs de webhooks (S-12, Task 3.7).

Deux couches sont testées :
- validate_webhook_url : validation syntaxique/statique à la sauvegarde
  (schéma http(s), endpoints metadata, plages privées/réservées, formes
  d'IP obfusquées) ;
- validate_resolved_ip : résolution DNS au moment de l'ENVOI (protection
  contre le DNS rebinding), testée avec socket.getaddrinfo mocké.
"""

import socket

import pytest

from app.url_validation import validate_resolved_ip, validate_webhook_url


class TestValidateWebhookUrlBlocked:
    """URLs qui DOIVENT être rejetées à la sauvegarde."""

    @pytest.mark.parametrize(
        "url",
        [
            # Loopback / privées RFC1918
            "http://127.0.0.1/hook",
            "http://127.0.0.1:8000/hook",
            "http://10.0.0.5/hook",
            "http://172.16.3.4/hook",
            "http://192.168.1.1/hook",
            # Loopback / link-local IPv6
            "http://[::1]/hook",
            "http://[fe80::1]/hook",
            # IPv4-mapped IPv6
            "http://[::ffff:127.0.0.1]/hook",
            "http://[::ffff:10.0.0.1]/hook",
            # Metadata cloud
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "https://metadata.goog/x",
            # Link-local IPv4
            "http://169.254.1.1/hook",
        ],
    )
    def test_private_and_metadata_targets_rejected(self, url: str):
        with pytest.raises(ValueError):
            validate_webhook_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            # Forme décimale de 169.254.169.254 (10 chiffres)
            "http://2852039166/hook",
            # Forme décimale de 10.0.0.1 (9 chiffres : doit aussi être bloquée,
            # getaddrinfo l'interprète comme une IPv4 via inet_aton)
            "http://167772161/hook",
            # Forme hexadécimale de 169.254.169.254
            "http://0xA9FEA9FE/hook",
            # Octets octaux / hexadécimaux
            "http://0177.0.0.1/hook",
            "http://0x7f.0.0.1/hook",
        ],
    )
    def test_obfuscated_ip_representations_rejected(self, url: str):
        with pytest.raises(ValueError):
            validate_webhook_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/hook",
            "file:///etc/passwd",
            "gopher://example.com/",
            "example.com/hook",  # pas de schéma
        ],
    )
    def test_non_http_schemes_rejected(self, url: str):
        with pytest.raises(ValueError):
            validate_webhook_url(url)

    def test_url_without_hostname_rejected(self):
        with pytest.raises(ValueError):
            validate_webhook_url("http:///path-only")


class TestValidateWebhookUrlAllowed:
    """URLs publiques légitimes qui doivent passer."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://hooks.example.com/treevuln",
            "https://siem.internal-tools.example.org:8443/ingest",
            "http://ticketing.example.com/api/webhook",
            # IP publique littérale
            "https://8.8.8.8/hook",
        ],
    )
    def test_public_urls_accepted(self, url: str):
        assert validate_webhook_url(url) == url


class TestValidateResolvedIp:
    """
    Résolution DNS au moment de l'envoi (webhook_service._send_webhook et
    webhook_dispatch) : un hostname public qui résout vers une IP privée
    (DNS rebinding) doit être rejeté.
    """

    @staticmethod
    def _fake_getaddrinfo(ip: str):
        def _fake(hostname, port, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

        return _fake

    def test_hostname_resolving_to_private_ip_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(socket, "getaddrinfo", self._fake_getaddrinfo("10.0.0.5"))
        with pytest.raises(ValueError, match="private or reserved"):
            validate_resolved_ip("rebind.attacker.example")

    def test_hostname_resolving_to_loopback_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(socket, "getaddrinfo", self._fake_getaddrinfo("127.0.0.1"))
        with pytest.raises(ValueError, match="private or reserved"):
            validate_resolved_ip("localhost-alias.example")

    def test_hostname_resolving_to_metadata_ip_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            socket, "getaddrinfo", self._fake_getaddrinfo("169.254.169.254")
        )
        with pytest.raises(ValueError, match="private or reserved"):
            validate_resolved_ip("metadata-alias.example")

    def test_hostname_resolving_to_public_ip_accepted(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(socket, "getaddrinfo", self._fake_getaddrinfo("93.184.216.34"))
        validate_resolved_ip("hooks.example.com")  # ne doit pas lever

    def test_dns_failure_is_deferred_to_http_client(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def _fail(hostname, port, **kwargs):
            raise socket.gaierror("NXDOMAIN")

        monkeypatch.setattr(socket, "getaddrinfo", _fail)
        validate_resolved_ip("nxdomain.example")  # ne doit pas lever
