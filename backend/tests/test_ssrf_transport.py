import socket
from unittest.mock import patch

import httpx
import pytest

from app.core.url_validator import SSRFSafeTransport, is_ip_private_or_restricted


def test_is_ip_private_or_restricted() -> None:
    """Verify classification of loopback, private RFC 1918, and cloud metadata addresses."""
    assert is_ip_private_or_restricted("127.0.0.1") is True
    assert is_ip_private_or_restricted("127.0.0.2") is True
    assert is_ip_private_or_restricted("::1") is True
    assert is_ip_private_or_restricted("10.0.0.1") is True
    assert is_ip_private_or_restricted("192.168.1.1") is True
    assert is_ip_private_or_restricted("172.16.0.1") is True
    assert is_ip_private_or_restricted("169.254.169.254") is True  # Cloud metadata
    assert is_ip_private_or_restricted("0.0.0.0") is True

    # Valid public addresses
    assert is_ip_private_or_restricted("93.184.216.34") is False
    assert is_ip_private_or_restricted("8.8.8.8") is False
    assert is_ip_private_or_restricted("1.1.1.1") is False


def test_ssrf_transport_blocks_loopback_connection_time() -> None:
    """Verify SSRFSafeTransport blocks direct connection to loopback at connect_tcp time."""
    transport = SSRFSafeTransport()
    with httpx.Client(transport=transport, timeout=1.0) as client:
        with pytest.raises(httpx.ConnectError) as exc_info:
            client.get("http://127.0.0.1:8000/api/v1/health")
        assert "Blocked restricted IP" in str(exc_info.value) or "restricted" in str(exc_info.value)


def test_ssrf_transport_blocks_cloud_metadata_connection_time() -> None:
    """Verify SSRFSafeTransport blocks direct connection to AWS/GCP cloud metadata IP."""
    transport = SSRFSafeTransport()
    with httpx.Client(transport=transport, timeout=1.0) as client:
        with pytest.raises(httpx.ConnectError) as exc_info:
            client.get("http://169.254.169.254/latest/meta-data/")
        assert "Blocked restricted IP" in str(exc_info.value) or "restricted" in str(exc_info.value)


def test_ssrf_transport_blocks_dns_rebinding_at_connection_time() -> None:
    """Simulate DNS rebinding where hostname initial resolution was benign, but connection-time

    DNS lookup returns a loopback/private IP.
    """
    transport = SSRFSafeTransport()

    # Mock socket.getaddrinfo to return a loopback IP at connect_tcp time
    mock_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]

    with (
        patch("socket.getaddrinfo", return_value=mock_addrinfo),
        httpx.Client(transport=transport, timeout=1.0) as client,
    ):
        with pytest.raises(httpx.ConnectError) as exc_info:
            client.get("http://rebind.attacker.example.com/sensitive-data")
        assert "Blocked restricted IP" in str(exc_info.value)
