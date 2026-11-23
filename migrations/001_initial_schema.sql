-- 001_initial_schema.sql
-- Initial schema for Atlas intelligence platform.

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
  preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entities (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  country TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (name, type)
);

CREATE TABLE IF NOT EXISTS prompt_templates (
  id BIGSERIAL PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  version TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sources (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  domain_type TEXT NOT NULL,
  ingestion_mode TEXT NOT NULL CHECK (ingestion_mode IN ('rss', 'api', 'scrape')),
  auth_mode TEXT NOT NULL DEFAULT 'none' CHECK (auth_mode IN ('none', 'api_key', 'oauth2', 'basic', 'cookie')),
  credential_ref TEXT,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  polling_cron TEXT NOT NULL DEFAULT '0 6 * * *',
  default_language TEXT NOT NULL DEFAULT 'fr',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  prompt_template_id BIGINT REFERENCES prompt_templates(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS source_recipes (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  primary_connector TEXT NOT NULL,
  fallback_chain JSONB NOT NULL DEFAULT '[]'::jsonb,
  request_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  parse_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
  priority INTEGER NOT NULL DEFAULT 100,
  updated_by BIGINT REFERENCES users(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id)
);

CREATE TABLE IF NOT EXISTS items (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
  external_id TEXT,
  url TEXT NOT NULL,
  title TEXT,
  raw_content TEXT,
  cleaned_content TEXT,
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  language TEXT,
  content_hash TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (url),
  UNIQUE (source_id, external_id)
);

CREATE TABLE IF NOT EXISTS enrichments (
  id BIGSERIAL PRIMARY KEY,
  item_id BIGINT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  summary TEXT,
  tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  sentiment TEXT,
  actors JSONB NOT NULL DEFAULT '[]'::jsonb,
  model_provider TEXT,
  model_name TEXT,
  prompt_version TEXT,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (item_id)
);

CREATE TABLE IF NOT EXISTS briefings (
  id BIGSERIAL PRIMARY KEY,
  briefing_date DATE NOT NULL,
  language TEXT NOT NULL DEFAULT 'fr',
  scope_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  synthesis_markdown TEXT NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (briefing_date, language)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fetch_runs (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
  scheduled_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  connector_attempted JSONB NOT NULL DEFAULT '[]'::jsonb,
  connector_used_final TEXT,
  item_count_fetched INTEGER NOT NULL DEFAULT 0,
  item_count_new INTEGER NOT NULL DEFAULT 0,
  error_summary TEXT
);

CREATE TABLE IF NOT EXISTS fetch_attempts (
  id BIGSERIAL PRIMARY KEY,
  fetch_run_id BIGINT NOT NULL REFERENCES fetch_runs(id) ON DELETE CASCADE,
  connector_type TEXT NOT NULL,
  attempt_number INTEGER NOT NULL,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  http_status INTEGER,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS dead_letters (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
  fetch_run_id BIGINT REFERENCES fetch_runs(id) ON DELETE SET NULL,
  stage TEXT NOT NULL,
  error_type TEXT,
  error_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

-- Connector execution store used by current API endpoints.
CREATE TABLE IF NOT EXISTS connector_runs (
  id BIGSERIAL PRIMARY KEY,
  connector_name TEXT NOT NULL,
  mode TEXT NOT NULL,
  run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  items_count INTEGER NOT NULL DEFAULT 0,
  errors_count INTEGER NOT NULL DEFAULT 0,
  errors_json JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS connector_items (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES connector_runs(id) ON DELETE CASCADE,
  connector_name TEXT NOT NULL,
  source TEXT,
  source_url TEXT,
  title TEXT,
  url TEXT,
  published_at TEXT,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_connector_runs_name_time
  ON connector_runs(connector_name, run_at DESC);

CREATE INDEX IF NOT EXISTS idx_connector_items_run_id
  ON connector_items(run_id);

CREATE INDEX IF NOT EXISTS idx_items_source_published
  ON items(source_id, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_items_hash
  ON items(content_hash);

CREATE INDEX IF NOT EXISTS idx_fetch_runs_source_time
  ON fetch_runs(source_id, started_at DESC);
