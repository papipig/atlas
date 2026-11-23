from __future__ import annotations

from .types import BaseConnector, ConnectorRunResult


class FacebookConnector(BaseConnector):
    name = "facebook"

    def run(self, limit_per_feed: int = 10) -> ConnectorRunResult:
        raise NotImplementedError("Facebook connector is not implemented yet")
