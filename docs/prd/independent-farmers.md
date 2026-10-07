# PRD — Independent farmers and `is_lead`

Status: implemented
Date: 2026-10-07

## 1. Why

A farmer existed only as a `FarmerVisit`: a row tied to a field trip. A sales person could not
record a farmer they met outside a trip, and there was no way to mark a farmer as a sales lead.

## 2. Rules

- `FarmerVisit.field_trip` is now nullable. A row with no trip is an **independent farmer**
  (`FarmerVisit.is_independent`) owned by `created_by`. No new table: the farmer list, export and
  crop / product links all keep working.
- `FarmerVisit.is_lead` (bool, default `false`) on every farmer, trip visit or independent.
  Accepted by `create-farmer-visit` and `edit-farmer-visit`, returned in every farmer payload.
- An independent farmer's `contact_number` is unique per sales person among live rows
  (`uniq_farmervisit_independent_contact`); a deleted one frees the number. Trip visits keep
  `uniq_farmervisit_trip_contact`.
- `village` is required for an independent farmer (there is no trip to default from). At least one
  crop; products optional (none = does not use our products).
- Independent farmers are editable at any time (no trip status guard). Delete is a soft delete.
- Only the owner reaches them: another sales person's farmer, or a trip visit, is a 404.

## 3. API (Android, sales-person token)

| Method | Path | Notes |
|---|---|---|
| GET | `farmers` | own independent farmers, paginated (`?all=true`); filters `public_id`, `contact_number`, `farmer_name`, `village`, `is_lead`, `uses_our_products`; sorts `created_at`, `land_area`, `farmer_name` |
| POST | `farmers` | body below; 201 with the farmer |
| GET / PATCH / DELETE | `farmer/<FV-…>` | detail / partial edit / soft delete (204) |

```json
{
  "farmer_name": "Ramesh Patel",
  "contact_number": "9876500101",
  "village": "Kamrej",
  "land_area_bigha": "2.5000",
  "is_lead": false,
  "crop_ids": [1],
  "product_public_ids": ["P-…"]
}
```

PATCH takes any subset of the same fields (`farmer_name`, `contact_number`, `village`,
`land_area_bigha`, `is_lead`, `crop_ids`, `product_public_ids`).

Farmer payload gains `is_lead` and `field_trip_public_id` (null for an independent farmer).
Sales-admin `farmers/` gains `is_lead` (and an `is_lead` filter) and `city` is null for a farmer
without a trip; `export/farmer-visits` has `field_trip: null` for them.

## 4. Schema

`sql/ddl.sql` is updated. Existing databases:

```sql
ALTER TABLE public.aggregator_farmervisit ALTER COLUMN field_trip_id DROP NOT NULL;
ALTER TABLE public.aggregator_farmervisit ADD COLUMN IF NOT EXISTS is_lead bool NOT NULL DEFAULT false;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_farmervisit_independent_contact
  ON public.aggregator_farmervisit USING btree (created_by_id, contact_number)
  WHERE field_trip_id IS NULL AND is_deleted = false;
```

No new content types or permissions: the model already exists.

## 5. Tests

`tests/android/test_independent_farmers.py`; route gating in `tests/test_view_contracts.py`.
