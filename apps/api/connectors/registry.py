from __future__ import annotations

from .facebook import FacebookConnector
from .rss import RSSConnector
from .scrape import ScrapeConnector
from .social_x import XConnector
from .types import BaseConnector


_CONNECTORS: dict[str, BaseConnector] = {
    "rss": RSSConnector(),
    "scrape": ScrapeConnector(),
    "x": XConnector(),
    "facebook": FacebookConnector(),
}


def list_connectors() -> list[str]:
    return sorted(_CONNECTORS.keys())


def get_connector(name: str) -> BaseConnector:
    key = name.strip().lower()
    if key not in _CONNECTORS:
        raise KeyError(f"Unknown connector: {name}")
    return _CONNECTORS[key]
