-- Per-dispatch delivery_to ("To" printed on the delivery challan).
--
-- Run once against a live database that predates the column. A fresh database
-- built from ddl.sql already has it and does not need this script. Safe to
-- re-run: the ALTERs are IF NOT EXISTS and the backfills only touch NULL rows.
--
-- Existing challans are backfilled with what they printed before the field
-- existed: the booked-for party's address delivery_to, else the order's own
-- delivery address delivery_to.
BEGIN;

ALTER TABLE public.aggregator_dispatchdetails        ADD COLUMN IF NOT EXISTS delivery_to varchar(255) NULL;
ALTER TABLE public.aggregator_privatedispatchdetails ADD COLUMN IF NOT EXISTS delivery_to varchar(255) NULL;
ALTER TABLE public.aggregator_dispatchentry          ADD COLUMN IF NOT EXISTS delivery_to varchar(255) NULL;

-- Challans of packaged orders.
UPDATE public.aggregator_dispatchentry de
SET delivery_to = COALESCE(bfa.delivery_to, da.delivery_to)
FROM public.aggregator_order o
JOIN public.aggregator_address da ON da.id = o.delivery_address_id
LEFT JOIN public.aggregator_clientchildorg bf ON bf.id = o.booked_for_id
LEFT JOIN public.aggregator_address bfa ON bfa.id = bf.address_id
WHERE de.order_id = o.id AND de.delivery_to IS NULL;

-- Challans of custom, waste and rejected orders.
UPDATE public.aggregator_dispatchentry de
SET delivery_to = COALESCE(bfa.delivery_to, da.delivery_to)
FROM public.aggregator_customorder co
JOIN public.aggregator_address da ON da.id = co.delivery_address_id
LEFT JOIN public.aggregator_clientchildorg bf ON bf.id = co.booked_for_id
LEFT JOIN public.aggregator_address bfa ON bfa.id = bf.address_id
WHERE de.custom_order_id = co.id AND de.delivery_to IS NULL;

-- Mirror the value onto the dispatch rows the entries point at.
UPDATE public.aggregator_dispatchdetails d
SET delivery_to = de.delivery_to
FROM public.aggregator_dispatchentry de
WHERE de.dispatch_details_id = d.id AND d.delivery_to IS NULL;

UPDATE public.aggregator_privatedispatchdetails p
SET delivery_to = de.delivery_to
FROM public.aggregator_dispatchentry de
JOIN public.aggregator_order o ON o.id = de.order_id
WHERE o.private_dispatch_details_id = p.id AND p.delivery_to IS NULL;

UPDATE public.aggregator_privatedispatchdetails p
SET delivery_to = de.delivery_to
FROM public.aggregator_dispatchentry de
JOIN public.aggregator_customorder co ON co.id = de.custom_order_id
WHERE co.private_dispatch_details_id = p.id AND p.delivery_to IS NULL;

COMMIT;
