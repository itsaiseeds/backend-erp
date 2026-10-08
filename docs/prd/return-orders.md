# PRD — Return orders

Status: implemented (see "Implementation notes" at the end)
Date: 2026-10-03

## Context
At the end of a season, clients send some product back against orders that were already shipped. We need to:
- record these returns and link each one to the original order;
- check that nothing is returned beyond what was actually dispatched;
- let a sales admin accept, reject, or undo either decision.

An accepted return becomes **inward stock**: its raw kg goes In Use directly, and if the admin chooses, its packing materials (from the recipes) are added too. The stock ledger must stay in sync with every step.

All code lives in `backend-erp/`. The schema is raw SQL in `sql/ddl.sql` and `sql/dml.sql`; there are no migrations.

## Decisions (from Q&A)
- **How returns become stock.** Accepting a return writes real `InwardRawMaterial` and `InwardOtherMaterial` rows that point back to the return. Every stock screen, export and ledger figure then picks them up with no reader changes.
- **Sold limit.** Only DISPATCHED or DELIVERED orders can have a return. The limit for each `(product, packet_weight)` is the packets on the order's challan: `DispatchEntryItem.quantity × packaging.packets`.
- **Live returns.** A return is live while PENDING or ACCEPTED. ~~An order can have only one~~ -- superseded by [multiple-return-orders.md](multiple-return-orders.md): an order may carry many live returns whose sum per `(product, packet_weight)` stays within the challan. **Android v1 keeps the single-live create rule** (400 if a live return exists). A REJECTED return keeps its order FK, but it is hidden from the order's details and does not count toward the limit.
- **Statuses.**
  - PENDING → ACCEPTED or REJECTED.
  - ACCEPTED → PENDING (revert-accept).
  - REJECTED → PENDING (unreject; re-checks the limit and the one-live rule).
  - Only PENDING returns can be edited, by the admin, with the same rules as create. Reject is allowed only from PENDING, so an accepted return must be reverted first.
- **Packing materials.** When `include_in_other_raw_materials` is true, the admin also sends a flat `recipe_public_ids` list. Live and soft-deleted recipes are both accepted (`OtherMaterialRecipe.all_objects`). Rules:
  - Each recipe is matched to the return line with the same `(product, packet_weight)`. A recipe that matches no line returns 400.
  - Each `(product, weight)` can have at most one recipe per material type (400 otherwise).
  - Every line must get at least one recipe, or the accept returns 400 and names the uncovered lines.
  - Each chosen recipe books `recipe.quantity × packets` of its material.
  - When the flag is false, `recipe_public_ids` must be empty or omitted.
- **New recipe picker endpoint.** `GET return-order-recipes/<RET-public_id>` returns, for each line of the return, every recipe for that line's `(product, packet_weight)`, including deleted ones. Each recipe shows `public_id`, material type (id, name, unit), quantity per packet, `is_deleted`, `created_at` and `deleted_at`.
- **Revert-accept** returns 400 if removing the raw kg or material would take available stock below zero. This is the same guard used when deleting an in-use lot.
- **Price.** The sales person enters `price_per_packet` (≥ 0). The GET prefill suggests the order line's bag price ÷ packets per bag.
- **Return date.** `return_date` defaults to today and is informational only. The inward `effective_date` is the accept date.
- **Inward rows created by a return:**
  - `party_id` is NULL and `lot_no` is the return's public_id.
  - In payloads, `party` reads `{"id": null, "name": "Return Order (<ORD-…>)"}`, and a new `return_order` reference is added.
  - They cannot be edited or deleted through the normal inward or Django-admin paths (400). Only revert-accept removes them.
- **Order guard.** `revert_dispatch` returns 400 while the order has a live return.
- **Android.** Sales people work only on orders they created. They get GET prefill, POST create, and `get-return-orders` (their own returns).

## Schema (`sql/ddl.sql`, `sql/dml.sql`)
- **Statuses** in `dml.sql`, mirrored in `StatusIds`:
  - id 17 `RETURN_PENDING`
  - id 18 `RETURN_ACCEPTED`
  - id 19 `RETURN_REJECTED`
- **`aggregator_returnorder`**:
  - Standard columns: id, timestamps, soft-delete, `created_by`, `public_id` (`RET-`).
  - Fields: `order_id`, `status_id`, `return_date`, `include_in_other_raw_materials` (nullable bool, set on accept), `verified_by_id`, `verified_at`, `rejected_by_id`, `rejected_at`.
  - ~~Partial unique index `uniq_returnorder_one_live_per_order`~~ -- dropped; see [multiple-return-orders.md](multiple-return-orders.md). `lock_order()` is the concurrency backstop for the shared limit.
- **`aggregator_returnorderitem`**:
  - Standard columns.
  - Fields: `return_order_id`, `product_id`, `packet_weight numeric(8,3)`, `packets int8 > 0`, `price_per_packet numeric(12,2) >= 0`.
  - Unique on `(return_order_id, product_id, packet_weight)`. It is not soft-delete aware, so syncing items restores rows, the same way `_sync_order_items` does.
- **Inward tables.** `aggregator_inwardrawmaterial` and `aggregator_inwardothermaterial` both get:
  - `party_id` made nullable;
  - a new `return_order_id` FK with an index;
  - `CHECK (party_id IS NOT NULL OR return_order_id IS NOT NULL)`.
- **`aggregator_stockevent`** gets a new `return_order_id` FK.

## Models
- New `aggregator/models/ReturnOrder.py` and `ReturnOrderItem.py`, following the bases in `Order.py` and `OrderItem.py`. Register them in `aggregator/models/__init__.py`.
  - `ReturnOrderItem` gets `kg` and `line_total` properties.
  - `ReturnOrder` gets `total_kg` and `total_amount`.
- `InwardEntryMixin.party` becomes `null=True`. A `return_order` FK is added to both inward models, and `clean()` requires a party unless `return_order` is set.
- `StockEvent.py`:
  - add `return_order = _source_fk(...)`;
  - add `StockEventType.RETURN_OPERATIONS = 12`;
  - add `StockEventDetail.RETURN_ACCEPTED = 80` and `RETURN_ACCEPT_REVERTED = 81`;
  - add both to `VALID_DETAILS`.

## Operations: new `aggregator/ReturnOrderOperations.py`
- **`returnable_packets(order, exclude=None)`** returns a dict `{(product_id, packet_weight): packets}`. It sums the order's live dispatch-entry bag lines and subtracts the items of any other live return.
- **Assertions:**
  - `assert_order_returnable(order)`: status is DISPATCHED or DELIVERED, and the order has no other live return.
  - `assert_items_within_limit(order, items, exclude)`: items are non-empty, have no duplicate `(product, weight)`, each pair appears on the challan, and packets do not exceed the limit.
- **Create and edit:**
  - `create_return_order(order, return_date, items, actor)` locks the order row first (`get_locked_order` pattern), so two creates for the same order run one after the other.
  - `update_return_order(ret, return_date, items, actor)` is allowed only on PENDING.
- **`return_order_recipe_options(ret)`** returns, per line, every recipe from `OtherMaterialRecipe.all_objects` for that line's `(product, packet_weight)`. The recipe picker endpoint uses it.
- **`accept_return_order(ret, include_other, recipe_public_ids, admin)`**, allowed only on PENDING:
  1. Re-run the limit check.
  2. If `include_other` is true, resolve `recipe_public_ids` through `all_objects` and apply the matching, one-per-material-type and every-line-covered rules above. Each failure returns 400.
  - **Implementation check:** confirm that `other_material_inward` and the material guards still count an inward row whose recipe is soft-deleted. The PRD says lots booked against a replaced recipe still count; verify that the join does not filter deleted recipes.
  3. Inside `recording(RETURN_OPERATIONS, RETURN_ACCEPTED, product_ids, source=ret, actor=admin)`, create these rows:
     - one IN_USE `InwardRawMaterial` per item, with `effective_date` = today and `quantity_kg` = packets × weight;
     - one `InwardOtherMaterial` per item per recipe.
  4. Set the return to ACCEPTED and stamp `include_in_other_raw_materials`, `verified_by` and `verified_at`.
- **`revert_accept_return_order(ret, admin)`**, allowed only on ACCEPTED:
  1. Inside `recording(RETURN_OPERATIONS, RETURN_ACCEPT_REVERTED, ...)`, lock the raw pools.
  2. Soft-delete the linked inward rows.
  3. Assert raw and material availability using `assert_raw_lot_removable` and the existing material guard.
  4. Set the return back to PENDING and clear the accept fields.
  - **Implementation check:** `InwardRawMaterial.guard_soft_delete` opens its own `recording`. Confirm how a nested recording behaves. If it would write a duplicate event, call the assertion functions directly and bypass the guard's own recording just for this path.
- **Reject and unreject:**
  - `reject_return_order` (PENDING → REJECTED, stamps `rejected_by` and `rejected_at`) writes no ledger row, because no stock moves.
  - `unreject_return_order` (REJECTED → PENDING) re-runs `assert_order_returnable` and the limit check.
- **Payload helpers:** `return_order_payload(ret)` and `return_order_list_payload(ret)` return status, dates, order and client references, the actors, the items (product, weight, packets, kg, price, total), totals, and the inward lot public_ids when accepted.

## Changes to existing code
- `StockLedgerOperations._SOURCE_FIELDS` maps `ReturnOrder` to `return_order`.
- `StockLedgerReport._source_payload` adds a `return_order` branch with the client name as the label. Bump `CACHE_VERSION`.
- `OrderOperations.revert_dispatch` returns 400 if the order has a live return.
- `OrderOperations.order_detail_payload` adds `"return_order"`: the live return's payload, or null. `GetOrderView.order_detail_queryset` prefetches it.
- In `InwardOperations`:
  - `inward_raw_material_payload` and `inward_other_material_payload` (and the export payloads) build the synthetic party for return rows and add `"return_order"`.
  - Their querysets add `select_related("return_order__order")`.
  - `update_raw_lot`, the other-material update and delete, both `guard_soft_delete` methods, and the Django admin all refuse rows with a `return_order` (400 or read-only). Revert-accept is the only allowed path.
- Documentation-only serializers in `api/order_serializers.py` (or a new `api/return_order_serializers.py`) are updated so the OpenAPI document and the contract tests match.

## Endpoints
**Android** (`android/api/v1/routes.py`, `AndroidBaseView`, orders limited to `created_by=request.user`):
- `return-order/<order_public_id>`, GET: returns
  - an order summary;
  - the live return, if there is one;
  - `lines[]`: product, packet_weight, dispatched_packets, returnable_packets, suggested_price_per_packet.
- `return-order/<order_public_id>`, POST: body is `{return_date?, items:[{product_public_id, packet_weight, packets, price_per_packet}]}`. Returns 201 with the return payload.
- `get-return-orders`: an `AndroidPaginatedDateRangeListView` of the user's own returns.

**Sales admin** (`api/sales_admin/urls.py`, `AdminApiView`, `admin_required`):
- `order/<public_id>`: now includes `return_order`.
- `return-orders/`: an `AdminPaginatedDateRangeListView`.
  - Filters: `public_id_filter("RET-")`, status, created_by, client (`order__client`), product (`items__product` plus distinct), order public id.
  - Sorts: `created_at`, and value through an annotated subquery, the same way `GetOrdersView` sorts by price.
- `edit-return-order/<public_id>`: uses the same HTTP method as `edit-order`. The body matches the Android POST.
- `return-order-recipes/<public_id>`: GET. The recipe picker (live and deleted recipes, grouped per line).
- `accept-return-order/<public_id>`: POST with `{include_in_other_raw_materials: bool (required), recipe_public_ids: [OMR-…]}`.
- `reject-return-order/<public_id>`, `unreject-return-order/<public_id>` and `revert-accept-return-order/<public_id>`: POST with no body. The "retun" typo in the request is corrected in the route name.
- A shared `ReturnOrderTransitionView` mirrors `OrderTransitionView`: lock the row, apply the transition, refresh, and return the payload.

## Docs and housekeeping
- `docs/prd/product-stock-ledger.md` §3.1: add a row for the new event type.
- `docs/knowledge-graph.md`: add the data model and URL map entries.
- `common/openapi_tags.py`: group the new endpoints.
- `docs/api/openapi.yml`: regenerate.
- Add the new routes to `EXPECTED_CONTRACTS`.
- Grep `admin_saiseeds/` for parsing of the inward `party`, to confirm a null `id` is safe. Report it if it is not.

## Verification
- **New tests:** `tests/test_return_orders.py` for operations, and admin and Android API tests. They cover:
  - over-limit, wrong weight, a product not on the challan, a non-dispatched order, a second live return, unreject while another return is live, and returns on another sales person's order;
  - accept with and without materials;
  - accept with a deleted recipe booking material;
  - accept returning 400 for a recipe that matches no line, two recipes of the same material type, or an uncovered line;
  - the picker endpoint listing deleted recipes;
  - stock figures after accept: raw `incoming` goes up and material `incoming` goes up;
  - revert-accept returning 400 once the stock has been packed;
  - normal inward edit or delete of a return lot returning 400;
  - revert-dispatch returning 400 while a return is live;
  - a rejected return disappearing from the order detail.
- **Ledger:** each test asserts the `RETURN_OPERATIONS` event deltas. The autouse fixture in `tests/conftest.py` already checks ledger == live after every DML test, and `tests/test_stock_ledger_reconciliation.py` gets the new operations added to its random sequence.
- **Full run:** run `pytest`, then `python manage.py check_stock_ledger` against a dev database loaded from `ddl.sql` and `dml.sql`.

## Implementation notes

Where the build differs from, or adds to, the sections above:

- **Revert-accept and the nested `recording`.** The check on `guard_soft_delete` is
  confirmed: it opens its own `recording`, and a nested one writes its own event next
  to the outer one, so a revert through it would be two events. `revert_accept_return_order`
  therefore soft-deletes the lots with one queryset update and calls
  `InventoryOperations.guard_stock_deletion(...)` with **no** `ledger=`, inside its own
  `recording`. That is the same raw / packing-material guard an in-use lot deletion
  applies (negative **and** lower than before is refused), so `assert_raw_lot_removable`
  is not called separately. Nothing changes on a refusal, ledger included.
- **Deleted recipes still count.** `other_material_inward` joins the lot's recipe only to
  read `material_type_id`, with no `is_deleted` filter, and `product_material_type_ids`
  reads recipes through `all_objects`. Neither needed a change; a test books material
  against a soft-deleted recipe and `check_ledger` stays empty. A material type that only
  a deleted recipe uses is not among those `recording` locks, so accept locks the chosen
  types itself, after the recording's locks (raw, bag, loose, materials) to keep the order.
- **Statuses in payloads.** The `status` of a return is its code: `RETURN_PENDING`,
  `RETURN_ACCEPTED` or `RETURN_REJECTED`. The `return_order` reference on an inward lot is
  `{public_id, order_public_id}`.
- **Picker response.** `GET return-order-recipes/<RET-…>` answers `{"lines": [...]}`, each line
  carrying its product, `packet_weight`, `packets` and `recipes`.
- **Lock order.** Create locks the order row; edit and the four verbs lock the return row,
  then the order row, then the stock pools. `revert-dispatch` locks the order row only, so it
  is serialised against all of them.
- **Django admin.** `ReturnOrder` is not registered. The two inward lot admins make a lot with a
  `return_order` read-only (no change, no delete) and never let `return_order` be set by hand.
- **`party` on a return lot** is NULL in the table and `{"id": null, "name": "Return Order (ORD-…)"}`
  in payloads. The Flutter admin reads a null party `id` as `0` (`int.tryParse('null') ?? 0`) and
  shows the name, so nothing breaks; the id is never sent back. The frontend was not changed.
- **Android list.** `get-return-orders` filters by `?status`, `?order` (order public id) and
  `?public_id`, and sorts by `created_at`.
- **Schema.** `sql/ddl.sql` and `sql/dml.sql` were loaded into an empty Postgres, and a full
  create / accept (with and without packing) / revert / reject / unreject run on the dummy data
  left `check_stock_ledger` clean. The two `CHECK`s and the partial unique index were exercised
  in SQL.
