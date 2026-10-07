# PRD — Lab tester role and lab testing

Status: implemented
Date: 2026-10-07

## 1. Why

An inward raw-material lot is booked in `Lab Testing` and held back from stock until
someone decides it is usable. Until now that "someone" was any admin or godown manager
flipping the lot's status by hand. The decision belongs to the person who actually runs
the grow-out test, and the test's figures should be on record next to the lot.

## 2. Goals

1. A third Android role, `LabTester`, a peer of `SalesPerson` and `GodownManager`.
2. A `LabTesting` record per lot: number of plants, female count, OT, comment,
   and the tester's own **Pass / Fail** verdict.
3. The verdict is what moves the lot: **Pass -> In Use**, **Fail -> Rejected**, stamping
   `effective_date` with today exactly as the old manual flip did.
4. Admins can only **revert** a lot to `Lab Testing`; godown managers cannot touch status.
5. Lab testers are told when a lot needs testing.
6. Read endpoints for both clients (Android and sales-admin), including one test in detail.

Rule of thumb for every guard below: **no figure may go negative; an action that would
make one negative is refused (400).**

## 3. Rules

### 3.1 Role and identity

- `LabTester` is a 1:1 profile on `User` with no location, a copy of `GodownManager`.
  Losing it revokes the user's credentials. Only a superuser or an `Admin` may create one.
- `User.is_lab_tester`; `User.role` is `"lab_tester"` (after `godown_manager` in precedence).
- Android login accepts a live lab tester and returns `is_lab_tester`; web login and
  reauthenticate return `can_create_lab_tester`.

### 3.2 The record (`LabTesting`, `LT-…`)

| Field | Type | Rule |
|---|---|---|
| `number_of_plants` | int | `> 0` |
| `female_count` | int | `>= 0` |
| `ot_count` | int | `>= 0` |
| `result` | `Pass` / `Fail` / null | entered by the tester, **independent of the counts**; null while the lot awaits a (re-)test |
| `comment` | text | optional |
| `tested_by`, `tested_at` | user, timestamp | whoever last submitted or edited |

`female_count + ot_count <= number_of_plants` (DB `CHECK` and serializer), so impurity
never exceeds 100% and the grow-out test never goes negative. Computed on read, never stored,
rounded half-up to two decimals:

```
genetical_impurity = (female_count + ot_count) / number_of_plants * 100
grow_out_test      = 100 - genetical_impurity
```

`InwardRawMaterial.lab_testing` is a nullable **one-to-one** FK. A lot has at most one test:
after an admin sends a lot back, the re-test **updates the same row** (same `LT-…` id), and
the revert keeps the inputs and only empties `result`. A lot booked by an accepted return
goes straight to `In Use`, never has a test, and is refused by `refuse_return_lot_change`.

### 3.3 The verdict moves the lot

`LabTestingOperations` is the only writer, and every move goes through
`InwardOperations.update_raw_lot`, so the stock ledger, the usability guard and the raw-pool
locks apply exactly once.

- **Submit** (`POST lab/lab-testings`): the lot must be in `Lab Testing`. Creates or updates the
  record, then Pass -> `In Use` / Fail -> `Rejected`, `effective_date = today`.
- **Edit** (`PATCH lab/lab-testing/<id>`): inputs are always editable. Changing `result`
  flips the lot `In Use <-> Rejected`:
  - **Pass -> Fail** takes the lot's kilograms out of the usable pool and is refused
    (`assert_raw_lot_removable`) when bags or sample packets are already packed from them. Orders
    reserve those bags, so the same check covers orders.
  - **Fail -> Pass** only adds kilograms and is always allowed.
  - On a lot awaiting re-test, the first `result` sent *is* the re-test.

### 3.4 Who may change a lot's status

| Actor | Allowed |
|---|---|
| Lab tester | the verdict (3.3) |
| Admin | `PATCH inward-raw-material/<id>` with `status`: **only** `In Use -> Lab Testing` and `Rejected -> Lab Testing` (`ALLOWED_RAW_STATUS_TRANSITIONS`). A revert of an `In Use` lot whose kilograms are packed stays refused. Moving a lot *out of* `Lab Testing` is a 400. |
| Godown manager | nothing: `PATCH` accepts no fields (`status` / `lab_sampling_date` are a 400). Booking and deleting lots are unchanged. |

### 3.5 Notifications

Event `LAB_TEST_REQUESTED` ("Lab test requested", screen `lab_test_pending`) goes to **every
live lab tester** (inbox row + push) when a lot enters `Lab Testing`: on booking
(`create_raw_lot`, admin and godown) and when an admin sends a lot back (`update_raw_lot`). It runs
through `fire_and_forget`: after commit, off the request thread, and a failure never breaks the
booking. `NotificationOperations.Message` now carries `recipient_ids`.

## 4. API

### Android (`AndroidLabTesterBaseView`, lab-tester token only, under `/android/api/v1/lab/`)

| Method | Path | Notes |
|---|---|---|
| GET | `lab/pending-lots` | lots in `Lab Testing`, oldest first; a lot sent back carries its earlier `lab_testing` |
| GET / POST | `lab/lab-testings` | list (filters `public_id`, `product`, `result`, `lot_status`; sorts `tested_at`, `product`) / submit a verdict |
| GET / PATCH | `lab/lab-testing/<LT-…>` | detail / edit |

`devices/register`, `notifications*` and `auth/*` are open to every Android role
(`AndroidSharedView`) so a lab tester receives push.

### Sales-admin (`admin_required`)

| Method | Path | Notes |
|---|---|---|
| GET | `lab-testings` | same list shape and filters |
| GET | `lab-testing/<LT-…>` | detail |
| GET / POST, PATCH / DELETE, POST | `lab-testers`, `lab-testers/<id>`, `lab-testers/<id>/rotate-qr` | account management, a copy of the godown-manager endpoints |

Every raw-lot payload gains `lab_testing: {public_id, result, grow_out_test} | null`.

## 5. Schema

`sql/ddl.sql`: `authentication_labtester`, `aggregator_labtesting` (CHECKs for the rules in 3.2),
and `aggregator_inwardrawmaterial.lab_testing_id` (unique, FK `RESTRICT`).
`sql/dml.sql`: content types 61-62 and permissions 206-213, chosen to follow prod's current
maximums (content type 60 `nonstockinward`, permission 205), a seed lab tester (user 7, phone
`4545454545`). `sql/delete_data.sql` wipes lab tests with the lots.

Existing databases (a reload drops the database, so run this by hand on prod / preprod):

```sql
CREATE TABLE public.authentication_labtester ( ...as in ddl.sql... );
CREATE TABLE IF NOT EXISTS public.aggregator_labtesting ( ...as in ddl.sql... );
ALTER TABLE public.aggregator_inwardrawmaterial ADD COLUMN IF NOT EXISTS lab_testing_id int8 NULL;
ALTER TABLE public.aggregator_inwardrawmaterial
  ADD CONSTRAINT aggregator_inwardrawmaterial_lab_testing_id_key UNIQUE (lab_testing_id);
ALTER TABLE public.aggregator_inwardrawmaterial
  ADD CONSTRAINT aggregator_inwardrawmaterial_lab_testing_id_fk FOREIGN KEY (lab_testing_id)
  REFERENCES public.aggregator_labtesting(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
```

Lots already `In Use` / `Rejected` keep `lab_testing_id = NULL`: they were decided before this
role existed, and a lab tester can only test a lot in `Lab Testing`.

## 6. Tests

- `tests/test_lab_testing_operations.py`: computed figures, both verdicts, validation, revert and
  re-test on the same row, the packed-stock guard (Pass -> Fail), notifications.
- `tests/android/test_lab_tester.py`: login, queue, submit / edit, role gating on every route,
  godown and admin restrictions, admin list / detail, lab-tester account management.

Content types and permissions on prod (ids match `sql/dml.sql`; idempotent):

```sql
INSERT INTO public.django_content_type (id, app_label, model) VALUES
  (61, 'authentication', 'labtester'),
  (62, 'aggregator', 'labtesting')
ON CONFLICT DO NOTHING;

INSERT INTO public.auth_permission (id, "name", content_type_id, codename) VALUES
  (206, 'Can add lab tester',       61, 'add_labtester'),
  (207, 'Can change lab tester',    61, 'change_labtester'),
  (208, 'Can delete lab tester',    61, 'delete_labtester'),
  (209, 'Can view lab tester',      61, 'view_labtester'),
  (210, 'Can add lab testing',      62, 'add_labtesting'),
  (211, 'Can change lab testing',   62, 'change_labtesting'),
  (212, 'Can delete lab testing',   62, 'delete_labtesting'),
  (213, 'Can view lab testing',     62, 'view_labtesting')
ON CONFLICT DO NOTHING;

SELECT setval(pg_get_serial_sequence('public.django_content_type', 'id'),
              (SELECT MAX(id) FROM public.django_content_type));
SELECT setval(pg_get_serial_sequence('public.auth_permission', 'id'),
              (SELECT MAX(id) FROM public.auth_permission));
```

## 7. Change: no sowing date

The lab test no longer records a sowing date: `sowing_date` is gone from `LabTesting`, every
request and response, the `sowing_date` sort, the Django admin and `sql/ddl.sql`. The lot's
quantity is already in each lab-testing payload as `inward_raw_material.quantity_kg`, mapped by
`inward_raw_material.public_id`.

Existing databases (run after the code is deployed):

```sql
ALTER TABLE public.aggregator_labtesting DROP COLUMN IF EXISTS sowing_date;
```
