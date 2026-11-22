-- Phase D3: Row Level Security policies for Supabase
-- The FastAPI gateway uses the service role and bypasses RLS.
-- These policies protect direct client access if the table is exposed.
-- Do not apply to the Marketplace project.

ALTER TABLE task_ownership ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_ownership_select_own
    ON task_ownership
    FOR SELECT
    TO authenticated
    USING (owner_id = auth.uid()::text);

CREATE POLICY task_ownership_service_all
    ON task_ownership
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON POLICY task_ownership_select_own ON task_ownership IS
    'Users may only read ownership records they own. Gateway uses service role.';
