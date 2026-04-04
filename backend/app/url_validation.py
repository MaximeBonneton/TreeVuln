"""
URL validation for webhooks.

Validates URL syntax and blocks known cloud metadata endpoints,
private/reserved IP ranges, and loopback addresses.
"""

import ipaddress
import re
from urllib.parse import urlparse

# Known hostnames for cloud metadata endpoints
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
}

# Private / reserved networks that must not be targeted by webhooks
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback IPv4
    ipaddress.ip_network("::1/128"),             # Loopback IPv6
    ipaddress.ip_network("10.0.0.0/8"),          # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),       # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),      # RFC1918
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local IPv4
    ipaddress.ip_network("fe80::/10"),           # Link-local IPv6
    ipaddress.ip_network("0.0.0.0/8"),           # "This" network
    ipaddress.ip_network("fc00::/7"),            # Unique local address (IPv6 private)
    ipaddress.ip_network("::ffff:0:0/96"),       # IPv4-mapped IPv6
]

# Detect numeric IP obfuscation: octal (0177), hex (0x7f), decimal (2130706433)
_OBFUSCATED_IP_RE = re.compile(
    r"^(0x[0-9a-fA-F]+|0[0-7]+|[0-9]{10,})$"
)


def _is_blocked_ip(hostname: str) -> bool:
    """Check if a hostname is an IP address in a blocked network."""
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return any(addr in network for network in _BLOCKED_NETWORKS)


def _is_obfuscated_ip(hostname: str) -> bool:
    """Detect obfuscated IP representations (hex, octal, large decimal)."""
    # Check the whole hostname (e.g. 0x7f000001)
    if _OBFUSCATED_IP_RE.match(hostname):
        return True
    # Check each octet (e.g. 0177.0.0.1)
    parts = hostname.split(".")
    if len(parts) in (1, 4):
        for part in parts:
            if part.startswith("0x") or (part.startswith("0") and len(part) > 1 and part.isdigit()):
                return True
    return False


def validate_webhook_url(url: str) -> str:
    """
    Validate a webhook URL (syntax + SSRF protection).

    Blocks:
    - Non HTTP(S) schemes
    - Cloud metadata endpoints
    - Private/reserved IP ranges (RFC1918, loopback, link-local)
    - IPv4-mapped IPv6 addresses
    - Obfuscated IP representations (hex, octal, large decimal)

    Raises:
        ValueError if the URL is invalid or targets a blocked destination.

    Returns:
        The validated URL.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ValueError("URL must contain a valid hostname")

    hostname_lower = hostname.lower()

    # Block known metadata endpoints
    if hostname_lower in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"URL points to a forbidden metadata endpoint ({hostname})"
        )

    # Block obfuscated IP representations
    if _is_obfuscated_ip(hostname_lower):
        raise ValueError(
            "URL contains an obfuscated IP address"
        )

    # Block private/reserved IP ranges
    if _is_blocked_ip(hostname):
        raise ValueError(
            "URL points to a private or reserved IP address"
        )

    return url
