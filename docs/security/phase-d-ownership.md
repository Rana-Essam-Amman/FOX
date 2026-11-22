# Phase D — Production ownership persistence

The gateway currently uses an in-memory `TaskOwnershipStore` for tests and single-process development. **This is not production-safe.**

## Required production schema (Postgres or SQLite)

```sql
CREATE TABLE task_ownership (
    task_id     TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    kind        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB NOT NULL DEFAULT '{}',
    UNIQUE (task_id)
);

CREATE INDEX idx_task_ownership_owner ON task_ownership (owner_id, created_at DESC);
```

## Configuration required before production

- `FOX_OIDC_ISSUER`
- `FOX_OIDC_AUDIENCE`
- `FOX_OIDC_JWKS_URL`

If any are missing, protected endpoints return 503 and authentication fails closed.

## Remaining blockers

- No durable multi-worker ownership store is configured.
- Rate limiting is process-local.
- Upload storage is local filesystem.
- Do not deploy until a durable ownership adapter is installed and tested.
