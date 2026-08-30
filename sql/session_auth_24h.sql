-- =============================================================================
-- Prod DDL: 24h session/token authentication
-- Backend ERP - PostgreSQL
-- =============================================================================
-- Manual SQL to run on the production database (Neon SQL Editor or psql), NOT
-- via docker; both ddl.sql/dml.sql are dev-only reference. This feature reuses
-- the two tables DRF/Django already create (authtoken_token, django_session),
-- so there is no new table -- prod just needs the same FK + cleanup indexes.
--
-- Idempotent: safe to re-run. Apply AFTER the code is deployed.
--
-- Run: paste into the Neon SQL editor
-- =============================================================================

BEGIN;

-- -------------------------------------------------------------------------
-- 1) authtoken_token.user_id -> authentication_user.id
--    The original schema never declared this FK; DRF adds it on migrate only.
--    Match the Django model exactly (ON DELETE CASCADE).
-- -------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'authtoken_token_user_id_fkey'
          AND conrelid = 'public.authtoken_token'::regclass
    ) THEN
        ALTER TABLE public.authtoken_token
            ADD CONSTRAINT authtoken_token_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.authentication_user(id)
            ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

-- -------------------------------------------------------------------------
-- 2) Expiry-sweep indexes: the 24h cleanup filters on these columns.
-- -------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS authtoken_token_created_idx
    ON public.authtoken_token (created);
CREATE INDEX IF NOT EXISTS django_session_expire_date_idx
    ON public.django_session (expire_date);

COMMIT;