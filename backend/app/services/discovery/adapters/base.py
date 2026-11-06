import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from app.core.url_validator import validate_safe_url

DEFAULT_USER_AGENT = "Nexora-JobDiscoveryBot/1.0 (+https://nexora.app; contact@nexora.app)"


@dataclass
class DiscoveredJob:
    """Normalized candidate job opportunity retrieved from an automated career source."""

    title: str
    job_url: str
    description: str
    external_source_id: Optional[str] = None
    application_url: Optional[str] = None
    employment_type: Optional[str] = None  # e.g., "full_time", "internship", "contract"
    seniority_level: Optional[str] = None  # e.g., "entry_level", "internship", "junior"
    work_arrangement: str = "unspecified"  # e.g., "remote", "hybrid", "onsite"
    location_text: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    country: Optional[str] = None
    remote_eligibility_regions: list[str] = field(default_factory=list)
    skills_tags: list[str] = field(default_factory=list)
    role_family: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    source_published_at: Optional[datetime] = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class BaseSourceAdapter(ABC):
    """Abstract base class for all automated job board and feed adapters."""

    adapter_name: str
    display_name: str

    def __init__(self, timeout: float = 10.0, max_redirects: int = 3) -> None:
        self.timeout = timeout
        self.max_redirects = max_redirects

    def safe_get(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute an outbound HTTP GET request with connection-time SSRF and redirect validation.

        Validates the host before requesting, prevents access to private/loopback/cloud metadata
        networks, and checks each redirect target explicitly.
        """
        req_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, application/xml, text/xml, */*",
        }
        if headers:
            req_headers.update(headers)

        current_url = validate_safe_url(url, field_name="Source URL")
        if not current_url:
            raise ValueError("Target source URL is empty or invalid")

        redirects_count = 0
        while redirects_count <= self.max_redirects:
            validated_url = validate_safe_url(current_url, field_name="Target URL")
            if not validated_url:
                raise ValueError("Redirect URL failed safety validation")

            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=False,
                verify=True,
            ) as client:
                try:
                    resp = client.get(
                        validated_url,
                        headers=req_headers,
                        params=params if redirects_count == 0 else None,
                    )
                except httpx.TimeoutException as exc:
                    raise TimeoutError(f"Connection timed out connecting to {url}: {exc}") from exc
                except httpx.RequestError as exc:
                    raise ConnectionError(f"HTTP request failed for {url}: {exc}") from exc

                # Check for redirects and validate destination URL before following
                if resp.is_redirect and "location" in resp.headers:
                    redirects_count += 1
                    if redirects_count > self.max_redirects:
                        raise ValueError(f"Exceeded maximum {self.max_redirects} redirects")
                    next_url = str(resp.headers["location"])
                    if not next_url.startswith(("http://", "https://")):
                        next_url = urljoin(validated_url, next_url)
                    current_url = next_url
                    continue

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "60")
                    raise PermissionError(
                        f"Source rate limited requests (HTTP 429). Retry after {retry_after}s."
                    )
                if resp.status_code in (401, 403):
                    raise PermissionError(
                        f"Access forbidden by source (HTTP {resp.status_code}). "
                        "Public feed may require authorization or be disabled."
                    )
                if resp.status_code == 404:
                    raise FileNotFoundError(
                        "Source endpoint not found (HTTP 404). Check board token or URL."
                    )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"Source returned HTTP error {resp.status_code}: {resp.text[:200]}"
                    )

                return resp

        raise ValueError("Exceeded maximum redirects")

    @abstractmethod
    def fetch_jobs(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
        **kwargs: Any,
    ) -> list[DiscoveredJob]:
        """Fetch and return normalized discovered jobs from the source."""
        pass

    @abstractmethod
    def test_connection(
        self,
        source_url: Optional[str] = None,
        board_token: Optional[str] = None,
    ) -> tuple[bool, str, int]:
        """Test source connectivity and return (is_success, message, detected_jobs_count)."""
        pass

    @staticmethod
    def clean_html(html_text: Optional[str]) -> str:
        """Strip dangerous HTML tags while preserving line breaks and basic readability."""
        if not html_text:
            return ""

        # Remove script and style elements
        cleaned = re.sub(
            r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>",
            "",
            html_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Convert <br>, <p>, <li> to newlines
        cleaned = re.sub(r"<\s*br\s*/?\s*>", "\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<\s*/p\s*>", "\n\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<\s*li\s*>", "\n• ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<\s*/h[1-6]\s*>", "\n\n", cleaned, flags=re.IGNORECASE)
        # Strip all other HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        # Unescape standard HTML entities
        cleaned = (
            cleaned.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
        )
        # Collapse excessive whitespace
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
        return cleaned.strip()
