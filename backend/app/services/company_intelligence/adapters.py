"""Public research source adapters for Company Intelligence.

Uses SSRFSafeTransport for safe outbound requests, enforces response size limits,
tracks original and final redirect URLs, parses HTML/RSS/JSON feeds safely,
and classifies domain provenance and verification integrity.
"""

import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from app.core.url_validator import (
    SSRFSafeTransport,
    extract_normalized_domain,
    validate_safe_url,
)

logger = logging.getLogger(__name__)

# Max response payload: 2MB to prevent decompression bombs and memory exhaustion
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 8.0

# Injection patterns to neutralize in untrusted web text
_PROMPT_INJECTION_PATTERN = re.compile(
    r"(?i)(?:\b(?:ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions)\b|"
    r"system\s*prompt\s*:|<system>|<\/system>|\bassistant\s*:|\bhuman\s*:)"
)


def sanitize_untrusted_content(text: str) -> str:
    """Neutralize potential prompt-injection directives from third-party web content."""
    if not text:
        return ""
    # Defuse direct instructions without losing research context
    sanitized = _PROMPT_INJECTION_PATTERN.sub(r"[filtered-directive]", text)
    return re.sub(r"\s+", " ", sanitized).strip()


class SimpleHTMLTextExtractor(HTMLParser):
    """Cleanly extracts document title and body text from HTML without external dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._in_ignored_tag = False
        self._ignored_tags = {"script", "style", "noscript", "svg", "head", "iframe"}
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
        clean = re.sub(r"\s+", " ", text).strip()
        return sanitize_untrusted_content(clean)


@dataclass
class FetchResult:
    """Raw result of an SSRF-safe HTTP request."""

    status_code: int
    source_url: str
    final_url: str
    content_bytes: bytes
    content_type: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ResearchSourcePayload:
    """Normalized payload representing a scraped or parsed public company source."""

    source_type: str  # official_website, careers_page, news_release,
    # engineering_blog, investor_relations, public_feed
    source_url: str
    final_url: str
    title: str
    content_snippet: str
    raw_content: str
    content_hash: str
    retrieved_at: datetime
    published_at: Optional[datetime] = None
    is_verified: bool = False
    metadata_json: dict[str, Any] = field(default_factory=dict)


def extract_content_hash(content: str) -> str:
    """Return SHA-256 digest of normalized text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_official_domain(url: str, expected_domain: Optional[str]) -> bool:
    """Check if the URL hostname matches the expected official company domain or subdomain."""
    if not url or not expected_domain:
        return False

    url_domain = extract_normalized_domain(url)
    if not url_domain:
        return False

    exp = expected_domain.lower().strip()
    act = url_domain.lower().strip()

    # Exact match or subdomain match (e.g. careers.stripe.com -> stripe.com)
    return act == exp or act.endswith(f".{exp}")


class SSRFSafeFetcher:
    """Hardened HTTP client enforcing SSRFSafeTransport, size caps, and redirect tracking."""

    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout_seconds
        self.headers = {
            "User-Agent": (
                "NexoraBot/1.0 (+https://nexora.career/bot; legitimate public career research)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8"
            ),
        }

    def fetch(self, raw_url: str) -> Optional[FetchResult]:
        """Fetch URL with connection-time IP validation and response size limits."""
        if not raw_url:
            return None

        try:
            validated_url = validate_safe_url(raw_url, field_name="research_source_url")
            if not validated_url:
                return None
        except Exception as exc:
            logger.warning("SSRF validation rejected URL %s: %s", raw_url, exc)
            return None

        try:
            transport = SSRFSafeTransport()
            with (
                httpx.Client(
                    transport=transport,
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=self.headers,
                ) as client,
                client.stream("GET", validated_url) as response,
            ):
                    if response.status_code >= 400:
                        logger.warning(
                            "Source %s returned HTTP %d", validated_url, response.status_code
                        )
                        return None

                    final_url_str = str(response.url)
                    # Re-validate final URL destination
                    try:
                        validate_safe_url(final_url_str, field_name="Redirect Destination")
                    except Exception as exc:
                        logger.warning(
                            "Blocked redirect to unsafe target %s: %s", final_url_str, exc
                        )
                        return None

                    chunks = []
                    total_bytes = 0
                    for chunk in response.iter_bytes(chunk_size=8192):
                        chunks.append(chunk)
                        total_bytes += len(chunk)
                        if total_bytes > MAX_RESPONSE_BYTES:
                            logger.warning(
                                "Response from %s exceeded size limit (%d bytes), truncating",
                                validated_url,
                                MAX_RESPONSE_BYTES,
                            )
                            break

                    content_type = response.headers.get("content-type", "").lower()
                    return FetchResult(
                        status_code=response.status_code,
                        source_url=validated_url,
                        final_url=final_url_str,
                        content_bytes=b"".join(chunks),
                        content_type=content_type,
                        headers=dict(response.headers),
                    )

        except Exception as exc:
            logger.warning("Failed to fetch public research source %s: %s", validated_url, exc)
            return None


# ============================================================================
# Modular Adapters for Each Source Category
# ============================================================================


class OfficialWebsiteAdapter:
    """Adapter for official company website pages (homepage, about, company)."""

    def __init__(self, fetcher: Optional[SSRFSafeFetcher] = None) -> None:
        self.fetcher = fetcher or SSRFSafeFetcher()

    def fetch_page(
        self,
        url: str,
        source_type: str = "official_website",
        expected_domain: Optional[str] = None,
        company_is_verified: bool = False,
    ) -> Optional[ResearchSourcePayload]:
        res = self.fetcher.fetch(url)
        if not res or not res.content_bytes:
            return None

        parser = SimpleHTMLTextExtractor()
        try:
            decoded = res.content_bytes.decode("utf-8", errors="replace")
            parser.feed(decoded)
        except Exception as exc:
            logger.warning("Failed to parse HTML for %s: %s", url, exc)
            return None

        body_text = parser.get_clean_text()
        if not body_text:
            return None

        title = parser.title.strip() or f"Official Page ({res.final_url})"
        capped_raw = body_text[:15000]
        snippet = body_text[:600]
        h = extract_content_hash(capped_raw)

        # Verification logic: Domain must match company domain and company must be verified
        is_official = is_official_domain(res.final_url, expected_domain)
        is_verified = bool(is_official and company_is_verified)

        return ResearchSourcePayload(
            source_type=source_type,
            source_url=res.source_url,
            final_url=res.final_url,
            title=title[:250],
            content_snippet=snippet,
            raw_content=capped_raw,
            content_hash=h,
            retrieved_at=datetime.utcnow(),
            is_verified=is_verified,
            metadata_json={
                "domain_match": is_official,
                "redirected": (res.source_url != res.final_url),
                "verification_reason": (
                    "Official company domain and verified entity"
                    if is_verified
                    else "Third-party domain or unverified entity"
                ),
            },
        )


class CompanyNewsroomAdapter:
    """Adapter for company newsrooms, press releases, and media announcements."""

    def __init__(self, fetcher: Optional[SSRFSafeFetcher] = None) -> None:
        self.fetcher = fetcher or SSRFSafeFetcher()

    def fetch_newsroom(
        self,
        url: str,
        expected_domain: Optional[str] = None,
        company_is_verified: bool = False,
    ) -> Optional[ResearchSourcePayload]:
        res = self.fetcher.fetch(url)
        if not res or not res.content_bytes:
            return None

        parser = SimpleHTMLTextExtractor()
        try:
            parser.feed(res.content_bytes.decode("utf-8", errors="replace"))
        except Exception:
            return None

        body_text = parser.get_clean_text()
        if not body_text:
            return None

        title = parser.title.strip() or f"Company Newsroom ({res.final_url})"
        capped_raw = body_text[:15000]
        snippet = body_text[:600]
        h = extract_content_hash(capped_raw)

        is_official = is_official_domain(res.final_url, expected_domain)
        is_verified = bool(is_official and company_is_verified)

        return ResearchSourcePayload(
            source_type="news_release",
            source_url=res.source_url,
            final_url=res.final_url,
            title=title[:250],
            content_snippet=snippet,
            raw_content=capped_raw,
            content_hash=h,
            retrieved_at=datetime.utcnow(),
            is_verified=is_verified,
            metadata_json={
                "category": "news_and_press",
                "domain_match": is_official,
                "verification_reason": "Verified official newsroom"
                if is_verified
                else "Third-party media source",
            },
        )


class EngineeringBlogAdapter:
    """Adapter for official engineering blogs and public technical documentation."""

    def __init__(self, fetcher: Optional[SSRFSafeFetcher] = None) -> None:
        self.fetcher = fetcher or SSRFSafeFetcher()

    def fetch_engineering_blog(
        self,
        url: str,
        expected_domain: Optional[str] = None,
        company_is_verified: bool = False,
    ) -> Optional[ResearchSourcePayload]:
        res = self.fetcher.fetch(url)
        if not res or not res.content_bytes:
            return None

        parser = SimpleHTMLTextExtractor()
        try:
            parser.feed(res.content_bytes.decode("utf-8", errors="replace"))
        except Exception:
            return None

        body_text = parser.get_clean_text()
        if not body_text:
            return None

        title = parser.title.strip() or f"Engineering Blog ({res.final_url})"
        capped_raw = body_text[:15000]
        snippet = body_text[:600]
        h = extract_content_hash(capped_raw)

        is_official = is_official_domain(res.final_url, expected_domain)
        is_verified = bool(is_official and company_is_verified)

        return ResearchSourcePayload(
            source_type="engineering_blog",
            source_url=res.source_url,
            final_url=res.final_url,
            title=title[:250],
            content_snippet=snippet,
            raw_content=capped_raw,
            content_hash=h,
            retrieved_at=datetime.utcnow(),
            is_verified=is_verified,
            metadata_json={
                "category": "engineering_publications",
                "domain_match": is_official,
                "verification_reason": "Official engineering publication"
                if is_verified
                else "External tech publication",
            },
        )


class InvestorRelationsAdapter:
    """Adapter for investor relations pages and public regulatory disclosures."""

    def __init__(self, fetcher: Optional[SSRFSafeFetcher] = None) -> None:
        self.fetcher = fetcher or SSRFSafeFetcher()

    def fetch_investor_relations(
        self,
        url: str,
        expected_domain: Optional[str] = None,
        company_is_verified: bool = False,
    ) -> Optional[ResearchSourcePayload]:
        res = self.fetcher.fetch(url)
        if not res or not res.content_bytes:
            return None

        parser = SimpleHTMLTextExtractor()
        try:
            parser.feed(res.content_bytes.decode("utf-8", errors="replace"))
        except Exception:
            return None

        body_text = parser.get_clean_text()
        if not body_text:
            return None

        title = parser.title.strip() or f"Investor Relations ({res.final_url})"
        capped_raw = body_text[:15000]
        snippet = body_text[:600]
        h = extract_content_hash(capped_raw)

        is_official = is_official_domain(res.final_url, expected_domain)
        is_verified = bool(is_official and company_is_verified)

        return ResearchSourcePayload(
            source_type="investor_relations",
            source_url=res.source_url,
            final_url=res.final_url,
            title=title[:250],
            content_snippet=snippet,
            raw_content=capped_raw,
            content_hash=h,
            retrieved_at=datetime.utcnow(),
            is_verified=is_verified,
            metadata_json={
                "category": "investor_disclosures",
                "domain_match": is_official,
                "verification_reason": "Official corporate IR page"
                if is_verified
                else "Third-party financial report",
            },
        )


class RSSFeedAdapter:
    """Adapter for permitted public RSS 2.0 and Atom feeds with entity expansion defenses."""

    def __init__(self, fetcher: Optional[SSRFSafeFetcher] = None) -> None:
        self.fetcher = fetcher or SSRFSafeFetcher()

    def fetch_feed(
        self,
        url: str,
        expected_domain: Optional[str] = None,
        company_is_verified: bool = False,
    ) -> list[ResearchSourcePayload]:
        res = self.fetcher.fetch(url)
        if not res or not res.content_bytes:
            return []

        raw_xml = res.content_bytes.decode("utf-8", errors="replace")

        # Disallow XML External Entity (XXE) and DTD injection
        if "<!ENTITY" in raw_xml.upper() or "<!DOCTYPE" in raw_xml.upper():
            logger.warning("Rejected feed %s: contains prohibited XML DTD/entity declarations", url)
            return []

        try:
            root = ET.fromstring(raw_xml)
        except Exception as exc:
            logger.warning("XML parsing failed for feed %s: %s", url, exc)
            return []

        is_official = is_official_domain(res.final_url, expected_domain)
        is_verified = bool(is_official and company_is_verified)

        items_payloads: list[ResearchSourcePayload] = []

        # RSS 2.0 (<rss><channel><item>)
        channel = root.find("channel")
        if channel is not None:
            feed_title = (channel.findtext("title") or "RSS Feed").strip()
            items = channel.findall("item")[:5]
            for item in items:
                it_title = (item.findtext("title") or feed_title).strip()
                it_desc = sanitize_untrusted_content(item.findtext("description") or "")
                it_link = (item.findtext("link") or res.final_url).strip()
                if not it_desc:
                    continue

                snippet = it_desc[:600]
                capped = it_desc[:15000]
                h = extract_content_hash(f"{it_title}:{capped}")

                items_payloads.append(
                    ResearchSourcePayload(
                        source_type="public_feed",
                        source_url=url,
                        final_url=it_link,
                        title=f"{feed_title}: {it_title}"[:250],
                        content_snippet=snippet,
                        raw_content=capped,
                        content_hash=h,
                        retrieved_at=datetime.utcnow(),
                        is_verified=is_verified,
                        metadata_json={
                            "feed_format": "rss_2.0",
                            "domain_match": is_official,
                        },
                    )
                )

        # Atom 1.0 (<feed xmlns="..."><entry>)
        tag_lower = root.tag.lower()
        if "feed" in tag_lower:
            feed_title = (
                root.findtext("{*}title") or root.findtext("title") or "Atom Feed"
            ).strip()
            entries = (root.findall("{*}entry") or root.findall("entry"))[:5]
            for entry in entries:
                et_title = (
                    entry.findtext("{*}title") or entry.findtext("title") or feed_title
                ).strip()
                summary = (
                    entry.findtext("{*}summary")
                    or entry.findtext("summary")
                    or entry.findtext("{*}content")
                    or entry.findtext("content")
                    or ""
                )
                clean_summary = sanitize_untrusted_content(summary)
                if not clean_summary:
                    continue

                link_elem = entry.find("{*}link") or entry.find("link")
                entry_url = res.final_url
                if link_elem is not None:
                    entry_url = link_elem.get("href") or res.final_url

                snippet = clean_summary[:600]
                capped = clean_summary[:15000]
                h = extract_content_hash(f"{et_title}:{capped}")

                items_payloads.append(
                    ResearchSourcePayload(
                        source_type="public_feed",
                        source_url=url,
                        final_url=entry_url,
                        title=f"{feed_title}: {et_title}"[:250],
                        content_snippet=snippet,
                        raw_content=capped,
                        content_hash=h,
                        retrieved_at=datetime.utcnow(),
                        is_verified=is_verified,
                        metadata_json={
                            "feed_format": "atom_1.0",
                            "domain_match": is_official,
                        },
                    )
                )

        return items_payloads


class JSONFeedAdapter:
    """Adapter for permitted public JSON feeds conforming to JSON Feed specification."""

    def __init__(self, fetcher: Optional[SSRFSafeFetcher] = None) -> None:
        self.fetcher = fetcher or SSRFSafeFetcher()

    def fetch_feed(
        self,
        url: str,
        expected_domain: Optional[str] = None,
        company_is_verified: bool = False,
    ) -> list[ResearchSourcePayload]:
        res = self.fetcher.fetch(url)
        if not res or not res.content_bytes:
            return []

        try:
            data = json.loads(res.content_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:
            logger.warning("JSON parsing failed for feed %s: %s", url, exc)
            return []

        if not isinstance(data, dict):
            return []

        feed_title = data.get("title", "JSON Feed")
        items = data.get("items", [])
        if not isinstance(items, list):
            return []

        is_official = is_official_domain(res.final_url, expected_domain)
        is_verified = bool(is_official and company_is_verified)

        payloads: list[ResearchSourcePayload] = []
        for it in items[:5]:
            if not isinstance(it, dict):
                continue

            it_title = it.get("title", feed_title)
            content = it.get("content_text") or it.get("summary") or it.get("content_html") or ""
            clean_content = sanitize_untrusted_content(content)
            if not clean_content:
                continue

            item_url = it.get("url") or res.final_url
            snippet = clean_content[:600]
            capped = clean_content[:15000]
            h = extract_content_hash(f"{it_title}:{capped}")

            payloads.append(
                ResearchSourcePayload(
                    source_type="public_feed",
                    source_url=url,
                    final_url=item_url,
                    title=f"{feed_title}: {it_title}"[:250],
                    content_snippet=snippet,
                    raw_content=capped,
                    content_hash=h,
                    retrieved_at=datetime.utcnow(),
                    is_verified=is_verified,
                    metadata_json={
                        "feed_format": "json_feed",
                        "domain_match": is_official,
                    },
                )
            )

        return payloads


# ============================================================================
# Company Research Coordinator
# ============================================================================


class CompanyResearchCoordinator:
    """Orchestrates multi-source public company research across all 6 supported categories."""

    def __init__(self) -> None:
        self.fetcher = SSRFSafeFetcher()
        self.website_adapter = OfficialWebsiteAdapter(self.fetcher)
        self.newsroom_adapter = CompanyNewsroomAdapter(self.fetcher)
        self.blog_adapter = EngineeringBlogAdapter(self.fetcher)
        self.ir_adapter = InvestorRelationsAdapter(self.fetcher)
        self.rss_adapter = RSSFeedAdapter(self.fetcher)
        self.json_adapter = JSONFeedAdapter(self.fetcher)

    def fetch_all_sources(
        self,
        website_url: Optional[str],
        careers_url: Optional[str],
        expected_domain: Optional[str],
        company_is_verified: bool,
        configured_sources: Optional[list[dict[str, str]]] = None,
    ) -> list[ResearchSourcePayload]:
        """Discover and fetch public research evidence across all 6 categories."""
        results: list[ResearchSourcePayload] = []
        seen_hashes: set[str] = set()

        def add_payload(p: Optional[ResearchSourcePayload]) -> None:
            if p and p.content_hash not in seen_hashes:
                seen_hashes.add(p.content_hash)
                results.append(p)

        def add_payloads(plist: list[ResearchSourcePayload]) -> None:
            for p in plist:
                add_payload(p)

        # 1. Official Website (Homepage & About)
        if website_url:
            p_home = self.website_adapter.fetch_page(
                website_url,
                source_type="official_website",
                expected_domain=expected_domain,
                company_is_verified=company_is_verified,
            )
            add_payload(p_home)

            # Discover /about
            about_url = urljoin(website_url, "/about")
            p_about = self.website_adapter.fetch_page(
                about_url,
                source_type="official_website",
                expected_domain=expected_domain,
                company_is_verified=company_is_verified,
            )
            add_payload(p_about)

        # 2. Careers Page
        if careers_url:
            p_careers = self.website_adapter.fetch_page(
                careers_url,
                source_type="careers_page",
                expected_domain=expected_domain,
                company_is_verified=company_is_verified,
            )
            add_payload(p_careers)

        # 3. Company Newsroom / Press Releases
        newsroom_url = None
        if configured_sources:
            for s in configured_sources:
                if s.get("source_type") in ("news_release", "newsroom"):
                    newsroom_url = s.get("source_url") or s.get("url")
                    break
        if not newsroom_url and website_url:
            newsroom_url = urljoin(website_url, "/news")

        if newsroom_url:
            p_news = self.newsroom_adapter.fetch_newsroom(
                newsroom_url,
                expected_domain=expected_domain,
                company_is_verified=company_is_verified,
            )
            add_payload(p_news)

        # 4. Engineering Blog & Technical Documentation
        blog_url = None
        if configured_sources:
            for s in configured_sources:
                if s.get("source_type") in ("engineering_blog", "tech_blog"):
                    blog_url = s.get("source_url") or s.get("url")
                    break
        if not blog_url and website_url:
            blog_url = urljoin(website_url, "/blog")

        if blog_url:
            p_blog = self.blog_adapter.fetch_engineering_blog(
                blog_url,
                expected_domain=expected_domain,
                company_is_verified=company_is_verified,
            )
            add_payload(p_blog)

        # 5. Investor Relations
        ir_url = None
        if configured_sources:
            for s in configured_sources:
                if s.get("source_type") in ("investor_relations", "ir"):
                    ir_url = s.get("source_url") or s.get("url")
                    break
        if not ir_url and website_url:
            ir_url = urljoin(website_url, "/investors")

        if ir_url:
            p_ir = self.ir_adapter.fetch_investor_relations(
                ir_url,
                expected_domain=expected_domain,
                company_is_verified=company_is_verified,
            )
            add_payload(p_ir)

        # 6. Permitted Public RSS / Atom / JSON Feeds
        if configured_sources:
            for s in configured_sources:
                stype = s.get("source_type", "")
                surl = s.get("source_url") or s.get("url", "")
                if not surl:
                    continue

                if stype in ("rss", "atom", "xml_feed", "rss_feed", "public_feed"):
                    add_payloads(
                        self.rss_adapter.fetch_feed(
                            surl,
                            expected_domain=expected_domain,
                            company_is_verified=company_is_verified,
                        )
                    )
                elif stype in ("json", "json_feed"):
                    add_payloads(
                        self.json_adapter.fetch_feed(
                            surl,
                            expected_domain=expected_domain,
                            company_is_verified=company_is_verified,
                        )
                    )

        return results
