# Dryrun Fixture Specification

This document defines the fixture format used when `RUN_MODE=dryrun`.

Goals:
- Run end-to-end pipeline tests without external network calls.
- Produce deterministic and reproducible results.
- Simulate realistic success and failure cases.

## Folder Layout

```text
tests/fixtures/dryrun/
  manifest.json
  sources.json
  items/
    think_tank_fr_001.json
    press_intl_001.json
  enrichments/
    think_tank_fr_001.enrichment.json
  briefings/
    daily_fr_2026-11-22.md
```

## 1) manifest.json

Top-level control file loaded first.

```json
{
  "version": 1,
  "seed": 42,
  "generated_at": "2026-11-22T06:00:00Z",
  "timezone": "Europe/Paris",
  "window": {
    "start": "2026-11-21T06:00:00Z",
    "end": "2026-11-22T06:00:00Z"
  },
  "includes": {
    "sources": "sources.json",
    "items_glob": "items/*.json",
    "enrichments_glob": "enrichments/*.json",
    "briefings_glob": "briefings/*.md"
  },
  "simulation": {
    "inject_duplicates": true,
    "inject_malformed_items": true,
    "failure_rate": 0.03,
    "latency_ms": { "min": 20, "max": 250 }
  }
}
```

## 2) sources.json

Synthetic source registry used by dryrun ingestion.

```json
[
  {
    "source_id": "src_thinktank_frs",
    "name": "FRS",
    "domain_type": "think_tank",
    "ingestion_mode": "rss",
    "polling_cron": "0 6 * * *",
    "default_language": "fr",
    "active": true,
    "recipe": {
      "primary_connector": "rss",
      "fallback_chain": ["scrape"],
      "request_policy": {
        "timeout_sec": 30,
        "max_retries": 3,
        "rate_limit_rpm": 30
      }
    }
  }
]
```

## 3) items/*.json

Each file is one canonical item payload entering normalization/dedup.

Required fields:
- item_id
- source_id
- url
- title
- cleaned_content
- published_at
- fetched_at
- language
- content_hash

Optional fields:
- external_id
- raw_content
- authors
- tags_hint
- actors_hint
- malformed (for failure simulation)

Example:

```json
{
  "item_id": "itm_2026_11_22_0001",
  "source_id": "src_thinktank_frs",
  "external_id": "frs-rss-987654",
  "url": "https://example.org/report-2026-strategy",
  "title": "New Strategic Outlook 2026",
  "raw_content": "<html>...</html>",
  "cleaned_content": "A new report evaluates strategic posture in Europe...",
  "published_at": "2026-11-22T04:30:00Z",
  "fetched_at": "2026-11-22T06:01:20Z",
  "language": "en",
  "content_hash": "sha256:2f7a...",
  "authors": ["Example Author"]
}
```

## 4) enrichments/*.json

Optional precomputed enrichment fixtures. If absent, worker can generate synthetic enrichment.

Required fields:
- item_id
- summary
- tags
- sentiment
- actors
- model_provider
- model_name
- prompt_version
- processed_at

Example:

```json
{
  "item_id": "itm_2026_11_22_0001",
  "summary": "The report introduces a revised force posture framework.",
  "tags": ["defense", "europe", "strategy"],
  "sentiment": "neutral",
  "actors": ["France", "European Union", "NATO"],
  "model_provider": "dryrun",
  "model_name": "fixture-engine",
  "prompt_version": "v1",
  "processed_at": "2026-11-22T06:03:10Z"
}
```

## 5) briefings/*.md

Optional prebuilt daily briefing templates for dashboard smoke tests.

Suggested filename:
- daily_<lang>_<YYYY-MM-DD>.md

## 6) Validation Rules

Validation should fail fast when:
- `source_id` in item does not exist in `sources.json`.
- Required fields are missing.
- Timestamp fields are not ISO-8601.
- `published_at` is after `fetched_at`.

## 7) Determinism Rules

For repeatable tests:
- Keep `seed` fixed.
- Keep fixture timestamps fixed (or deterministically shifted).
- Keep item ordering stable by `published_at`, then `item_id`.

## 8) Suggested Initial Dataset Size

- 25 sources
- 250 items/day
- 10-20 duplicate candidates
- 5 malformed items
- 5 simulated connector failures

This gives realistic stress without external risk.
