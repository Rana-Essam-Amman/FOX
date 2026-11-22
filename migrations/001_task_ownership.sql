-- Phase D2: durable task ownership
-- Compatible with PostgreSQL 14+ and Supabase (PostgreSQL 15+).
-- Do not apply to the Marketplace project.

CREATE TABLE IF NOT EXISTS task_ownership (
    task_id     TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    kind        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB NOT NULL DEFAULT '{}',
    CONSTRAINT task_ownership_task_id_unique UNIQUE (task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_ownership_owner_created
    ON task_ownership (owner_id, created_at DESC);

COMMENT ON TABLE task_ownership IS
    'Immutable ownership records for FOX tasks and materials. '
    'owner_id is derived from a verified JWT sub claim and must never be supplied by the client.';
