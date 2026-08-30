-- =============================================================================
-- Prod DDL: Django admin performance indexes
-- Backend ERP - PostgreSQL
-- =============================================================================
-- For the managed production database (Neon / Supabase SQL editor or psql).
-- Idempotent: safe to re-run.
--
-- The FIRST statement below creates the pg_trgm extension (required before the
-- gin_trgm_ops indexes can exist). After that, the two GIN indexes back the
-- Django admin's ILIKE '%term%' search on the user directory (name/email);
-- without them those searches fall back to a full table scan as the table
-- grows. phone_number is already covered by its unique btree index.
--
-- If your SQL tool complains that the first line "cannot be run inside a
-- transaction block", run just that one line first, then re-run this file.
--
-- Note on login speed: settings.PASSWORD_HASHERS now prefers Argon2, which
-- verifies ~5-10x faster than the PBKDF2 hashes seeded so far. Existing
-- password hashes only move to Argon2 on the next password set/reset, so reset
-- the admin password (or use the "Set password" button) once after deploying.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS authentication_user_name_trgm_idx
    ON public.authentication_user USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS authentication_user_email_trgm_idx
    ON public.authentication_user USING gin (email gin_trgm_ops);