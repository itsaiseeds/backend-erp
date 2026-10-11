-- One-off SQL for the live DB (the repo has no migrations): rejected orders + LR delivery.
-- Purely additive for deployed code: made_from_waste stays; made_from_rejected is new
-- with a default, so running code keeps working while this is applied.
-- Run once, then: StockLedgerOperations.check_ledger() must return [].

BEGIN;

-- Rejected orders ------------------------------------------------------------
ALTER TABLE public.aggregator_customorder
	ADD COLUMN IF NOT EXISTS made_from_rejected bool NOT NULL DEFAULT false;

-- The old checks forbid a kg order that is not a waste order; relax them.
ALTER TABLE public.aggregator_customorder DROP CONSTRAINT IF EXISTS ck_customorder_waste_unit;
ALTER TABLE public.aggregator_customorder DROP CONSTRAINT IF EXISTS ck_customorder_hsn_waste_only;
ALTER TABLE public.aggregator_customorder DROP CONSTRAINT IF EXISTS ck_customorder_not_waste_and_rejected;
ALTER TABLE public.aggregator_customorder ADD CONSTRAINT ck_customorder_not_waste_and_rejected
	CHECK (NOT (made_from_waste AND made_from_rejected));
ALTER TABLE public.aggregator_customorder ADD CONSTRAINT ck_customorder_waste_unit CHECK (
	((made_from_waste OR made_from_rejected) AND unit_of_measure = 'kg')
	OR (NOT made_from_waste AND NOT made_from_rejected AND unit_of_measure = 'packet')
);
ALTER TABLE public.aggregator_customorder ADD CONSTRAINT ck_customorder_hsn_waste_only
	CHECK (made_from_waste OR made_from_rejected OR hsn_code = '');

ALTER TABLE public.aggregator_customorderitem
	ADD COLUMN IF NOT EXISTS inward_raw_material_id int8 NULL;
ALTER TABLE public.aggregator_customorderitem
	ADD CONSTRAINT aggregator_customorderitem_inward_raw_material_id_fk
	FOREIGN KEY (inward_raw_material_id) REFERENCES public.aggregator_inwardrawmaterial(id)
	ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public.aggregator_customorderitem
	ADD CONSTRAINT ck_customorderitem_lot_is_kg
	CHECK (inward_raw_material_id IS NULL OR quantity_kg IS NOT NULL);

-- Two lots of one product may share a rejected order; one lot only once.
DROP INDEX IF EXISTS public.uniq_customorderitem_order_product_kg;
CREATE UNIQUE INDEX uniq_customorderitem_order_product_kg ON public.aggregator_customorderitem
	USING btree (custom_order_id, product_id) WHERE packet_weight IS NULL AND inward_raw_material_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_customorderitem_order_lot ON public.aggregator_customorderitem
	USING btree (custom_order_id, inward_raw_material_id) WHERE inward_raw_material_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS aggregator_customorderitem_inward_raw_material_id_idx
	ON public.aggregator_customorderitem USING btree (inward_raw_material_id);

-- ... and so may two challan lines (kg lines are told apart by lot number).
DROP INDEX IF EXISTS public.uniq_dispatchentryitem_entry_product_kg;
CREATE UNIQUE INDEX uniq_dispatchentryitem_entry_product_kg ON public.aggregator_dispatchentryitem
	USING btree (dispatch_entry_id, product_id, lot_number) WHERE packet_weight IS NULL AND product_id IS NOT NULL;

-- LR => DELIVERED backfill ---------------------------------------------------
-- DISPATCHED agency orders that already have an LR number are delivered; no
-- notifications. DISPATCHED -> DELIVERED moves no stock-ledger figure.
UPDATE public.aggregator_order o
SET status_id = (SELECT id FROM public.aggregator_status WHERE code = 'DELIVERED'),
	actual_delivery_date = current_date,
	updated_at = now()
FROM public.aggregator_dispatchdetails d
WHERE o.dispatch_details_id = d.id
	AND d.lr_number <> ''
	AND o.is_deleted = false
	AND o.status_id = (SELECT id FROM public.aggregator_status WHERE code = 'DISPATCHED');

COMMIT;
