"""
URL validation for webhooks.

Validates URL syntax and blocks known cloud metadata endpoints.
No DNS resolution is performed — this tool is designed for on-premise
deployment where webhooks typically target internal networks.
"""

from urllib.parse import urlparse

# Known hostnames for cloud metadata endpoints
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
}


def validate_webhook_url(url: str) -> str:
    """
    Validate a webhook URL (syntax + metadata endpoint blocking).

    Raises:
        ValueError if the URL is invalid or targets a cloud metadata endpoint.

    Returns:
        The validated URL.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ValueError("URL must contain a valid hostname")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"URL points to a forbidden metadata endpoint ({hostname})"
        )

    return url
