"""Public research source adapters for Company Intelligence.

Uses SSRFSafeTransport for safe, outbound requests, respects timeouts,
and extracts clean text snippets with SHA-256 provenance hashing.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin

import httpx

from app.core.url_validator import SSRFSafeTransport, validate_safe_url

logger = logging.getLogger(__name__)


class SimpleHTMLTextExtractor(HTMLParser):
    """Cleanly extracts document title and body text from HTML without external dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._in_ignored_tag = False
        self._ignored_tags = {"script", "style", "noscript", "svg", "head"}
        self.title = ""
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in self._ignored_tags:
            self._in_ignored_tag = True
        elif tag_lower == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self._ignored_tags:
            self._in_ignored_tag = False
        elif tag_lower == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif not self._in_ignored_tag:
            cleaned = data.strip()
            if cleaned:
                self.text_chunks.append(cleaned)

    def get_clean_text(self) -> str:
        text = " ".join(self.text_chunks)
        # Collapse whitespace
        return re.sub(r"\s+", " ", text).strip()


@dataclass
class ResearchSourcePayload:
    """Normalized payload representing a scraped or parsed public company source."""

    source_type: (
        str  # "official_website", "careers_page", "engineering_blog", "news_release", "public_feed"
    )
    source_url: str
    title: str
    content_snippet: str
    raw_content: str
    content_hash: str
    retrieved_at: datetime
    published_at: Optional[datetime] = None
    is_verified: bool = True


def extract_content_hash(content: str) -> str:
    """Return SHA-256 digest of normalized text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class OfficialWebsiteAdapter:
    """Adapter for official company website pages (homepage, about, careers)."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self.timeout = timeout_seconds
        self.headers = {
            "User-Agent": (
                "NexoraBot/1.0 (+https://nexora.career/bot; legitimate public career research)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }

    def fetch_url(self, raw_url: str, source_type: str) -> Optional[ResearchSourcePayload]:
        """Safely fetch and parse a single company URL using SSRFSafeTransport."""
        if not raw_url:
            return None

        try:
            validated_url = validate_safe_url(raw_url, field_name="research_source_url")
            if not validated_url:
                return None
        except Exception as exc:
            logger.warning("Skipping invalid research URL %s: %s", raw_url, exc)
            return None

        try:
            transport = SSRFSafeTransport()
            with httpx.Client(
                transport=transport,
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.headers,
            ) as client:
                response = client.get(validated_url)
                if response.status_code >= 400:
                    logger.warning(
                        "Source %s returned HTTP %d", validated_url, response.status_code
                    )
                    return None

                content_type = response.headers.get("content-type", "").lower()
                body_text = ""
                title = ""

                if "text/html" in content_type or not content_type:
                    parser = SimpleHTMLTextExtractor()
                    parser.feed(response.text)
                    title = parser.title.strip() or f"Official Page ({validated_url})"
                    body_text = parser.get_clean_text()
                else:
                    title = f"Document ({validated_url})"
                    body_text = response.text[:10000].strip()

                if not body_text:
                    return None

                # Keep raw_content capped at reasonable length for DB
                capped_raw = body_text[:15000]
                snippet = body_text[:600]
                h = extract_content_hash(capped_raw)

                return ResearchSourcePayload(
                    source_type=source_type,
                    source_url=validated_url,
                    title=title[:250],
                    content_snippet=snippet,
                    raw_content=capped_raw,
                    content_hash=h,
                    retrieved_at=datetime.utcnow(),
                    is_verified=True,
                )
        except Exception as exc:
            logger.warning("Failed to fetch public research source %s: %s", validated_url, exc)
            return None

    def fetch_company_sources(
        self,
        website_url: Optional[str],
        careers_url: Optional[str],
        additional_urls: Optional[list[str]] = None,
    ) -> list[ResearchSourcePayload]:
        """Fetch primary public web sources for a company."""
        results: list[ResearchSourcePayload] = []
        seen_urls: set[str] = set()

        if website_url:
            payload = self.fetch_url(website_url, "official_website")
            if payload and payload.source_url not in seen_urls:
                seen_urls.add(payload.source_url)
                results.append(payload)

                # Attempt about page discovery if main website succeeded
                about_url = urljoin(payload.source_url, "/about")
                about_payload = self.fetch_url(about_url, "official_website")
                if about_payload and about_payload.source_url not in seen_urls:
                    seen_urls.add(about_payload.source_url)
                    results.append(about_payload)

        if careers_url and careers_url not in seen_urls:
            careers_payload = self.fetch_url(careers_url, "careers_page")
            if careers_payload and careers_payload.source_url not in seen_urls:
                seen_urls.add(careers_payload.source_url)
                results.append(careers_payload)

        if additional_urls:
            for extra_url in additional_urls:
                if extra_url and extra_url not in seen_urls:
                    stype = "engineering_blog" if "blog" in extra_url.lower() else "news_release"
                    payload = self.fetch_url(extra_url, stype)
                    if payload and payload.source_url not in seen_urls:
                        seen_urls.add(payload.source_url)
                        results.append(payload)

        return results
