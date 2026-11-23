from __future__ import annotations

from .types import BaseConnector, ConnectorRunResult


class XConnector(BaseConnector):
    name = "x"

    def run(self, limit_per_feed: int = 10) -> ConnectorRunResult:
        raise NotImplementedError("X connector is not implemented yet")
