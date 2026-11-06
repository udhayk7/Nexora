from app.core.errors import BadRequestError
from app.services.discovery.adapters.ashby import AshbyAdapter
from app.services.discovery.adapters.base import BaseSourceAdapter
from app.services.discovery.adapters.greenhouse import GreenhouseAdapter
from app.services.discovery.adapters.json_feed import JSONFeedAdapter
from app.services.discovery.adapters.lever import LeverAdapter
from app.services.discovery.adapters.rss import RSSFeedAdapter

ADAPTER_CLASSES: dict[str, type[BaseSourceAdapter]] = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "rss_feed": RSSFeedAdapter,
    "json_feed": JSONFeedAdapter,
}


def get_adapter(adapter_name: str) -> BaseSourceAdapter:
    """Retrieve an instantiated adapter by its registered name."""
    normalized = (adapter_name or "").strip().lower()
    adapter_cls = ADAPTER_CLASSES.get(normalized)
    if not adapter_cls:
        valid_keys = ", ".join(ADAPTER_CLASSES.keys())
        raise BadRequestError(
            f"Unsupported source adapter '{adapter_name}'. Supported adapters: {valid_keys}"
        )
    return adapter_cls()


def list_supported_adapters() -> list[dict[str, str]]:
    """List all supported adapters with display names and descriptions."""
    return [
        {
            "id": "greenhouse",
            "name": "Greenhouse Job Board",
            "description": "Public Greenhouse API using board token or URL.",
            "example_token": "stripe",
            "token_label": "Board Token / Slug",
        },
        {
            "id": "lever",
            "name": "Lever Job Postings",
            "description": "Public Lever API using site slug or jobs.lever.co URL.",
            "example_token": "netflix",
            "token_label": "Site Slug",
        },
        {
            "id": "ashby",
            "name": "Ashby Job Board",
            "description": "Public Ashby API using board name or jobs.ashbyhq.com URL.",
            "example_token": "linear",
            "token_label": "Board Name",
        },
        {
            "id": "rss_feed",
            "name": "RSS / Atom Job Feed",
            "description": "Public XML RSS 2.0 or Atom career feed URL.",
            "example_token": "https://example.com/careers.xml",
            "token_label": "Feed URL",
        },
        {
            "id": "json_feed",
            "name": "Custom JSON Feed",
            "description": "Public JSON endpoint providing career opportunity listings.",
            "example_token": "https://api.example.com/v1/jobs",
            "token_label": "API Endpoint URL",
        },
    ]
