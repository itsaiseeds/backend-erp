-- =============================================================================
-- Prod DDL: product stage + image, drop buying price
-- Backend ERP - PostgreSQL (Neon)
-- =============================================================================
-- Applied MANUALLY, per the project's "no migrations" rule. Run the whole file
-- against EACH deployed database (prod and preprod) -- they are separate
-- databases and both need it.
--
-- This is a BREAKING change, so it is split in two:
--
--   STEP 1  additive only, safe to run BEFORE the code deploy. Old code keeps
--           working: stage_id and image_url both get defaults, so inserts that
--           do not mention them still succeed.
--   STEP 2  run AFTER the new code is live on that environment. Drops the
--           defaults and the buying_price column, which old code still writes.
--
-- Every statement is idempotent -- re-running the file is a no-op.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- STEP 0 - pre-flight (read-only; run first and eyeball the output)
-- -----------------------------------------------------------------------------
SELECT to_regclass('public.aggregator_stage') AS stage_table_exists;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'aggregator_product'
ORDER BY ordinal_position;

SELECT count(*) AS products_to_backfill FROM public.aggregator_product;


-- =============================================================================
-- STEP 1 - additive. Safe to run before the code deploy.
-- =============================================================================
BEGIN;

-- 1a. The stage lookup table (mirrors aggregator_status) -----------------------
CREATE TABLE IF NOT EXISTS public.aggregator_stage (
	id bigserial NOT NULL,
	created_at timestamptz NOT NULL,
	updated_at timestamptz NOT NULL,
	is_deleted bool NOT NULL DEFAULT false,
	deleted_at timestamptz NULL,
	deleted_by_id int8 NULL,
	created_by_id int8 NULL,
	code varchar(32) NOT NULL,
	"name" varchar(64) NOT NULL,
	sequence int2 NOT NULL DEFAULT 0,
	CONSTRAINT aggregator_stage_pkey PRIMARY KEY (id),
	CONSTRAINT aggregator_stage_code_key UNIQUE (code),
	CONSTRAINT aggregator_stage_sequence_check CHECK (sequence >= 0)
);

CREATE INDEX IF NOT EXISTS aggregator_stage_code_like ON public.aggregator_stage USING btree (code varchar_pattern_ops);
CREATE INDEX IF NOT EXISTS aggregator_stage_is_deleted_idx ON public.aggregator_stage USING btree (is_deleted);
CREATE INDEX IF NOT EXISTS aggregator_stage_created_by_id_idx ON public.aggregator_stage USING btree (created_by_id);
CREATE INDEX IF NOT EXISTS aggregator_stage_deleted_by_id_idx ON public.aggregator_stage USING btree (deleted_by_id);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1 FROM pg_constraint WHERE conname = 'aggregator_stage_created_by_id_fk'
	) THEN
		ALTER TABLE public.aggregator_stage
			ADD CONSTRAINT aggregator_stage_created_by_id_fk
			FOREIGN KEY (created_by_id) REFERENCES public.authentication_user(id)
			ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
	END IF;
	IF NOT EXISTS (
		SELECT 1 FROM pg_constraint WHERE conname = 'aggregator_stage_deleted_by_id_fk'
	) THEN
		ALTER TABLE public.aggregator_stage
			ADD CONSTRAINT aggregator_stage_deleted_by_id_fk
			FOREIGN KEY (deleted_by_id) REFERENCES public.authentication_user(id)
			ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
	END IF;
END $$;

-- 1b. The four fixed stage rows ------------------------------------------------
-- ids MUST match aggregator/models/Stage.py::StageIds -- that enum is the
-- single source of truth for the CODE -> id mapping and there are no migrations
-- to keep them aligned.
INSERT INTO public.aggregator_stage
	(id, created_at, updated_at, is_deleted, deleted_at, deleted_by_id, created_by_id, code, "name", "sequence")
VALUES
	(1, '2026-08-28 05:22:53.878+00', '2026-08-28 05:22:53.878+00', false, NULL, NULL, NULL, 'BREEDER',     'Breeder',     1),
	(2, '2026-08-28 05:22:53.878+00', '2026-08-28 05:22:53.878+00', false, NULL, NULL, NULL, 'FOUNDATION',  'Foundation',  2),
	(3, '2026-08-28 05:22:53.878+00', '2026-08-28 05:22:53.878+00', false, NULL, NULL, NULL, 'RESEARCH',    'Research',    3),
	(4, '2026-08-28 05:22:53.878+00', '2026-08-28 05:22:53.878+00', false, NULL, NULL, NULL, 'CERTIFICATE', 'Certificate', 4)
ON CONFLICT (id) DO NOTHING;

-- Explicit ids do not advance the sequence; re-sync it so an ORM-created row
-- does not collide from id=1.
SELECT setval(pg_get_serial_sequence('public.aggregator_stage', 'id'),
              (SELECT MAX(id) FROM public.aggregator_stage));

-- 1c. aggregator_product: stage_id and image_url -------------------------------
-- DEFAULT 1 (BREEDER) is what lets the currently-deployed code keep inserting
-- products; STEP 2 removes it once the new code is live.
ALTER TABLE public.aggregator_product
	ADD COLUMN IF NOT EXISTS stage_id int8 NOT NULL DEFAULT 1;

ALTER TABLE public.aggregator_product
	ADD COLUMN IF NOT EXISTS image_url varchar(500) NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS aggregator_product_stage_id_idx
	ON public.aggregator_product USING btree (stage_id);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1 FROM pg_constraint WHERE conname = 'aggregator_product_stage_id_fk'
	) THEN
		ALTER TABLE public.aggregator_product
			ADD CONSTRAINT aggregator_product_stage_id_fk
			FOREIGN KEY (stage_id) REFERENCES public.aggregator_stage(id)
			ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
	END IF;
END $$;

-- 1d. Django admin plumbing for the new model ----------------------------------
-- Ids come from the sequences rather than being hardcoded: sql/dml.sql pins 37
-- and 125-128 for a from-scratch local reload, but a live database may already
-- have those taken. The (app_label, model) and (content_type_id, codename)
-- unique keys are what actually matter to Django.
INSERT INTO public.django_content_type (app_label, model)
VALUES ('aggregator', 'stage')
ON CONFLICT (app_label, model) DO NOTHING;

INSERT INTO public.auth_permission ("name", content_type_id, codename)
SELECT p.name, ct.id, p.codename
FROM (VALUES
		('Can add stage',    'add_stage'),
		('Can change stage', 'change_stage'),
		('Can delete stage', 'delete_stage'),
		('Can view stage',   'view_stage')
	) AS p(name, codename)
CROSS JOIN (
	SELECT id FROM public.django_content_type
	WHERE app_label = 'aggregator' AND model = 'stage'
) AS ct
ON CONFLICT (content_type_id, codename) DO NOTHING;

COMMIT;


-- =============================================================================
-- STEP 2 - destructive. Run ONLY after the new code is live on this environment.
-- =============================================================================
BEGIN;

-- 2a. The app always supplies stage now; drop the migration crutch.
ALTER TABLE public.aggregator_product ALTER COLUMN stage_id DROP DEFAULT;

-- 2b. Narrow the price check, then drop the column it referenced.
--     (Dropping the column would take the whole constraint with it, including
--     the selling_price half, so replace it explicitly first.)
ALTER TABLE public.aggregator_product
	DROP CONSTRAINT IF EXISTS ck_product_prices_non_negative;

ALTER TABLE public.aggregator_product
	ADD CONSTRAINT ck_product_prices_non_negative CHECK (selling_price >= 0);

ALTER TABLE public.aggregator_product DROP COLUMN IF EXISTS buying_price;

COMMIT;


-- =============================================================================
-- STEP 3 - verification (read-only)
-- =============================================================================
-- Expect: 4 rows, ids 1-4, BREEDER/FOUNDATION/RESEARCH/CERTIFICATE.
SELECT id, code, "name", sequence FROM public.aggregator_stage ORDER BY id;

-- Expect: stage_id NOT NULL with no default, image_url NOT NULL default '',
--         and NO buying_price row.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'aggregator_product'
ORDER BY ordinal_position;

-- Expect: ck_product_prices_non_negative mentioning only selling_price.
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.aggregator_product'::regclass
ORDER BY conname;

-- Expect: 0 -- every product points at a real stage.
SELECT count(*) AS orphaned_products
FROM public.aggregator_product p
LEFT JOIN public.aggregator_stage s ON s.id = p.stage_id
WHERE s.id IS NULL;

-- Expect: 4 permission rows.
SELECT p.id, p.codename
FROM public.auth_permission p
JOIN public.django_content_type ct ON ct.id = p.content_type_id
WHERE ct.app_label = 'aggregator' AND ct.model = 'stage'
ORDER BY p.id;
