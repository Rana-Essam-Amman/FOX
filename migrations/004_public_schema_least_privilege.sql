-- Phase D4: deny-by-default access for FOX's internal database objects.
-- The FastAPI backend connects with trusted server credentials. Browser/mobile
-- clients must not access ownership or rate-limit internals through the Data API.
-- Explicit grants below preserve the service_role path when it is used.

REVOKE ALL PRIVILEGES
    ON TABLE public.task_ownership, public.rate_limit_counters
    FROM anon, authenticated, service_role;

REVOKE ALL PRIVILEGES
    ON ALL SEQUENCES IN SCHEMA public
    FROM anon, authenticated, service_role;

REVOKE EXECUTE
    ON ALL FUNCTIONS IN SCHEMA public
    FROM PUBLIC, anon, authenticated, service_role;

GRANT ALL PRIVILEGES
    ON TABLE public.task_ownership, public.rate_limit_counters
    TO service_role;

GRANT EXECUTE
    ON FUNCTION public.cleanup_expired_rate_limits()
    TO service_role;

-- Supabase's project defaults may grant newly created public objects to
-- anon/authenticated. Revoke those defaults for the migration owner so future
-- internal tables/functions remain inaccessible until explicitly granted.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;
