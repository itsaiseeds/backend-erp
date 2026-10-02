# PRD — Godown manager role

Status: approved, not yet implemented
Date: 2026-10-02

## 1. Why

The Android app serves exactly one role today: `SalesPerson`. Every authenticated
Android endpoint is gated by `AndroidBaseView.salesperson_required = True`, and
`LoginView` refuses anyone without a live `SalesPerson` profile.

Godown (warehouse) staff need a different slice of the system — the inward-material
screens that exist only on the sales-admin Flutter dashboard today:

| Dashboard tab | What it is | Godown needs |
|---|---|---|
| `raw-material-stock` | Incoming raw-material position per product | View |
| `other-material-stock` | On-hand position per material type | View |
| `inward-raw-materials` | Raw-material lots received | View, create, edit |
| `other-material-inward` | Other-material lots received | View, create, edit |
| `other-raw-materials` | Material recipes (`OtherMaterialRecipe`) | View |

Those five tabs are backed by `admin_required` endpoints under `/api/sales-admin/`,
reachable only with a web session cookie. A godown manager therefore cannot use them
from a phone, and there is no role to hang the permission on.

## 2. Goals

1. A second Android role, `GodownManager`, as a peer table to `SalesPerson`.
2. The five dashboards above, mirrored as token-authenticated Android endpoints that
   only godown managers may call.
3. Android login reports **both** roles so the client picks its own navigation.
4. Admins can hire godown managers from the sales-admin web app.
5. The app can reach a sales admin by phone, for admins who opt in.

Non-goals: godown managers do not get the sales-admin web app, and they create no
master data (parties, recipes, material types stay admin-only).

## 3. Rules

### 3.1 Role and identity

- `GodownManager` is a 1:1 profile on `User`, carrying **no** location field. Nothing
  in the inward domain is scoped by location, so a `city` or `godown` FK would be
  speculative.
- A user may hold both profiles. Holding both grants both sets of screens; the two
  flags are independent, never exclusive.
- Losing the role must revoke every live credential (`revoke_user_credentials`), the
  same as `SalesPerson` and `Admin`. This is load-bearing: it is what makes
  "a live token implies a live Android role" true, which 3.2 relies on.
- Only a superuser or an application `Admin` may create one — the same rule as
  `SalesPerson`.

### 3.2 Authorization

- Android stays **token-only**; the web stays **session-only**. Nothing here changes
  that split.
- Role gating is expressed as `BaseApiView` flags. No view may hand-roll
  `permission_classes` — `get_permissions()` ignores it and a test enforces this.
- `BaseApiView` ANDs its flags, so "salesperson **or** godown manager" needs its own
  permission class.
- The `godown/` routes are **godown-manager-only**. A salesperson token must get 403.
- Everything under `utilities/` is open to **both** Android roles, existing routes
  included. Look-ups are reference data both apps legitimately need; the boundary
  that matters is the `godown/` prefix, not the look-ups feeding its forms.
  This is safe because every `utilities/` view is either flat reference data or
  already scoped to `created_by=request.user` — a godown manager owns no clients, so
  those return nothing. No client-owned or order data becomes reachable.
- `auth/reauthenticate` must accept either role, or a godown-manager-only user is
  locked out at startup.
- `tests/test_view_contracts.py` remains the single owner of the auth contract. Every
  new or changed route is declared there; per-endpoint auth tests stay forbidden.

### 3.3 Login payload

`POST /android/api/v1/auth/login` and `GET /android/api/v1/auth/reauthenticate` both
return, on the `user` object:

- `is_sales_person` — wire spelling matches the existing `can_create_sales_person`;
  the Python property stays `is_salesperson`.
- `is_godown_manager`

Login accepts a user with either role. A user with neither still gets the existing
generic 400, indistinguishable from a wrong code.

### 3.4 Inward behaviour on Android

- The Android endpoints must reuse `aggregator/InwardOperations.py` — the status
  lifecycle (`assert_raw_status_transition`), the removability check
  (`assert_raw_lot_removable`), the `effective_date` stamping, and the pool locking
  — not restate any of it. Same rules, different client.
- `DELETE` is included. The web corrects a wrong booking by soft-delete + re-book
  (`product` / `party` / `quantity` are immutable by design), so without `DELETE` a
  godown manager could not fix a mistyped quantity.
- `other-material-recipes` is view-only. It doubles as the recipe picker via the
  existing `?all=true` pagination escape, so no separate look-up endpoint exists.
- The refusals must still bite from Android: reverting or deleting an `In Use` lot
  whose kilograms are already packed is a 400.

### 3.5 Sharing a sales admin's contact

- Not every admin wants their number handed out, so listing is **opt-in** via a new
  `Admin.share_contact` boolean, default `false`.
- The look-up exposes **name and phone number only** — no id, no email, nothing else
  off the user record.
- A soft-deleted admin drops out automatically (the default manager is
  soft-delete-aware).

## 4. API surface

### New — Android, godown-manager-only

| Route (under `/android/api/v1/`) | Methods |
|---|---|
| `godown/raw-material-stock` | GET |
| `godown/other-material-stock` | GET |
| `godown/inward-raw-materials` | GET, POST |
| `godown/inward-raw-material/<public_id>` | PATCH, DELETE |
| `godown/inward-other-materials` | GET, POST |
| `godown/inward-other-material/<public_id>` | PATCH, DELETE |
| `godown/other-material-recipes` | GET |

### New — Android, either role

| Route | Returns |
|---|---|
| `utilities/parties` | flat list via `InwardOperations.party_payload` |
| `utilities/other-material-types` | flat list via `other_material_type_payload` |
| `utilities/sales-admins` | `[{name, phone_number}]`, `share_contact` admins only |

### New — sales-admin web

| Route | Methods |
|---|---|
| `/api/sales-admin/godown-managers` | GET, POST |
| `/api/sales-admin/godown-managers/<int:id>` | PATCH, DELETE |

### Changed

- `auth/reauthenticate` and all seven existing `utilities/…` routes: salesperson-only
  to either-role.
- `VerifyOTPView` and the web `ReauthenticateView` gain `can_create_godown_manager`
  (superuser or admin), beside the existing `can_create_*` flags.
- `AdminsView` / `UpdateAdminView` accept and return `share_contact`.

## 5. Implementation map

### Role table

- New `authentication/models/GodownManager.py`, mirroring `SalesPerson.py` minus the
  `city` FK; export from `authentication/models/__init__.py`.
- `authentication/models/User.py` — `is_godown_manager` via the existing
  `_live_profile` helper (it already handles the soft-deleted reverse-O2O trap), and
  `"godown_manager"` slotted into `role` after `salesperson`.
- `authentication/admin.py` — `GodownManagerAdmin(SoftDeleteModelAdmin)` mirroring
  `SalesPersonAdmin`.

### Schema (raw SQL — there are no migrations)

- `sql/ddl.sql` — `public.authentication_godownmanager` after
  `authentication_salesperson` (~line 195): same columns minus `city_id`, the three
  `CREATE INDEX` lines, and in the FK-override block (~line 425) the three
  `ALTER TABLE` statements (`user` CASCADE, `created_by` RESTRICT, `deleted_by` SET NULL).
- `sql/ddl.sql` — `ALTER TABLE public.authentication_admin ADD COLUMN share_contact
  boolean NOT NULL DEFAULT false;` beside the `can_update_stock_count` one (~line 485),
  which is how that column was added.
- `sql/dml.sql` — content type id **51**, permissions **182–185**, a seed godown
  manager user + profile beside the salesperson seed, a `setval` line, and
  `share_contact` on the two seeded admin rows (one `true`).
- Production (Neon) is manual SQL applied **after** the code deploy, per
  `skills/database.md`.

### Permissions

- `api/permissions.py` — `IsGodownManager(IsRolePermission)` and `IsAndroidRole`
  (either role).
- `api/views.py` — `godown_manager_required` and `android_role_required` flags.
- `android/api/base.py` — split so the 24 existing views are untouched:
  `AndroidTokenView` holds the auth scheme; `AndroidBaseView` keeps
  `salesperson_required`; new `AndroidGodownBaseView` and `AndroidSharedView`.
- `android/api/paginated_views.py` — `AndroidGodownPaginatedDateRangeListView`.

### Shared serializers

The business logic is already client-agnostic in `InwardOperations`; the serializer
and filter/sort declarations are not — they sit inline in the web view modules.
Following the `api/client_serializers.py` precedent, move them verbatim into a new
`api/inward_serializers.py` and import from both clients. Also move `locked_raw_lot()`
from `UpdateInwardRawMaterialView.py` into `InwardOperations` — it is concurrency
logic, and both clients must take the same locks in the same order.

This is the only refactor; everything else is additive.

### Flutter admin app

Copy `lib/features/sales_people/` to `features/godown_managers/` dropping the city
field, add a `godown_managers_endpoints.dart`, wire the tab into `tab_ids.dart`,
`dashboard_content_switcher.dart` and the sidebar, and carry
`can_create_godown_manager` through `auth_session.dart` / `user_roles.dart`. Add the
`share_contact` checkbox to the admins form and `shareContact` to `admin_model.dart`.
Rebuild the committed bundle with `bash scripts/run.sh flutter`.

### Docs and grouping

- `common/openapi_tags.py` — new tags and `ROUTE_TAGS` patterns for
  `/android/api/v1/godown/…` and the three new `utilities/` routes;
  `tests/test_openapi_tags.py` fails for any ungrouped operation.
- `docs/frontend-auth-android.md` — the two new login flags.
- `docs/knowledge-graph.md` — `GodownManager` in the auth subgraph and node registry,
  the new routes, and `share_contact` on the `Admin` node (which currently documents
  `can_update_stock_count` as gating "nothing else").
- Regenerate `docs/api/openapi.yml` (`bash scripts/run.sh schema`).

## 6. Acceptance criteria

1. `bash scripts/reload_db.sh --step all` applies the new DDL and DML cleanly.
2. A godown manager logs in on Android and gets `is_sales_person: false`,
   `is_godown_manager: true`.
3. With that token: every `godown/…` route answers, `utilities/parties` and
   `utilities/sales-admins` answer, and `get-clients` is 403.
4. Booking a raw lot then `PATCH`ing it to `In Use` stamps `effective_date` with
   today and moves the kilograms into `incoming_kg` on the stock endpoint.
5. Reverting or deleting an `In Use` lot whose kilograms are already packed is a 400.
6. With a salesperson token: every `godown/…` route is 403, `get-clients` answers,
   and every `utilities/…` route answers.
7. A user holding both profiles reports both flags true and reaches both route sets.
8. `utilities/sales-admins` lists only `share_contact` admins, name and phone only,
   and omits a soft-deleted admin.
9. Soft-deleting a `GodownManager` revokes that user's token.
10. `test`, `lint` and `typecheck` pass; `test_view_contracts.py` and
    `test_openapi_tags.py` cover every new and changed route.

## 7. Known adjacent defects (out of scope)

Found while reading `admin_saiseeds/lib/features/inward_raw_materials/`, independent
of this change and deliberately left alone:

- The Flutter create form never sends `lot_no`, which `CreateInwardRawMaterialSerializer`
  requires — so creating a raw-material lot from the dashboard 400s.
- The Dart `InwardStatus` enum omits `Rejected`, so `rejected_kg` and the reject
  transition are unreachable from the dashboard.

The new Android views should implement both correctly from the start.
