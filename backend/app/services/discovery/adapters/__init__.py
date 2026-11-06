"""Source adapter architecture for automated job discovery."""

from app.services.discovery.adapters.ashby import AshbyAdapter
from app.services.discovery.adapters.base import BaseSourceAdapter, DiscoveredJob
from app.services.discovery.adapters.greenhouse import GreenhouseAdapter
from app.services.discovery.adapters.json_feed import JSONFeedAdapter
from app.services.discovery.adapters.lever import LeverAdapter
from app.services.discovery.adapters.registry import get_adapter, list_supported_adapters
from app.services.discovery.adapters.rss import RSSFeedAdapter

__all__ = [
    "BaseSourceAdapter",
    "DiscoveredJob",
    "GreenhouseAdapter",
    "LeverAdapter",
    "AshbyAdapter",
    "RSSFeedAdapter",
    "JSONFeedAdapter",
    "get_adapter",
    "list_supported_adapters",
]
