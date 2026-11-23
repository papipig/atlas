from __future__ import annotations

from .types import BaseConnector, ConnectorRunResult


class ScrapeConnector(BaseConnector):
    name = "scrape"

    def run(self, limit_per_feed: int = 10) -> ConnectorRunResult:
        raise NotImplementedError("Scrape connector is not implemented yet")
