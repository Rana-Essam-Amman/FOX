-- Phase D3: PostgreSQL-based distributed rate limiting
-- Compatible with Supabase Free (PostgreSQL).
-- Atomic counters via UPDATE ... RETURNING inside a transaction.
-- Do not apply to the Marketplace project.

CREATE TABLE IF NOT EXISTS rate_limit_counters (
    key         TEXT PRIMARY KEY,
    count       INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_expires
    ON rate_limit_counters (expires_at);

CREATE OR REPLACE FUNCTION cleanup_expired_rate_limits()
RETURNS void
LANGUAGE sql
AS $$
    DELETE FROM rate_limit_counters WHERE expires_at < NOW();
$$;
