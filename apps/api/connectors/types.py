from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectorRunResult:
    mode: str
    items: list[dict[str, str]]
    errors: list[dict[str, str]]


class BaseConnector:
    name: str = "base"

    def run(self, limit_per_feed: int = 10, **kwargs) -> ConnectorRunResult:
        raise NotImplementedError
