# MANIFEST

## 1) Mission
Build an intelligence platform that continuously collects public information from strategic sources, processes it with provider-agnostic LLM workflows, and delivers executive-grade daily syntheses.

Core product question:
- What is new in the world today?
- Which new studies, publications, statements, and signals have appeared in the last 24 hours?

The platform must be:
- Configurable by admins without code changes.
- Reliable for daily operations.
- Explainable and auditable.
- Scalable from local testing to VPS deployment.

## 2) Product Vision
The product is a server-based system that:
- Polls source lists on configurable schedules (default: once per day).
- Ingests content via RSS/API first, then scraping fallback.
- Normalizes and stores all content for long-term intelligence use.
- Runs AI processing on newly ingested items (summary, tags, sentiment, geopolitical actors).
- Produces executive-facing syntheses and daily briefings.
- Exposes search and filtering in a web dashboard.

Primary product outcome:
- Deliver a clear daily answer to what is new today, not a generic news feed.
- Highlight only newly published or newly detected items in the selected time window.
- Separate truly new signals from repeated commentary.

Primary user experience priority:
- Executive-style synthesis and daily briefing first.

## 3) Source Domains
Initial source domains:
- Think tanks
- Press
- Publications on X
- Truth
- Blogs

Examples include institutions, media, public figures, and specialized blogs listed by product ownership.

All source definitions are configurable in admin settings:
- Source name and URL(s)
- Source type (RSS/API/scrape)
- Polling strategy (cron-like)
- Priority and category
- Custom prompt template for AI processing
- Language hint
- Activation status

## 4) Core Principles
- RSS/API first: prefer structured and official endpoints when available.
- Scraping fallback: only when feeds/APIs are unavailable.
- Provider-agnostic AI: LLM layer must support multiple vendors through a unified interface.
- Human control: admins define ingestion and prompt behavior.
- Traceability: every synthesis links to underlying sources.
- Security by default: role-based access, audit logs, hardened deployment profile.

## 5) Roles and Permissions
### Admin
Can:
- Create/edit/deactivate sources.
- Configure polling strategies per source.
- Configure AI prompt templates globally and per source.
- Manage LLM provider selection and model routing.
- Manage system settings and moderation rules.

### User
Can:
- Access dashboard, briefing views, and source content.
- Configure personal dashboard preferences and filters.
- Use search and saved views.

## 6) Language and Localization
- Default interface and summarization language: French.
- Multilingual behavior is configurable in dashboard settings.
- Content language detection at ingestion time informs downstream summarization and indexing.

## 7) Functional Capabilities
### Ingestion
- Scheduled polling with per-source schedule.
- Backoff/retry policies for network/API failures.
- Duplicate detection using content fingerprinting and source-level IDs.

### Processing
For each new item:
- Short executive summary.
- Tag extraction (themes/topics).
- Sentiment classification.
- Geopolitical actor extraction.

Prompting model:
- Global prompt baseline.
- Source-specific prompt overrides.
- Versioned prompt templates for reproducibility.

### Synthesis
- Daily briefing generated from selected time window and source scope.
- Optional thematic synthesis (defense, energy, diplomacy, etc.).
- Evidence-first output linking each insight to source items.
- First section in every briefing: "What is new today?"
- Structured output per novelty type:
  - New studies/reports
  - New official statements
  - New media investigations
  - New policy/market/security signals
  - Newly emerging weak signals (low volume but strategic)

### Dashboard
- Executive home view with daily briefing.
- Search over content and metadata.
- Filters by date, source, category, language, sentiment, tags, actors.
- Saved filters/views.

## 8) Recommended Technology Stack
This project should use a hybrid architecture.

TypeScript is not required for all backend logic. It is JavaScript with static typing and runs in the Node.js ecosystem. In this architecture, TypeScript is used only for frontend and optional API gateway/admin tooling, while Python handles ingestion and AI-heavy workflows.

### Backend and Processing (Python-first)
- API and services: FastAPI
- Job orchestration and scheduling: Celery + Celery Beat (cron-like schedules)
- Message broker and cache: Redis
- Data/ETL tooling: Python workers (httpx, feedparser, trafilatura/readability-lxml, newspaper4k alternative if needed)
- AI orchestration layer: custom provider abstraction in Python

Why:
- Strong ecosystem for scraping, NLP, and AI pipelines.
- Excellent fit with your Python preference.

### Frontend and Admin UI
- Web framework: Next.js (React + TypeScript)
- Styling/UI: Tailwind CSS + component system (shadcn/ui or equivalent)
- Auth integration with backend RBAC endpoints

Why:
- Robust admin UX and dashboard capabilities.
- Easy deployment as static/server-rendered web app.

### Data and Search
- Primary relational DB: PostgreSQL
- Full-text and faceted search: OpenSearch (or Elasticsearch-compatible)
- Optional vector retrieval later: pgvector in PostgreSQL

Why:
- PostgreSQL provides durable structured storage.
- OpenSearch enables fast filtering and analyst-grade search.

### Deployment and Operations
- Containerization: Docker + Docker Compose (local and VPS baseline)
- Reverse proxy: Caddy or Nginx
- Observability: Prometheus + Grafana + Loki (or lightweight logs first)
- Background monitoring: Flower for Celery

### LLM Provider Abstraction
Implement a provider adapter interface:
- Anthropic adapter
- OpenAI adapter
- Mistral adapter
- Local model adapter (future)

Routing strategy:
- Global default provider/model
- Per-source override capability
- Fallback chain on provider failure

## 9) Architecture: Single Pipeline, Multiple Connectors
The project uses one business pipeline with multiple acquisition connectors.

Design rule:
- Do not build separate applications for RSS, APIs, and scraping.
- Build one orchestration layer that selects the correct connector per source configuration.

### 9.1 Runtime Components
1. Scheduler/Orchestrator
  - Reads source schedules (cron-like) and dispatches polling jobs.
  - Supports default strategy (once per day) and per-source overrides.
2. Connector Layer (pluggable adapters)
  - RSS/Atom connector
  - Official API connector
  - Web scraping connector (fallback)
3. Normalization Layer
  - Converts acquired payloads to canonical item schema.
4. Deduplication Layer
  - URL canonicalization + external IDs + content hashing.
5. Enrichment Layer
  - LLM processing for summary, tags, sentiment, and geopolitical actors.
6. Synthesis Layer
  - Builds executive daily briefing and thematic syntheses.
7. API + Dashboard Layer
  - Admin setup, monitoring views, search, filtering, and user preferences.

### 9.2 Source Strategy (Recipe Model)
Each source has an admin-configurable recipe:
- Primary mode: `rss` | `api` | `scrape`
- Fallback chain: for example `rss -> scrape`
- Polling schedule (cron)
- Request policy: timeout, retries, backoff, rate limits
- Parsing rules (especially for scraping selectors)
- Prompt template assignment (global default + source override)

This enables adding new sources mainly by configuration, not code changes.

### 9.3 End-to-End Flow
1. Scheduler creates a polling run for eligible sources.
2. Orchestrator executes the source's primary connector.
3. If primary fails, fallback chain is attempted according to policy.
4. Raw payload and metadata are persisted for traceability.
5. Content is normalized into canonical items.
6. Deduplication marks existing vs new items.
7. New items are enriched by LLM adapters.
8. Items and enrichments are indexed for search/filtering.
9. Daily briefing job composes executive synthesis.

### 9.4 Reliability and Operations
- Retry with exponential backoff and capped attempts.
- Dead-letter queue for persistent failures.
- Per-source health metrics:
  - last successful poll
  - success/failure rate
  - average latency
  - connector used (primary/fallback)
- Alerting for source degradation and parsing breakages.
- Full auditability of admin changes to source recipes and prompt rules.

### 9.5 ASCII Architecture Diagram

    +---------------------------+
    | Admin UI / API Settings   |
    | - sources                 |
    | - recipes                 |
    | - prompts                 |
    +-------------+-------------+
        |
        v
    +---------------------------+
    | Scheduler / Orchestrator  |
    | (cron per source)         |
    +------+------+-------------+
      |      |
      |      +--------------------------------------+
      |                                             |
      v                                             v
    +-------------+   +-------------+   +----------------------+
    | RSS Adapter |   | API Adapter |   | Scraper Adapter      |
    | primary/fb  |   | primary/fb  |   | primary/fb           |
    +------+------+   +------+------+   +----------+-----------+
      \              |                         /
       \             |                        /
        +------------+-----------------------+
           |
           v
    +---------------------------+
    | Raw Fetch Storage         |
    | + fetch_runs/attempts     |
    +-------------+-------------+
        |
        v
    +---------------------------+
    | Normalization             |
    | (canonical item schema)   |
    +-------------+-------------+
        |
        v
    +---------------------------+
    | Deduplication             |
    | (url/id/hash/similarity)  |
    +-------------+-------------+
        |
        v
    +---------------------------+
    | Enrichment (LLM adapters) |
    | - summary                 |
    | - tags                    |
    | - sentiment               |
    | - actors                  |
    +------+------+-------------+
      |      |
      |      +-----------------------------+
      v                                    v
    +-------------+                     +------------------+
    | PostgreSQL  |                     | OpenSearch       |
    | source of   |                     | search + filters |
    | truth       |                     +---------+--------+
    +------+------+                               |
      |                                      v
      |                           +------------------+
      +-------------------------->| Dashboard /      |
              | Executive View   |
              +---------+--------+
              |
              v
              +------------------+
              | Daily Briefing   |
              | Synthesis        |
              +------------------+

## 10) Canonical Data Model (Initial)
### entities
- id
- name
- type (person, institution, media, blog, government)
- country

### sources
- id
- name
- domain_type (think_tank, press, x, truth, blog)
- ingestion_mode (rss, api, scrape)
- config (JSON)
- polling_cron
- default_language
- active
- prompt_template_id (nullable)

### source_recipes
- id
- source_id
- primary_connector (rss, api, scrape)
- fallback_chain (array)
- request_policy (JSON: retries, timeout, rate_limit, backoff)
- parse_rules (JSON: selectors/transform rules)
- priority
- updated_by
- updated_at

### fetch_runs
- id
- source_id
- scheduled_at
- started_at
- completed_at
- status (success, partial, failed)
- connector_attempted (array)
- connector_used_final
- item_count_fetched
- item_count_new
- error_summary

### fetch_attempts
- id
- fetch_run_id
- connector_type
- attempt_number
- started_at
- completed_at
- status
- http_status
- error_message

### items
- id
- source_id
- external_id
- url
- title
- raw_content
- cleaned_content
- published_at
- fetched_at
- language
- content_hash

### enrichments
- id
- item_id
- summary
- tags (array)
- sentiment
- actors (array)
- model_provider
- model_name
- prompt_version
- processed_at

### briefings
- id
- briefing_date
- language
- scope_config (JSON)
- synthesis_markdown
- generated_at

### users
- id
- email
- role (admin, user)
- preferences (JSON)

### audit_logs
- id
- user_id
- action
- target_type
- target_id
- payload
- created_at

### dead_letters
- id
- source_id
- fetch_run_id
- stage (acquisition, normalization, enrichment)
- error_type
- error_payload
- created_at
- resolved_at (nullable)

## 11) Configuration Strategy
Configuration hierarchy:
1. System defaults
2. Source category defaults
3. Source-level settings
4. User-level dashboard preferences

Key configurable parameters:
- Polling frequency and cron schedule per source.
- Source activation.
- Prompt template assignment.
- Preferred summary language.
- Daily briefing generation time.

### 11.1 Configuration Files and Runtime Config
The project uses two config classes:
- Non-secret configuration (versioned in repository).
- Secret configuration (never committed, injected at runtime).

Recommended files:
- .env.example: documentation of required environment variables (no real secrets).
- infra/docker/.env.local: local development secrets (gitignored).
- apps/api/config/providers.yaml: non-secret provider routing defaults.
- apps/worker/config/pipeline.yaml: non-secret ingestion and processing defaults.

Repository reference files:
- .env.example
- docs/config/CREDENTIALS.md
- docs/config/credentials-store.example.json

Runtime principle:
- Secrets are read from environment variables or secret manager.
- Business configuration (sources, recipes, prompts) is stored in database and editable by admin UI.

### 11.2 LLM Configuration Model
LLM behavior should be configured in two layers.

Layer A: Secret keys and endpoints (runtime secrets)
- LLM_ANTHROPIC_API_KEY
- LLM_OPENAI_API_KEY
- LLM_MISTRAL_API_KEY
- Optional custom base URLs for enterprise endpoints

Layer B: Non-secret routing policy (config + DB)
- Default provider and model.
- Per-source provider/model override.
- Fallback provider chain.
- Token and cost budgets per pipeline stage.
- Timeout/retry policies.

### 11.3 Source Credentials (X and Restricted Sites)
Some sources require credentials or paid API access.

Credential policy:
- Never store raw credentials in source records.
- Store only a credential reference ID in DB.
- Resolve secrets at runtime from a secure store.

Examples:
- X API: key/secret/bearer token stored as runtime secret; source recipe references credential ID.
- Authenticated news sites: service account credentials stored as secret; avoid personal credentials.
- Cookie-based sessions: avoid if possible; if required, rotate and store securely with short TTL.

Database fields:
- sources.credential_ref (nullable)
- sources.auth_mode (none, api_key, oauth2, basic, cookie)

Admin UX behavior:
- Admin can attach/change a credential reference for a source.
- UI never displays raw secret values, only masked metadata.
- All credential-link changes are written to audit logs.

### 11.4 Secret Management by Environment
Local development:
- Docker Compose with local .env files (gitignored).

VPS production:
- Use a secret manager or encrypted environment injection.
- Rotate secrets regularly.
- Keep least-privilege credentials per connector/provider.

### 11.5 Run Modes (Dry Run, Sandbox, Live)
To prevent bans, rate-limit issues, and unwanted traffic during heavy test phases, the platform supports explicit run modes.

Run modes:
- dryrun
  - No external network calls.
  - Uses synthetic or fixture-based data.
  - Simulates ingestion, normalization, dedup, enrichment, and briefing generation.
  - Does not require real source credentials.
- sandbox
  - Limited real calls on a small allow-list of safe sources.
  - Strict low-frequency schedules and conservative rate limits.
- live
  - Full production behavior.

Dryrun goals:
- Validate end-to-end pipeline behavior without touching external providers.
- Load-test queues and dashboard logic safely.
- Test failure scenarios deterministically (timeouts, malformed payloads, provider errors).

Dryrun data strategy:
- Fixture packs by source domain (think tanks, press, blogs, etc.).
- Deterministic seed for reproducible test runs.
- Optional noise injection for duplicates, late arrivals, and content drift.

Safety guardrails:
- Default local mode should be `dryrun`.
- A global network kill-switch blocks outbound requests in dryrun.
- CI should run in dryrun by default.

## 12) Security and Governance Baseline
- RBAC enforced at API level.
- Signed auth tokens and refresh flow.
- Audit logs for admin changes.
- Secrets in environment variables or vault.
- Source access and scraper behavior rate-limited.
- Respect robots/legal constraints where applicable.
- Strict no-secrets-in-repo policy for all API keys and site credentials.
- Credential references in DB, secret values only in runtime secret store.
- Dryrun mode with outbound network disabled for safe testing at scale.

Current retention policy:
- Infinite retention for raw and processed data.

## 13) Roadmap (Full)
### Phase 0: Foundations
- Monorepo structure and CI baseline.
- Local Docker stack for dev.
- Core schema and migrations.

### Phase 1: MVP Ingestion + Executive Briefing
- Source registry with admin CRUD.
- RSS/API ingest and basic scraping fallback.
- Daily scheduler (default once per day).
- AI enrichment (summary, tags, sentiment, actors).
- Executive daily briefing page.

### Phase 2: Search and Intelligence UX
- OpenSearch indexing.
- Advanced filters and saved views.
- Source-level prompt tuning in admin UI.
- Better deduplication and clustering.

### Phase 3: Reliability and Scale
- Queue partitioning and worker scaling.
- Retry policies and dead-letter handling.
- Monitoring dashboards and alerting.
- Provider failover and cost controls.

### Phase 4: Strategic Intelligence Features
- Thematic synthesis packs.
- Trend analysis across time windows.
- Entity relationship mapping.
- Optional vector and semantic retrieval.

## 14) Proposed Repository Structure

```text
atlas/
  apps/
    api/                    # FastAPI service (auth, sources, search, briefings)
    worker/                 # Celery tasks: ingest, normalize, enrich, synthesize
    web/                    # Next.js dashboard and admin UI
  packages/
    shared-schema/          # Pydantic/TS schema contracts and OpenAPI artifacts
    prompts/                # Versioned prompt templates (global + per source)
    provider-adapters/      # LLM provider abstraction and adapters
  infra/
    docker/                 # Compose files and environment templates
    nginx/                  # Reverse proxy config (if used)
    monitoring/             # Prometheus/Grafana/Loki configs
  migrations/               # DB migrations
  docs/
    architecture/
    runbooks/
    product/
  MANIFEST.md
```

## 15) Local-to-VPS Deployment Path
1. Local development with Docker Compose:
   - PostgreSQL, Redis, OpenSearch, API, Worker, Web.
2. Staging on single VPS with same containers.
3. Production hardening:
   - TLS termination
   - Backups
   - Log shipping
   - Alerting

## 16) Definition of Success
- Admin can add a source in UI and set schedule without code.
- New content appears automatically in dashboard within expected polling windows.
- Daily executive briefing is generated reliably.
- Users can find relevant information quickly via filters and search.
- AI enrichments are traceable and adjustable via prompt settings.
- The platform provides, every day, a concise and trustworthy answer to "what is new today" across configured domains.

## 17) Non-Goals for Initial Build
- Real-time social firehose ingestion.
- Full data retention legal automation framework.
- Advanced analyst graph intelligence UI.

These can be addressed in later phases.

## 18) Configuration Bootstrap Artifacts
The repository includes initial templates for configuration and credentials handling:

- .env.example
  - Required runtime variables for API, worker, DB, Redis, OpenSearch, auth, and LLM providers.
  - Contains placeholders only, never real keys.

- docs/config/CREDENTIALS.md
  - Operational policy for credential references, auth modes, runtime secret resolution, and production controls.

- docs/config/credentials-store.example.json
  - Reference catalog format for credential references and secret variable mapping.
  - For documentation/bootstrap only, not a secret vault.

- docs/config/DRYRUN_FIXTURES.md
  - Fixture format specification for `RUN_MODE=dryrun`.
  - Defines deterministic test data and simulation settings.

- scripts/dryrun_runner.py
  - Local dryrun executor for end-to-end fixture-based simulation.
  - Produces generated briefing and run summary outputs.

- docs/runbooks/DRYRUN_RUNNER.md
  - Execution instructions for the dryrun runner.

- scripts/mock_api_server.py
  - Local HTTP mock API exposing dryrun briefing, summary, sources, and items.
  - Intended for frontend integration without external dependencies.

- docs/runbooks/MOCK_API.md
  - How to run and query the mock API endpoints.

- infra/docker/docker-compose.yml
  - Local/VPS baseline multi-service stack (api, worker, scheduler, postgres, redis).
  - Optional OpenSearch profile for search features.

- docs/runbooks/DOCKER_LOCAL.md
  - Startup, shutdown, health checks, and reset instructions for Docker Compose.

- Run mode variables in .env.example
  - `RUN_MODE` selects dryrun/sandbox/live behavior.
  - `DRYRUN_*` variables control fixtures, determinism, and fault simulation.
