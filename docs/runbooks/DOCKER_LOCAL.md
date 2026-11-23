# Local Docker Stack

This stack runs Atlas locally with:
- API (FastAPI)
- Worker
- Scheduler (dryrun loop)
- PostgreSQL
- Redis
- Web dashboard (static app)
- Optional OpenSearch profile

## Start

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

## Start with OpenSearch

```bash
docker compose -f infra/docker/docker-compose.yml --profile search up --build
```

## Start with HTTPS (Self-Signed)

1. Generate local certificate:

```bash
chmod +x scripts/gen-self-signed-cert.sh
./scripts/gen-self-signed-cert.sh
```

2. Start stack with HTTPS proxy profile:

```bash
docker compose -f infra/docker/docker-compose.yml --profile https up --build
```

3. Open dashboard in browser:

```text
https://localhost
```

Notes:
- Browser warning is expected with self-signed cert.
- API calls go through same-origin proxy path `/api`.
- Direct HTTP endpoints remain available on `http://127.0.0.1:8000` and `http://127.0.0.1:3000`.

## Later: Switch to Let's Encrypt

- Keep the `reverse-proxy` service and Caddy.
- In `infra/docker/Caddyfile`, replace local TLS line with domain-based site block.
- Example approach:
	- use `atlas.example.com` site block
	- remove explicit cert paths
	- let Caddy auto-provision certificates
- Persisted Caddy state already configured via Docker volumes:
	- `caddy_data`
	- `caddy_config`

## Health checks

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/config
```

## SQL Schema Initialization

- Initial schema is versioned in `migrations/001_initial_schema.sql`.
- API applies pending SQL migrations automatically on startup.

## RSS Connector First, Then Dashboard

Authentication:
- Default demo account: `demo` / `demo`.
- Login is required for connector runs and dashboard data APIs.

1. Trigger connector run (generic endpoint):

```bash
TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/auth/login" \
	-H "Content-Type: application/json" \
	-d '{"username":"demo","password":"demo"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -s -X POST "http://127.0.0.1:8000/connectors/rss/run?limit_per_feed=10" \
	-H "Authorization: Bearer ${TOKEN}"
```

Alternative generic form:

```bash
curl -s -X POST "http://127.0.0.1:8000/connectors/rss/run?limit_per_feed=10"
```

2. Open dashboard:

```text
http://127.0.0.1:3000
```

3. Optional JSON verification:

```bash
curl -s "http://127.0.0.1:8000/users/me/rss-sources" -H "Authorization: Bearer ${TOKEN}"
curl -s "http://127.0.0.1:8000/dashboard/items?connector=rss&limit=20" -H "Authorization: Bearer ${TOKEN}"
curl -s "http://127.0.0.1:8000/connectors/rss/latest?limit=20" -H "Authorization: Bearer ${TOKEN}"
curl -s "http://127.0.0.1:8000/connectors" -H "Authorization: Bearer ${TOKEN}"
```

Notes:
- In `RUN_MODE=dryrun` or when `ALLOW_OUTBOUND_NETWORK=false`, connector uses fixture data.
- In live mode with outbound network enabled, connector pulls real RSS feeds from `RSS_FEEDS`.
- `Latest Items` is empty until you run the RSS connector for the logged-in user.
- API service now defaults to outbound enabled via `ALLOW_OUTBOUND_NETWORK_API=true` in compose.
- Connector runs and fetched items are persisted in PostgreSQL tables:
	- connector_runs
	- connector_items
- RSS source catalog is imported from `old/rss-manager.jsx` (only entries with URL and status `ok` or `uncertain`).
- Dashboard and API responses are now scoped per authenticated user.
- You can still access API-native dashboard at `http://127.0.0.1:8000/dashboard`.

## Stop

```bash
docker compose -f infra/docker/docker-compose.yml down
```

## Reset data

```bash
docker compose -f infra/docker/docker-compose.yml down -v
```

## Notes

- Default mode is dryrun.
- Outbound network should remain disabled in dryrun.
- For local override values, create a `.env` file in repository root.
