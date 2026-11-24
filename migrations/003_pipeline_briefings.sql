-- Persistent canonical pipeline and refreshable daily briefings.

ALTER TABLE items
  ADD COLUMN IF NOT EXISTS item_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_items_item_key
  ON items(item_key)
  WHERE item_key IS NOT NULL;

ALTER TABLE enrichments
  DROP COLUMN IF EXISTS sentiment;

CREATE TABLE IF NOT EXISTS pipeline_runs (
  id BIGSERIAL PRIMARY KEY,
  run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  run_mode TEXT NOT NULL,
  connector_name TEXT NOT NULL,
  user_id BIGINT REFERENCES user_accounts(id) ON DELETE SET NULL,
  items_fetched INTEGER NOT NULL DEFAULT 0,
  items_new INTEGER NOT NULL DEFAULT 0,
  items_updated INTEGER NOT NULL DEFAULT 0,
  errors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  briefing_id BIGINT REFERENCES briefings(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_time
  ON pipeline_runs(run_at DESC);

ALTER TABLE briefings
  ADD COLUMN IF NOT EXISTS update_count INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
