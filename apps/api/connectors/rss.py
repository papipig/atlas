from __future__ import annotations

import html
import json
import os
import re
import ssl
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from typing import Any

import feedparser

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
        feeds_override = kwargs.get("feed_urls")
        feeds = [f for f in (feeds_override or self._get_feed_list()) if f]

        # For dashboard user flows, prefer real RSS feeds whenever explicit feed URLs are provided.
        # Dryrun fixtures are kept only as fallback when there is no configured feed list.
        if not feeds:
            items = self._load_fixture_items()[: safe_limit * 50]
            return ConnectorRunResult(mode="dryrun-fixtures", items=items, errors=[])

        if not allow_outbound:
            return ConnectorRunResult(
                mode="network-blocked",
                items=[],
                errors=[
                    {
                        "feed": "*",
                        "error": "Outbound network is disabled. Enable ALLOW_OUTBOUND_NETWORK for real RSS fetches.",
                    }
                ],
            )

        all_items: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        timeout = int(os.getenv("INGEST_HTTP_TIMEOUT_SEC", "30"))
        user_agent = os.getenv("INGEST_USER_AGENT", "atlas-rss-connector/0.1")

        allow_insecure_ssl = os.getenv("ALLOW_INSECURE_SSL_FEEDS", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        include_fallback_feed_items = os.getenv("INCLUDE_FEED_FALLBACK_ITEMS", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }

        for feed_url in feeds:
            parsed = urlparse(feed_url)
            source_name = parsed.netloc or "unknown-source"

            items, err = self._collect_feed_items(
                feed_url=feed_url,
                source_name=source_name,
                user_agent=user_agent,
                timeout=timeout,
                safe_limit=safe_limit,
                allow_insecure_ssl=allow_insecure_ssl,
            )
            if items:
                all_items.extend(items)
            elif err:
                errors.append({"feed": feed_url, "error": err})
                if include_fallback_feed_items:
                    all_items.append(
                        {
                            "source": source_name,
                            "source_url": feed_url,
                            "title": "Feed currently unavailable - open source URL",
                            "url": feed_url,
                            "published_at": "",
                        }
                    )

        # Deduplicate by URL first, then by title+source when URL is absent.
        seen: set[str] = set()
        unique_items: list[dict[str, str]] = []
        for item in all_items:
            key = item.get("url") or f"{item.get('source','')}|{item.get('title','')}"
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)

        unique_items.sort(key=lambda x: (x.get("published_at", ""), x.get("title", "")), reverse=True)
        mode = "live-rss" if run_mode != "dryrun" else "dryrun-live-rss"
        return ConnectorRunResult(mode=mode, items=unique_items, errors=errors)

    def _collect_feed_items(
        self,
        feed_url: str,
        source_name: str,
        user_agent: str,
        timeout: int,
        safe_limit: int,
        allow_insecure_ssl: bool,
    ) -> tuple[list[dict[str, str]], str | None]:
        candidates = self._candidate_urls(feed_url)
        attempted: list[str] = []
        discovery_attempted = False

        for candidate in candidates:
            attempted.append(candidate)
            payload, fetch_err = self._fetch_payload(
                url=candidate,
                user_agent=user_agent,
                timeout=timeout,
                allow_insecure_ssl=allow_insecure_ssl,
            )
            if fetch_err:
                # For 404/403, try discovery from the website homepage once.
                if ("HTTP Error 404" in fetch_err or "HTTP Error 403" in fetch_err) and not discovery_attempted:
                    discovered = self._discover_feed_candidates(candidate, user_agent, timeout, allow_insecure_ssl)
                    discovery_attempted = True
                    for extra in discovered:
                        if extra not in candidates:
                            candidates.append(extra)
                continue

            items = self._parse_feed_with_fallback(payload, source_name, feed_url, safe_limit)
            if items:
                return items, None

        final_err = "No readable feed found"
        if attempted:
            final_err = f"{final_err} after trying {len(attempted)} URL(s): {', '.join(attempted[:4])}"
            if len(attempted) > 4:
                final_err += ", ..."
        return [], final_err

    def _fetch_payload(
        self,
        url: str,
        user_agent: str,
        timeout: int,
        allow_insecure_ssl: bool,
    ) -> tuple[bytes | None, str | None]:
        req = Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            },
        )
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read(), None
        except ssl.SSLCertVerificationError as exc:
            if not allow_insecure_ssl:
                return None, str(exc)
            try:
                insecure_ctx = ssl._create_unverified_context()
                with urlopen(req, timeout=timeout, context=insecure_ctx) as resp:
                    return resp.read(), None
            except Exception as retry_exc:  # noqa: BLE001
                return None, str(retry_exc)
        except HTTPError as exc:
            return None, f"HTTP Error {exc.code}: {exc.reason}"
        except (URLError, TimeoutError, OSError) as exc:
            return None, str(exc)

    def _parse_feed_with_fallback(
        self,
        payload: bytes,
        source_name: str,
        source_url: str,
        max_items: int,
    ) -> list[dict[str, str]]:
        # Fast path for well-formed RSS/Atom.
        try:
            parsed_items = self._parse_rss_or_atom(payload, source_name, source_url, max_items)
            if parsed_items:
                return parsed_items
        except (ET.ParseError, ValueError):
            pass

        # Fallback for malformed XML/entities commonly found in public feeds.
        feed = feedparser.parse(payload)
        out: list[dict[str, str]] = []
        for entry in feed.entries[:max_items]:
            title = html.unescape(str(getattr(entry, "title", "") or "").strip())
            link = str(getattr(entry, "link", "") or "").strip()
            published_raw = str(
                getattr(entry, "published", "")
                or getattr(entry, "updated", "")
                or getattr(entry, "created", "")
                or ""
            ).strip()
            published = self._safe_dt(published_raw)
            if title or link:
                description = self._text_or_empty(entry.get("description"))
                content_elem = entry.get("content")
                content = self._text_or_empty(content_elem)
                if not content:
                    content_elem = entry.get("encoded")
                    content = self._text_or_empty(content_elem)
                text = html.unescape(content or description).strip()
                out.append(
                    {
                        "source": source_name,
                        "source_url": source_url,
                        "title": title,
                        "url": link,
                        "published_at": published,
                        "description": description,
                        "content": text,
                    }
                )
        return out

    def _candidate_urls(self, url: str) -> list[str]:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return [url]

        candidates: list[str] = [url]

        # Try trailing slash variants.
        if parsed.path and not parsed.path.endswith("/"):
            candidates.append(url + "/")
        if parsed.path.endswith("/") and parsed.path != "/":
            candidates.append(url.rstrip("/"))

        # Try host variants (www/non-www).
        host = parsed.netloc
        if host.startswith("www."):
            alt_host = host[4:]
        else:
            alt_host = f"www.{host}"
        if alt_host and alt_host != host:
            alt_base = f"{parsed.scheme}://{alt_host}"
            candidates.append(alt_base + parsed.path)
            if parsed.path == "/" or not parsed.path:
                candidates.extend([
                    f"{alt_base}/feed/",
                    f"{alt_base}/rss.xml",
                    f"{alt_base}/feed.xml",
                ])

        # For root-like URLs, try common feed endpoints.
        if parsed.path in {"", "/"}:
            base = f"{parsed.scheme}://{parsed.netloc}"
            candidates.extend([
                f"{base}/feed/",
                f"{base}/rss",
                f"{base}/rss.xml",
                f"{base}/feed.xml",
                f"{base}/atom.xml",
            ])

        deduped: list[str] = []
        for c in candidates:
            if c not in deduped:
                deduped.append(c)
        return deduped

    def _discover_feed_candidates(
        self,
        from_url: str,
        user_agent: str,
        timeout: int,
        allow_insecure_ssl: bool,
    ) -> list[str]:
        parsed = urlparse(from_url)
        if not parsed.scheme or not parsed.netloc:
            return []
        homepage = f"{parsed.scheme}://{parsed.netloc}/"
        payload, err = self._fetch_payload(homepage, user_agent, timeout, allow_insecure_ssl)
        if err or not payload:
            return []

        text = payload.decode("utf-8", errors="ignore")
        hrefs = re.findall(
            r"<link[^>]+rel=[\"'][^\"']*alternate[^\"']*[\"'][^>]+type=[\"'](?:application/rss\+xml|application/atom\+xml|text/xml)[\"'][^>]+href=[\"']([^\"']+)[\"']",
            text,
            flags=re.IGNORECASE,
        )
        if not hrefs:
            hrefs = re.findall(
                r"<a[^>]+href=[\"']([^\"']*(?:rss|feed|atom)[^\"']*)[\"']",
                text,
                flags=re.IGNORECASE,
            )

        out: list[str] = []
        for href in hrefs:
            cand = urljoin(homepage, href.strip())
            if cand and cand not in out:
                out.append(cand)
        return out

    def _text_or_empty(self, elem: Any) -> str:
        if elem is None:
            return ""
        if isinstance(elem, str):
            return html.unescape(elem).strip()
        if isinstance(elem, dict):
            return self._text_or_empty(elem.get("value") or elem.get("text") or elem.get("content"))
        if isinstance(elem, (list, tuple)):
            for item in elem:
                text = self._text_or_empty(item)
                if text:
                    return text
            return ""
        text = getattr(elem, "text", None)
        return html.unescape(str(text or "")).strip()

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
                    description = self._text_or_empty(item.find("description"))
                    content_elem = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
                    content = self._text_or_empty(content_elem)
                    if not content:
                        content_elem = item.find("content")
                        content = self._text_or_empty(content_elem)
                    text = html.unescape(content or description).strip()
                    out.append(
                        {
                            "source": source_name,
                            "source_url": source_url,
                            "title": title,
                            "url": link,
                            "published_at": pub,
                            "description": description,
                            "content": text,
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
                summary_elem = entry.find("atom:summary", ns)
                content_elem = entry.find("atom:content", ns)
                description = self._text_or_empty(summary_elem)
                content = self._text_or_empty(content_elem)
                text = html.unescape(content or description).strip()
                out.append(
                    {
                        "source": source_name,
                        "source_url": source_url,
                        "title": title,
                        "url": link,
                        "published_at": pub,
                        "description": description,
                        "content": text,
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
