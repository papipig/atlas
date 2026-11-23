# Mock API (Dryrun)

This mock API serves dryrun data to frontend and integration tests without external calls.

## Start

```bash
python3 scripts/mock_api_server.py --host 127.0.0.1 --port 8081
```

Optional dataset path:

```bash
python3 scripts/mock_api_server.py --dataset tests/fixtures/dryrun --port 8081
```

## Endpoints

- GET /health
- GET /api/mock/run-summary
- GET /api/mock/briefing?format=json|md
- GET /api/mock/sources
- GET /api/mock/items?limit=50&source_id=<id>&include_enrichment=true

## Example Calls

```bash
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1:8081/api/mock/run-summary
curl -s http://127.0.0.1:8081/api/mock/briefing
curl -s "http://127.0.0.1:8081/api/mock/items?limit=10"
```

## Notes

- The API reads fixtures from tests/fixtures/dryrun.
- If run summary is missing, run the dryrun runner first:

```bash
RUN_MODE=dryrun ALLOW_OUTBOUND_NETWORK=false python3 scripts/dryrun_runner.py
```
