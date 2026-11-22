# Phase D3 — Free-tier Supabase integration notes

## Architecture (zero-cost)

- Supabase PostgreSQL: durable ownership + atomic rate-limit counters
- Supabase Auth: JWT issuer for the mobile client
- Supabase Storage: private buckets for materials and results
- FastAPI gateway: sole holder of the service-role key
- No Redis, no commercial object storage, no paid services

## Required environment variables (production)

- FOX_ENV=production
- FOX_OIDC_ISSUER (Supabase Auth issuer)
- FOX_OIDC_AUDIENCE
- FOX_OIDC_JWKS_URL
- DATABASE_URL (Supabase PostgreSQL connection string)
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY (server only; never in the mobile app)

## Migrations to apply after the dedicated FOX project is created

1. migrations/001_task_ownership.sql
2. migrations/002_rate_limit_counters.sql
3. migrations/003_rls_policies.sql

## Storage bucket setup

Create a private bucket named `fox-media`. Do not enable public access. The gateway uses the service role to upload and to generate short-lived signed URLs after ownership checks.

## Free-tier constraints

- 500 MB database
- 1 GB file storage
- 5 GB egress
- 50 MB max file upload
- Projects may pause after 7 days of inactivity

## Remaining provisioning steps

1. User confirms the Catch-app organization.
2. Create a new Supabase project dedicated to FOX (not Fox-marketplace).
3. Apply the three migrations.
4. Configure Supabase Auth.
5. Create the private `fox-media` bucket.
6. Set the environment variables on the FastAPI host.
7. Do not place the service-role key in the mobile application.
