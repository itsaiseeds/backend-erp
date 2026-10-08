# PRD — Multiple return orders per order (+ Android API v2)

Status: implemented
Date: 2026-10-08
Extends: [return-orders.md](return-orders.md)

## Context
Today an order can have only one *live* (PENDING or ACCEPTED) return. Clients send goods back in more than one batch, so an order must be able to carry any number of returns. All of them together are still capped by what the challan dispatched.

The Android app gets a new API version, **v2**, for the changed return-order contract. **v1 stays exactly as it is** so older app builds keep working.

The existing code mostly supports this already:
- `returnable_packets` in `aggregator/ReturnOrderOperations.py` already adds up the items of **every** live return.
- Every lifecycle verb already locks the order row with `lock_order(order)`.

The one-return rule lives in only three places:
1. a DB index;
2. one guard function, `assert_order_returnable`;
3. the payloads that return a single `return_order`.

All code lives in `backend-erp/`. The schema is raw SQL in `sql/ddl.sql`; there are no migrations.

## Decisions (from Q&A)
- **Many returns per order.** An order may have any number of live returns. The sum of their items per `(product, packet_weight)` cannot exceed the packets on the challan. A REJECTED return still does not count toward the limit.
- **v1 Android keeps the one-live rule.** `POST /android/api/v1/return-order/<ORD>` still returns 400 if the order already has a live return. `GET` still returns a single `return_order`: the newest live one, or null.
- **v2 Android allows many.**
  - `POST /android/api/v2/return-order/<ORD>` creates another return if the items fit.
  - `GET` returns `return_orders: [...]`, all live returns with the newest first.
- **Sales-admin order detail adds a list and keeps the old key.** It adds `return_orders: [...]` (all live returns, newest first). It keeps `return_order`, which holds the newest live return and is now deprecated, so the current web UI does not break.
- **Admin verbs (edit / accept / unreject)** no longer check the one-live rule. They still check the order status and the shared packet limit. Without this change, a second return raised from v2 could never be accepted.

## DB changes
No new tables or columns are needed.
- `ReturnOrder.order` is already a plain FK (`related_name="return_orders"`), so the one-to-many relationship already exists.
- **Only change:** drop the partial unique index `uniq_returnorder_one_live_per_order`. It sits on `(order_id)` with the condition `WHERE is_deleted = false AND status_id IN (17, 18)`.
  - Model: remove the constraint from `ReturnOrder.Meta.constraints` in `aggregator/models/ReturnOrder.py`, and update the `LIVE_RETURN_STATUS_IDS` comment.
  - `sql/ddl.sql`: replace the `CREATE UNIQUE INDEX` line with `DROP INDEX IF EXISTS public.uniq_returnorder_one_live_per_order;`. The DDL uses `IF NOT EXISTS`, so deleting the line alone would not drop the index on existing DBs.
  - Prod: run the same `DROP INDEX IF EXISTS` one-liner.
- Nothing else needs to change:
  - `aggregator_returnorder_order_id_idx` already exists, so lookups by order stay indexed.
  - The `ReturnOrderItem` unique key is per return.
  - Inward lots use `lot_no = RET-…` and point at their return.
  - Stock-ledger events are recorded per return.
- Once the index is gone, `lock_order()` is the concurrency backstop. It is already taken by create, edit, accept and unreject, and it already guards the packet limit today.

## Domain changes — `aggregator/ReturnOrderOperations.py`
1. Change the signature to `assert_order_returnable(order, exclude=None, *, single_live=False)`. It always checks that the order is DISPATCHED or DELIVERED. It checks for an existing live return only when `single_live=True`.
2. `create_return_order(..., single_live: bool = False)` passes the flag through. The v1 view passes `single_live=True`.
3. `update_return_order`, `accept_return_order` and `unreject_return_order` drop the one-live check. They keep the status check and `assert_items_within_limit`, which already excludes `ret` and counts every other live return.
4. Add `live_return_orders(order) -> list[ReturnOrder]`, newest first. It reads the `order.live_return_orders` prefetch when one exists. `live_return_order(order)` stays as the first item of that list, for v1 and other compatibility callers.
5. `return_order_prefill_payload(order, *, many: bool = False)`: the v1 shape is unchanged. With `many=True` it emits `return_orders: [...]` instead of `return_order`.
6. Update the docstrings so they no longer say an order can carry only one return.

`revert_dispatch` (`aggregator/OrderOperations.py`) already uses `.first()` on live returns. It still returns 400 while any live return exists, so it works unchanged.

## Android v2
- In `android/api/urls.py`, set `VERSIONS = ["v1", "v2"]`. The existing inheritance in `routing.build_urlpatterns` serves every v1 endpoint under `/android/api/v2/` automatically, so no view files are copied.
- Add `android/api/v2/__init__.py` and `android/api/v2/routes.py`. The routes file contains only `ROUTES = {"return-order/<order_public_id>": ReturnOrderView}`, pointing at the v2 class.
- Add `android/api/v2/ReturnOrderView.py`:
  - It subclasses the v1 `ReturnOrderView`.
  - `GET` calls `return_order_prefill_payload(order, many=True)`.
  - `POST` calls `create_return_order(..., single_live=False)`.
  - It has its own `extend_schema`, with operation ids `android_api_v2_return_order_*` and the `ReturnOrderPrefillV2Serializer`.
- `get-return-orders` needs no change. It is already a list that can be filtered with `?order=`, and v2 inherits it.
- In `api/return_order_serializers.py`:
  - Add `ReturnOrderPrefillV2Serializer` with `order`, `return_orders = ReturnOrderPayloadSerializer(many=True)` and `lines`.
  - Update the `returnable_packets` help text to "less what live returns already claim".

### Plumbing for a second version
- **OpenAPI tags.** `_ANDROID` in `common/openapi_tags.py` is hardcoded to `/android/api/v1/`. Make the Android routes match `/android/api/v\d+/`. Otherwise `tests/test_openapi_tags.py` fails for every v2 path.
- **OpenAPI operation ids.** Override `get_operation_id` in `GroupedAutoSchema` (`common/openapi.py`). It rewrites a leading `android_api_v1_` to the version found in the path, so v1 views inherited by v2 do not produce duplicate operationIds.
- **View-contract test.** The path registry in `tests/test_view_contracts.py` lists every path by hand. Generate the `android/api/v2/...` entries from the v1 entries, with the same view and permission, instead of listing about 60 more by hand.

## Sales-admin web
- `OrderOperations.order_detail_payload` gets a new key: `"return_orders": [return_order_payload(r) for r in live_return_orders(order)]`. It keeps `"return_order"` (the newest live return) and marks it deprecated in the docs.
- In `GetOrderView.order_detail_queryset`, add `.order_by("-created_at")` to the `live_return_orders` prefetch so "newest" is always the same return.
- In `api/order_serializers.py`, add `return_orders = ReturnOrderPayloadSerializer(many=True)`.
- The accept, reject, edit and unreject endpoints keep the same signatures. The domain changes above cover them.

## Docs
- Update `docs/prd/return-orders.md`:
  - Replace the "One live return per order" rule and the partial-index note with a pointer to this PRD.
  - State that v1 Android keeps the single-live create rule.
- Regenerate `docs/api/openapi.yml` with `bash scripts/run.sh schema`.

## Tests
- **`tests/test_return_orders.py`.** Replace the tests that expect a second live return to fail with 400 by these cases:
  - Two returns that fit the challan together are both created.
  - A return that pushes the total over the limit returns 400.
  - Accepting or unrejecting a second return respects the shared limit.
  - Rejecting a return frees its packets for other returns.
- **New `tests/android/test_return_orders_v2.py`:**
  - v2 GET returns a `return_orders` list.
  - v2 POST allows a second return.
  - v1 POST still returns 400 when a live return exists.
  - v1 GET still returns a single `return_order`.
- **`tests/android/test_routing.py`.** The real v2 resolves inherited routes to the v1 classes, and resolves `return-order/...` to the v2 class.
- **Admin order detail.** The response contains the `return_orders` list and the old `return_order` key.

## Verification
1. Run the full suite on the host `.venv`, with only the db container running: `pytest tests -n 4 --dist loadscope`.
2. Check the DDL separately, because the test DB is built from the models, not from `ddl.sql`. Load `ddl.sql` and `dml.sql` into a scratch DB, then confirm that the index is gone and that the schema matches the model-built test DB.
3. Confirm `ruff check` is clean. Regenerate `openapi.yml` and confirm two things: there are no operationId collision warnings, and the v2 paths are tagged.
4. Smoke test the endpoints:
   - Two `POST`s to `/android/api/v2/return-order/<ORD>` whose items fit together return two `RET-` ids.
   - A second `POST` to `/android/api/v1/...` returns 400.
