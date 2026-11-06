import hashlib
import re
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Common tracking parameters to strip for canonical URL deduplication
_TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "trk",
    "gh_src",
}

_ROMAN_NUMERALS_MAP = {
    r"\biv\b": "4",
    r"\biii\b": "3",
    r"\bii\b": "2",
    r"\bi\b": "1",
}


def canonicalize_job_url(url: Optional[str]) -> Optional[str]:
    """Strip tracking and marketing query parameters to create a canonical URL for deduplication."""
    if not url or not url.strip():
        return None

    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parsed.path.rstrip("/")

        # Filter out tracking query params while preserving meaningful resource params
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        filtered_pairs = [(k, v) for k, v in query_pairs if k.lower() not in _TRACKING_QUERY_PARAMS]
        filtered_query = urlencode(filtered_pairs)

        canonical = urlunparse((parsed.scheme.lower(), netloc, path, "", filtered_query, ""))
        return canonical
    except Exception:
        return cleaned


def compute_canonical_url_hash(url: Optional[str]) -> Optional[str]:
    """Return SHA-256 hex digest of the canonical URL."""
    canonical = canonicalize_job_url(url)
    if not canonical:
        return None
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_job_title(title: str) -> str:
    """Normalize a job title to lowercase alphanumeric baseline for duplicate clustering.

    Examples:
        'Senior Software Engineer - Backend' -> 'senior software engineer backend'
        'Backend Developer II (Python)' -> 'backend developer 2 python'
    """
    if not title:
        return ""

    lowered = title.lower()

    # Normalize Roman numerals
    for pattern, replacement in _ROMAN_NUMERALS_MAP.items():
        lowered = re.sub(pattern, replacement, lowered, flags=re.IGNORECASE)

    # Remove punctuation
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    tokens = [t for t in cleaned.split() if t]
    return " ".join(tokens)
