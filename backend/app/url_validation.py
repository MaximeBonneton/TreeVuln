"""
URL validation for SSRF protection.

Blocks requests to private networks, loopback,
link-local addresses, and cloud metadata endpoints.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Private/internal networks to block
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

# Known hostnames for cloud metadata endpoints
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
}


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is in a blocked network."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    return any(addr in network for network in _BLOCKED_NETWORKS)


def resolve_and_validate_url(url: str) -> tuple[str, list[str]]:
    """
    Validate a webhook URL against SSRF attacks and resolve DNS.

    Returns the URL and resolved IPs to allow IP pinning
    (prevention of DNS rebinding / TOCTOU).

    Raises:
        ValueError if the URL is invalid or points to a blocked network.

    Returns:
        Tuple (validated_url, resolved_IPs_list).
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ValueError("URL must contain a valid hostname")

    # Check known blocked hostnames
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"URL points to a forbidden metadata endpoint ({hostname})"
        )

    # Resolve DNS and verify IPs
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Unable to resolve hostname '{hostname}'")

    if not addr_infos:
        raise ValueError(f"No IP address found for '{hostname}'")

    resolved_ips: list[str] = []
    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        if _is_private_ip(ip_str):
            raise ValueError(
                f"URL points to a private/internal network ({ip_str}). "
                f"Webhooks can only target public addresses."
            )
        resolved_ips.append(ip_str)

    return url, resolved_ips


def validate_webhook_url(url: str) -> str:
    """
    Validate a webhook URL (wrapper for Pydantic schema validators).

    Raises:
        ValueError if the URL is invalid or points to a blocked network.

    Returns:
        The validated URL.
    """
    validated_url, _ = resolve_and_validate_url(url)
    return validated_url
