-- SCRUM-67: record *when* each stock count line was taken (counted_at).
--
-- Production (Neon) is manual SQL only -- see README "Database & schema
-- management". Run in two steps around the deploy.
--
-- STEP 1 -- apply BEFORE deploying the code that reads counted_at.
--   Existing rows are backfilled to 2026-09-27 09:00 IST. The temporary
--   DEFAULT now() keeps the old code's inserts (which do not send the column)
--   working until the new code is live.

BEGIN;

ALTER TABLE public.aggregator_inventorysnapshot ADD COLUMN counted_at timestamptz NULL;
UPDATE public.aggregator_inventorysnapshot
   SET counted_at = TIMESTAMPTZ '2026-09-27 09:00:00+05:30'
 WHERE counted_at IS NULL;
ALTER TABLE public.aggregator_inventorysnapshot
    ALTER COLUMN counted_at SET DEFAULT now(),
    ALTER COLUMN counted_at SET NOT NULL;

ALTER TABLE public.aggregator_loosestocksnapshot ADD COLUMN counted_at timestamptz NULL;
UPDATE public.aggregator_loosestocksnapshot
   SET counted_at = TIMESTAMPTZ '2026-09-27 09:00:00+05:30'
 WHERE counted_at IS NULL;
ALTER TABLE public.aggregator_loosestocksnapshot
    ALTER COLUMN counted_at SET DEFAULT now(),
    ALTER COLUMN counted_at SET NOT NULL;

COMMIT;

-- STEP 2 -- apply AFTER the code is deployed, to match sql/ddl.sql (the
--   application always writes counted_at itself).
--
-- ALTER TABLE public.aggregator_inventorysnapshot ALTER COLUMN counted_at DROP DEFAULT;
-- ALTER TABLE public.aggregator_loosestocksnapshot ALTER COLUMN counted_at DROP DEFAULT;
