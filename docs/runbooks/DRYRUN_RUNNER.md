# Dryrun Runner

This runbook explains how to execute a complete local dryrun without external calls.

## Preconditions
- RUN_MODE must be `dryrun`
- ALLOW_OUTBOUND_NETWORK must be `false`
- Fixture dataset must exist under `tests/fixtures/dryrun`

## Command

```bash
RUN_MODE=dryrun ALLOW_OUTBOUND_NETWORK=false python3 scripts/dryrun_runner.py
```

## Output Files
The runner creates:
- `tests/fixtures/dryrun/output/daily_briefing.generated.md`
- `tests/fixtures/dryrun/output/run_summary.json`

## What It Simulates
- Fixture loading (sources/items/enrichments)
- Item validation
- Deduplication by `content_hash` and URL
- Simulated connector failures (based on configured failure rate)
- Briefing generation for dashboard smoke tests

## Notes
- No real API keys are required in dryrun mode.
- No external network requests are made.
- Use `DRYRUN_SEED` for deterministic runs.
