-- Phase D3: Row Level Security policies for Supabase
-- The FastAPI gateway uses the service role and bypasses RLS.
-- These policies protect direct client access if the table is exposed.
-- Do not apply to the Marketplace project.
--
-- On vanilla PostgreSQL (CI) the Supabase roles may not exist.
-- This migration creates them if missing so the policies can be applied.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role;
    END IF;
END
$$;

ALTER TABLE task_ownership ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS task_ownership_select_own ON task_ownership;
CREATE POLICY task_ownership_select_own
    ON task_ownership
    FOR SELECT
    TO authenticated
    USING (owner_id = current_setting('request.jwt.claim.sub', true));

DROP POLICY IF EXISTS task_ownership_service_all ON task_ownership;
CREATE POLICY task_ownership_service_all
    ON task_ownership
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
