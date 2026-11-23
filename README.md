# Atlas

Atlas is an intelligence dashboard project focused on one daily question:

- What is new in the world today?

It ingests sources through connectors (RSS first), stores runs in PostgreSQL, and serves a per-user dashboard.

## Current MVP

- Modular connectors (RSS implemented, others scaffolded)
- User authentication with demo account
- Per-user RSS source selection
- Connector runs and items persisted in PostgreSQL
- Web dashboard + API
- Docker stack with optional HTTPS reverse proxy

## Quick Start (Docker)

From project root:

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

Open:

- Web dashboard: http://127.0.0.1:3000
- API docs base: http://127.0.0.1:8000

## HTTPS Local (Self-Signed)

Generate local certificate:

```bash
chmod +x scripts/gen-self-signed-cert.sh
./scripts/gen-self-signed-cert.sh
```

Start with HTTPS profile:

```bash
docker compose -f infra/docker/docker-compose.yml --profile https up --build
```

Open:

- https://localhost

## Login

Default demo account:

- username: demo
- password: demo

## Test RSS Flow

1. Login from web dashboard.
2. Keep or adjust your RSS source selection.
3. Run connector rss.
4. Refresh latest items.

You can also test via API after login token issuance.

## Key Paths

- Product and architecture manifesto: MANIFEST.md
- Local Docker runbook: docs/runbooks/DOCKER_LOCAL.md
- API app: apps/api
- Web app: apps/web
- SQL migrations: migrations
