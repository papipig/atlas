#!/usr/bin/env python3
"""Dryrun pipeline runner.

Loads fixtures from tests/fixtures/dryrun and simulates:
- source polling
- item validation
- deduplication
- enrichment presence
- daily briefing generation

No external network calls are made.
"""

from __future__ import annotations

import glob
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ISO_FMT_HINT = "Expected ISO-8601 datetime string"
REQUIRED_ITEM_FIELDS = [
    "item_id",
    "source_id",
    "url",
    "title",
    "cleaned_content",
    "published_at",
    "fetched_at",
    "language",
    "content_hash",
]


@dataclass
class DryrunStats:
    total_items: int = 0
    valid_items: int = 0
    malformed_items: int = 0
    duplicates: int = 0
    simulated_failures: int = 0
    enriched_items: int = 0
    sources_count: int = 0


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_iso(ts: str) -> datetime:
    # Supports "Z" suffix in fixtures.
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _validate_item(item: dict[str, Any], known_source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item or item[field] in (None, ""):
            errors.append(f"missing_required_field:{field}")

    source_id = item.get("source_id")
    if source_id and source_id not in known_source_ids:
        errors.append("unknown_source_id")

    try:
        published_at = _parse_iso(item["published_at"])
        fetched_at = _parse_iso(item["fetched_at"])
        if published_at > fetched_at:
            errors.append("published_after_fetched")
    except Exception:
        errors.append(f"invalid_timestamp:{ISO_FMT_HINT}")

    return errors


def _read_glob_json(base_dir: Path, pattern: str) -> list[dict[str, Any]]:
    resolved = sorted(glob.glob(str(base_dir / pattern)))
    records: list[dict[str, Any]] = []
    for p in resolved:
        records.append(_load_json(Path(p)))
    return records


def _load_fixture_manifest(dataset_dir: Path) -> dict[str, Any]:
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing fixture manifest: {manifest_path}")
    return _load_json(manifest_path)


def _build_briefing(items: list[dict[str, Any]], enrichments_by_id: dict[str, dict[str, Any]]) -> str:
    # Very small deterministic briefing for smoke testing dashboard and API rendering.
    lines = [
        "# What is new today?",
        "",
        "## New studies and publications",
    ]

    for item in items[:10]:
        summary = enrichments_by_id.get(item["item_id"], {}).get("summary", "No summary")
        lines.append(f"- {item['title']}: {summary}")

    if len(lines) == 3:
        lines.append("- No new validated items in this run.")

    lines.extend([
        "",
        "## Notes",
        "- Generated in dryrun mode.",
        "- No external network calls were performed.",
    ])
    return "\n".join(lines) + "\n"


def run() -> int:
    run_mode = os.getenv("RUN_MODE", "dryrun").strip().lower()
    if run_mode != "dryrun":
        print(f"Refusing to run: RUN_MODE={run_mode}. Set RUN_MODE=dryrun.")
        return 2

    allow_outbound = os.getenv("ALLOW_OUTBOUND_NETWORK", "false").strip().lower()
    if allow_outbound in {"1", "true", "yes"}:
        print("Refusing to run: ALLOW_OUTBOUND_NETWORK must be false in dryrun.")
        return 2

    dataset_path = os.getenv("DRYRUN_DATASET_PATH", "./tests/fixtures/dryrun")
    dataset_dir = Path(dataset_path)
    if not dataset_dir.exists():
        print(f"Dataset directory not found: {dataset_dir}")
        return 2

    manifest = _load_fixture_manifest(dataset_dir)
    simulation = manifest.get("simulation", {})

    seed = int(os.getenv("DRYRUN_SEED", str(manifest.get("seed", 42))))
    failure_rate = float(
        os.getenv("DRYRUN_SIMULATED_FAILURE_RATE", str(simulation.get("failure_rate", 0.0)))
    )

    rng = random.Random(seed)
    stats = DryrunStats()

    includes = manifest.get("includes", {})
    sources_file = includes.get("sources", "sources.json")
    sources = _load_json(dataset_dir / sources_file)
    stats.sources_count = len(sources)

    known_source_ids = {s["source_id"] for s in sources if "source_id" in s}

    items_pattern = includes.get("items_glob", "items/*.json")
    items = _read_glob_json(dataset_dir, items_pattern)

    enrich_pattern = includes.get("enrichments_glob", "enrichments/*.json")
    enrichments = _read_glob_json(dataset_dir, enrich_pattern)
    enrichments_by_id = {e["item_id"]: e for e in enrichments if "item_id" in e}

    stats.total_items = len(items)

    seen_hashes: set[str] = set()
    seen_urls: set[str] = set()
    accepted_items: list[dict[str, Any]] = []

    for item in items:
        if rng.random() < failure_rate:
            stats.simulated_failures += 1
            continue

        errors = _validate_item(item, known_source_ids)
        if errors or item.get("malformed"):
            stats.malformed_items += 1
            continue

        content_hash = item["content_hash"]
        url = item["url"].strip().lower()

        if content_hash in seen_hashes or url in seen_urls:
            stats.duplicates += 1
            continue

        seen_hashes.add(content_hash)
        seen_urls.add(url)

        if item.get("item_id") in enrichments_by_id:
            stats.enriched_items += 1

        accepted_items.append(item)
        stats.valid_items += 1

    accepted_items.sort(key=lambda x: (x["published_at"], x["item_id"]))

    briefing_text = _build_briefing(accepted_items, enrichments_by_id)
    out_dir = dataset_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    briefing_out = out_dir / "daily_briefing.generated.md"
    summary_out = out_dir / "run_summary.json"

    briefing_out.write_text(briefing_text, encoding="utf-8")
    summary_out.write_text(
        json.dumps(
            {
                "run_mode": run_mode,
                "dataset": str(dataset_dir),
                "seed": seed,
                "failure_rate": failure_rate,
                "stats": stats.__dict__,
                "output": {
                    "briefing": str(briefing_out),
                    "summary": str(summary_out),
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Dryrun completed")
    print(json.dumps(stats.__dict__, indent=2))
    print(f"Briefing: {briefing_out}")
    print(f"Summary:  {summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
