import ipaddress
import re
import socket
from collections.abc import Iterable
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpcore
import httpx

from app.core.errors import BadRequestError

# Common legal and corporate entity suffixes to normalize for duplicate matching
_CORPORATE_SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|corp|corporation|llc|ltd|limited|pvt|private|co|company|"
    r"technologies|technology|tech|solutions|solution|services|service|systems|system|group)\b\.?",
    re.IGNORECASE,
)

_WHITESPACE_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")

_DISALLOWED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}


def normalize_company_name(name: str) -> str:
    """Normalize company name to lowercase alphanumeric baseline for duplicate matching.

    Example:
        'Acme Technologies, Inc.' -> 'acme'
        'Stripe, Inc.' -> 'stripe'
    """
    if not name:
        return ""

    lowered = name.lower()
    without_suffixes = _CORPORATE_SUFFIX_PATTERN.sub("", lowered)
    clean = _WHITESPACE_PUNCTUATION_PATTERN.sub(" ", without_suffixes)
    tokens = [t for t in clean.split() if t]
    return " ".join(tokens)


def extract_normalized_domain(url: Optional[str]) -> Optional[str]:
    """Extract normalized lowercase host domain from a URL (e.g., 'careers.stripe.com').

    Returns None if the URL is invalid or has no netloc.
    """
    if not url or not url.strip():
        return None

    trimmed = url.strip()
    if not trimmed.startswith(("http://", "https://")):
        trimmed = f"https://{trimmed}"

    try:
        parsed = urlparse(trimmed)
        hostname = parsed.hostname
        if not hostname:
            return None
        hostname = hostname.lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return None


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Return True if an IP is loopback, private, link-local, multicast, or cloud metadata."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or str(ip) == "169.254.169.254"
        )
    except ValueError:
        return False


def validate_safe_url(url: Optional[str], field_name: str = "URL") -> Optional[str]:
    """Validate that a URL uses http/https scheme and is not a private/internal host.

    Returns the stripped URL string, or None if input was empty.
    Raises BadRequestError on invalid schemes, malformed URLs, or SSRF-prohibited hosts.
    """
    if not url or not url.strip():
        return None

    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
    except Exception:
        raise BadRequestError(f"Invalid {field_name} format") from None

    if parsed.scheme.lower() not in {"http", "https"}:
        raise BadRequestError(f"{field_name} must use http or https protocol")

    hostname = parsed.hostname
    if not hostname:
        raise BadRequestError(f"{field_name} is missing a valid domain or host")

    hostname_lower = hostname.lower()

    if hostname_lower in _DISALLOWED_HOSTS or hostname_lower.endswith(
        (".localhost", ".local", ".internal")
    ):
        raise BadRequestError(f"{field_name} refers to a restricted internal host")

    # Check direct IP addresses
    if is_ip_private_or_restricted(hostname_lower):
        raise BadRequestError(f"{field_name} refers to a private or restricted network address")

    # Attempt DNS resolution check to prevent SSRF DNS rebinding to local addresses
    try:
        addr_info = socket.getaddrinfo(hostname_lower, None)
        for entry in addr_info:
            sockaddr = entry[4]
            resolved_ip = str(sockaddr[0])
            if is_ip_private_or_restricted(resolved_ip):
                raise BadRequestError(
                    f"{field_name} resolves to a private or restricted network address"
                )
    except socket.gaierror:
        # Unresolvable domains during creation are permitted for pre-registered records,
        # but the hostname format itself must be a valid domain label structure.
        if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", hostname_lower):
            raise BadRequestError(f"{field_name} contains an invalid hostname") from None

    return cleaned


class SSRFProtectedSyncBackend(httpcore.SyncBackend):
    """Enforces connection-time IP validation to eliminate DNS rebinding risks."""

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Optional[Iterable[Any]] = None,
    ) -> httpcore.NetworkStream:
        try:
            addr_info = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise httpcore.ConnectError(f"DNS resolution failed for {host}: {exc}") from exc

        verified_ip: Optional[str] = None
        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = str(sockaddr[0])
            if is_ip_private_or_restricted(ip_str):
                raise httpcore.ConnectError(
                    f"Blocked restricted IP {ip_str} (connection-time DNS rebinding protection)"
                )
            if not verified_ip:
                verified_ip = ip_str

        if not verified_ip:
            raise httpcore.ConnectError(f"No valid public IP addresses resolved for {host}")

        return super().connect_tcp(
            verified_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class SSRFSafeTransport(httpx.HTTPTransport):
    """Custom httpx transport enforcing connection-time destination validation and IP pinning."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pool = httpcore.ConnectionPool(
            network_backend=SSRFProtectedSyncBackend(),
            ssl_context=getattr(self._pool, "_ssl_context", None),
            max_connections=getattr(self._pool, "_max_connections", 10),
            max_keepalive_connections=getattr(self._pool, "_max_keepalive_connections", None),
            keepalive_expiry=getattr(self._pool, "_keepalive_expiry", None),
            http1=getattr(self._pool, "_http1", True),
            http2=getattr(self._pool, "_http2", False),
            retries=getattr(self._pool, "_retries", 0),
        )


def safe_check_url_status(
    url: str,
    timeout: float = 8.0,
    max_redirects: int = 3,
) -> tuple[bool, Optional[int], str]:
    """Safely check an external URL's availability with strict SSRF and connection guards.

    Validates URL host, prohibits local/private/cloud-metadata networks at each redirect hop,
    and queries HTTP status codes safely using SSRFSafeTransport with connection-time IP pinning.

    Returns:
        (is_reachable, status_code, message)
    """
    try:
        current_url = validate_safe_url(url, field_name="Target URL")
        if not current_url:
            return False, None, "URL is empty"
    except Exception as exc:
        return False, None, f"Security validation failed: {exc}"

    headers = {
        "User-Agent": "Nexora-JobFreshnessBot/1.0 (+https://nexora.app; contact@nexora.app)",
        "Accept": "*/*",
    }

    redirects_followed = 0
    while redirects_followed <= max_redirects:
        try:
            validated_target = validate_safe_url(current_url, field_name="Redirect URL")
            if not validated_target:
                return False, None, "Redirect URL is empty"

            with httpx.Client(
                transport=SSRFSafeTransport(),
                timeout=timeout,
                follow_redirects=False,
                verify=True,
            ) as client:
                try:
                    resp = client.head(validated_target, headers=headers)
                    if resp.status_code == 405:  # Method Not Allowed for HEAD
                        resp = client.get(validated_target, headers=headers)
                except httpx.RequestError as req_err:
                    return False, None, f"Network request error: {req_err}"

                # Handle HTTP redirects safely with target validation
                if resp.is_redirect and "location" in resp.headers:
                    redirects_followed += 1
                    if redirects_followed > max_redirects:
                        return False, resp.status_code, "Too many redirects"
                    next_url = str(resp.headers["location"])
                    if not next_url.startswith(("http://", "https://")):
                        next_url = urljoin(validated_target, next_url)
                    current_url = next_url
                    continue

                status_code = resp.status_code
                if 200 <= status_code < 400:
                    return True, status_code, f"URL active and reachable (HTTP {status_code})"
                elif status_code == 404:
                    return False, status_code, "Listing not found (HTTP 404)"
                elif status_code == 410:
                    return False, status_code, "Listing removed or expired (HTTP 410)"
                else:
                    return False, status_code, f"URL returned HTTP {status_code}"

        except Exception as exc:
            return False, None, f"Check failed: {exc}"

    return False, None, "Exceeded maximum redirects"
