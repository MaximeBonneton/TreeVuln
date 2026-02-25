"""
Validation d'URL pour la protection contre les SSRF.

Bloque les requêtes vers les réseaux privés, le loopback,
les adresses link-local, et les endpoints de métadonnées cloud.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Réseaux privés/internes à bloquer
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),         # This network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local (cloud metadata)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),       # IETF protocol assignments
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

# Hostnames connus pour les endpoints de métadonnées cloud
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
}


def _is_private_ip(ip_str: str) -> bool:
    """Vérifie si une adresse IP est dans un réseau bloqué."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    return any(addr in network for network in _BLOCKED_NETWORKS)


def resolve_and_validate_url(url: str) -> tuple[str, list[str]]:
    """
    Valide une URL de webhook contre les attaques SSRF et résout le DNS.

    Retourne l'URL et les IPs résolues pour permettre le pinning IP
    (prévention du DNS rebinding / TOCTOU).

    Raises:
        ValueError si l'URL est invalide ou pointe vers un réseau bloqué.

    Returns:
        Tuple (url_validée, liste_IPs_résolues).
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError("L'URL doit commencer par http:// ou https://")

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ValueError("L'URL doit contenir un hostname valide")

    # Vérifie les hostnames bloqués connus
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"L'URL pointe vers un endpoint de métadonnées interdit ({hostname})"
        )

    # Résout le DNS et vérifie les IPs
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Impossible de résoudre le hostname '{hostname}'")

    if not addr_infos:
        raise ValueError(f"Aucune adresse IP trouvée pour '{hostname}'")

    resolved_ips: list[str] = []
    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        if _is_private_ip(ip_str):
            raise ValueError(
                f"L'URL pointe vers un réseau privé/interne ({ip_str}). "
                f"Les webhooks ne peuvent cibler que des adresses publiques."
            )
        resolved_ips.append(ip_str)

    return url, resolved_ips


def validate_webhook_url(url: str) -> str:
    """
    Valide une URL de webhook (wrapper pour les validateurs de schéma Pydantic).

    Raises:
        ValueError si l'URL est invalide ou pointe vers un réseau bloqué.

    Returns:
        L'URL validée.
    """
    validated_url, _ = resolve_and_validate_url(url)
    return validated_url
