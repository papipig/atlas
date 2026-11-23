#!/usr/bin/env python3
"""Local mock API server for dryrun fixtures.

No external dependencies required. Uses Python stdlib only.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

DEFAULT_DATASET = Path("tests/fixtures/dryrun")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_sources(dataset: Path) -> list[dict[str, Any]]:
    src = dataset / "sources.json"
    return load_json(src) if src.exists() else []


def load_items(dataset: Path) -> list[dict[str, Any]]:
    items_dir = dataset / "items"
    if not items_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(items_dir.glob("*.json")):
        records.append(load_json(path))
    return records


def load_enrichments(dataset: Path) -> dict[str, dict[str, Any]]:
    enrich_dir = dataset / "enrichments"
    if not enrich_dir.exists():
        return {}
    by_item: dict[str, dict[str, Any]] = {}
    for path in sorted(enrich_dir.glob("*.json")):
        data = load_json(path)
        item_id = data.get("item_id")
        if item_id:
            by_item[item_id] = data
    return by_item


def load_run_summary(dataset: Path) -> dict[str, Any] | None:
    path = dataset / "output" / "run_summary.json"
    if not path.exists():
        return None
    return load_json(path)


def load_briefing(dataset: Path) -> str | None:
    generated = dataset / "output" / "daily_briefing.generated.md"
    if generated.exists():
        return generated.read_text(encoding="utf-8")

    briefings_dir = dataset / "briefings"
    if not briefings_dir.exists():
        return None
    candidates = sorted(briefings_dir.glob("*.md"))
    if not candidates:
        return None
    return candidates[0].read_text(encoding="utf-8")


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler: BaseHTTPRequestHandler, status: int, text: str) -> None:
    body = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/markdown; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class MockHandler(BaseHTTPRequestHandler):
    dataset: Path

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/health":
            return json_response(
                self,
                200,
                {
                    "status": "ok",
                    "mode": "dryrun-mock-api",
                    "dataset": str(self.dataset),
                },
            )

        if parsed.path == "/api/mock/run-summary":
            summary = load_run_summary(self.dataset)
            if summary is None:
                return json_response(
                    self,
                    404,
                    {
                        "error": "run_summary_not_found",
                        "hint": "Run: RUN_MODE=dryrun ALLOW_OUTBOUND_NETWORK=false python3 scripts/dryrun_runner.py",
                    },
                )
            return json_response(self, 200, summary)

        if parsed.path == "/api/mock/briefing":
            briefing = load_briefing(self.dataset)
            if briefing is None:
                return json_response(
                    self,
                    404,
                    {
                        "error": "briefing_not_found",
                        "hint": "No generated briefing in dryrun dataset",
                    },
                )
            format_ = (query.get("format", ["json"])[0] or "json").lower()
            if format_ == "md":
                return text_response(self, 200, briefing)
            return json_response(
                self,
                200,
                {
                    "title": "What is new today?",
                    "markdown": briefing,
                },
            )

        if parsed.path == "/api/mock/sources":
            sources = load_sources(self.dataset)
            return json_response(self, 200, {"count": len(sources), "sources": sources})

        if parsed.path == "/api/mock/items":
            try:
                limit = int(query.get("limit", ["50"])[0])
            except ValueError:
                limit = 50
            limit = max(1, min(limit, 500))

            source_filter = query.get("source_id", [None])[0]
            include_enrichment = (query.get("include_enrichment", ["true"])[0] or "true").lower() in {
                "1",
                "true",
                "yes",
            }

            items = load_items(self.dataset)
            enrichments = load_enrichments(self.dataset)

            out: list[dict[str, Any]] = []
            for item in items:
                if source_filter and item.get("source_id") != source_filter:
                    continue
                record = dict(item)
                if include_enrichment:
                    record["enrichment"] = enrichments.get(item.get("item_id"))
                out.append(record)

            out.sort(key=lambda x: (x.get("published_at", ""), x.get("item_id", "")), reverse=True)
            out = out[:limit]

            return json_response(self, 200, {"count": len(out), "items": out})

        return json_response(
            self,
            404,
            {
                "error": "not_found",
                "available_endpoints": [
                    "/health",
                    "/api/mock/run-summary",
                    "/api/mock/briefing?format=json|md",
                    "/api/mock/sources",
                    "/api/mock/items?limit=50&source_id=...&include_enrichment=true",
                ],
            },
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep terminal output concise during local runs.
        return


def build_handler(dataset: Path):
    class _DatasetBoundHandler(MockHandler):
        pass

    _DatasetBoundHandler.dataset = dataset
    return _DatasetBoundHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local dryrun mock API")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8081, help="Bind port")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET),
        help="Path to dryrun dataset directory",
    )
    args = parser.parse_args()

    dataset = Path(args.dataset)
    if not dataset.exists():
        print(f"Dataset does not exist: {dataset}")
        return 2

    handler = build_handler(dataset)
    server = HTTPServer((args.host, args.port), handler)
    print(f"Mock API listening on http://{args.host}:{args.port}")
    print(f"Dataset: {dataset}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
