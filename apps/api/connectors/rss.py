from __future__ import annotations

import json
import os
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .types import BaseConnector, ConnectorRunResult


class RSSConnector(BaseConnector):
    name = "rss"

    def run(self, limit_per_feed: int = 10, **kwargs) -> ConnectorRunResult:
        run_mode = os.getenv("RUN_MODE", "dryrun").strip().lower()
        allow_outbound = os.getenv("ALLOW_OUTBOUND_NETWORK", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }

        safe_limit = max(limit_per_feed, 1)

        if run_mode == "dryrun" or not allow_outbound:
            items = self._load_fixture_items()[: safe_limit * 50]
            return ConnectorRunResult(mode="dryrun-fixtures", items=items, errors=[])

        feeds_override = kwargs.get("feed_urls")
        feeds = [f for f in (feeds_override or self._get_feed_list()) if f]
        all_items: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        timeout = int(os.getenv("INGEST_HTTP_TIMEOUT_SEC", "30"))
        user_agent = os.getenv("INGEST_USER_AGENT", "atlas-rss-connector/0.1")

        for feed_url in feeds:
            parsed = urlparse(feed_url)
            source_name = parsed.netloc or "unknown-source"
            req = Request(feed_url, headers={"User-Agent": user_agent})
            try:
                with urlopen(req, timeout=timeout) as resp:
                    payload = resp.read()
                items = self._parse_rss_or_atom(payload, source_name, feed_url, safe_limit)
                all_items.extend(items)
            except (URLError, TimeoutError, ET.ParseError, ValueError) as exc:
                errors.append({"feed": feed_url, "error": str(exc)})

        all_items.sort(key=lambda x: (x.get("published_at", ""), x.get("title", "")), reverse=True)
        return ConnectorRunResult(mode="live-rss", items=all_items, errors=errors)

    def _text_or_empty(self, elem: ET.Element | None) -> str:
        return (elem.text or "").strip() if elem is not None else ""

    def _find_first(self, elem: ET.Element, candidates: list[str]) -> ET.Element | None:
        for c in candidates:
            found = elem.find(c)
            if found is not None:
                return found
        return None

    def _safe_dt(self, value: str) -> str:
        if not value:
            return ""
        try:
            dt = parsedate_to_datetime(value)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return value

    def _parse_rss_or_atom(
        self,
        xml_bytes: bytes,
        source_name: str,
        source_url: str,
        max_items: int,
    ) -> list[dict[str, str]]:
        root = ET.fromstring(xml_bytes)

        channel = root.find("channel")
        if channel is not None:
            out: list[dict[str, str]] = []
            for item in channel.findall("item")[:max_items]:
                title = self._text_or_empty(item.find("title"))
                link = self._text_or_empty(item.find("link"))
                pub = self._safe_dt(self._text_or_empty(item.find("pubDate")))
                if title or link:
                    out.append(
                        {
                            "source": source_name,
                            "source_url": source_url,
                            "title": title,
                            "url": link,
                            "published_at": pub,
                        }
                    )
            return out

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        out: list[dict[str, str]] = []
        for entry in entries[:max_items]:
            title = self._text_or_empty(entry.find("atom:title", ns))
            link_elem = self._find_first(entry, ["{http://www.w3.org/2005/Atom}link", "link"])
            link = ""
            if link_elem is not None:
                link = (link_elem.attrib.get("href") or "").strip() or self._text_or_empty(link_elem)
            published = self._text_or_empty(entry.find("atom:published", ns))
            updated = self._text_or_empty(entry.find("atom:updated", ns))
            pub = self._safe_dt(published or updated)
            if title or link:
                out.append(
                    {
                        "source": source_name,
                        "source_url": source_url,
                        "title": title,
                        "url": link,
                        "published_at": pub,
                    }
                )
        return out

    def _load_fixture_items(self) -> list[dict[str, str]]:
        dataset_path = Path(os.getenv("DRYRUN_DATASET_PATH", "./tests/fixtures/dryrun"))
        items_dir = dataset_path / "items"
        if not items_dir.exists():
            return []

        out: list[dict[str, str]] = []
        for path in sorted(items_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append(
                {
                    "source": data.get("source_id", "dryrun-source"),
                    "source_url": "fixture://dryrun",
                    "title": data.get("title", ""),
                    "url": data.get("url", ""),
                    "published_at": data.get("published_at", ""),
                }
            )
        out.sort(key=lambda x: (x.get("published_at", ""), x.get("title", "")), reverse=True)
        return out

    def _get_feed_list(self) -> list[str]:
        raw = os.getenv("RSS_FEEDS", "").strip()
        if raw:
            return [x.strip() for x in raw.split(",") if x.strip()]
        return [
            "https://www.lemonde.fr/rss/une.xml",
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://www.theguardian.com/world/rss",
        ]
