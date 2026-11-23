-- 002_user_auth_and_rss_sources.sql

CREATE TABLE IF NOT EXISTS user_accounts (
  id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rss_sources (
  id BIGSERIAL PRIMARY KEY,
  category TEXT NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_rss_source_prefs (
  user_id BIGINT NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
  source_id BIGINT NOT NULL REFERENCES rss_sources(id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, source_id)
);

ALTER TABLE connector_runs
  ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES user_accounts(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_connector_runs_user_connector_time
  ON connector_runs(user_id, connector_name, run_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_rss_prefs_user_enabled
  ON user_rss_source_prefs(user_id, enabled);
