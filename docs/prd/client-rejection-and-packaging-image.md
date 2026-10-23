  # PRD — Client rejection & product-packaging image

Status: approved, not yet implemented
Date: 2026-10-23


## 1. Why
Clients asked for two changes:
1. A sales admin can **reject** a client. Allowed moves are `VERIFICATION_PENDING → CLIENT_REJECTED` and `CLIENT_REJECTED → VERIFICATION_PENDING`. A sales-admin endpoint does the re-open. Only the status changes: no reason or rejected_by columns.
2. A **product packaging can have its own optional image**. Packaging create and edit accept it. Wherever an app shows a packaging's picture, the packaging image is used first, then the product image.

Everything must stay backwards compatible. The Flutter admin and Android apps are not changing, so all existing request and response shapes keep working. New keys and statuses are additive only.

The project has no Django migrations. The schema lives in `sql/ddl.sql` and `sql/dml.sql`, plus a "Production (Neon) needs: ALTER …" comment (the pattern already used for `is_usable`).

---

## Part 1: CLIENT_REJECTED status

**Seed / enum**
- `sql/dml.sql`: add a status row `(21, 'CLIENT_REJECTED', 'Rejected', sequence 3)` next to ids 8–9. The code `REJECTED` is already taken by order id 7 and `code` is unique, which is the same reason `RAW_MATERIAL_REJECTED` exists. Add a comment with the production `INSERT` for Neon.
- `aggregator/models/Status.py`:
  - Add `CLIENT_REJECTED = 21` and update the docstring.
  - Change `client_statuses()` from a range to an explicit list `[VERIFICATION_PENDING, VERIFIED, CLIENT_REJECTED]`.
  - This list feeds `CLIENT_STATUS_CODES` (Client.clean), both GetClientsView status filters and catalogues, and the analytics `by_status` zero-fill (`aggregator/AnalyticsOperations.py:26`, `android/api/v1/AnalyticsView.py`). All of these are additive: a new key or filter value appears.

**Model**: `aggregator/models/Client.py`
- Add an `is_rejected` property next to `is_verified`.
- In `clean()`, treat `CLIENT_REJECTED` like pending: it may not carry `verified_by`.

**Operations**: `aggregator/ClientOperations.py`
- Add a transition guard, `_assert_client_status(client, allowed: set[StatusIds], action)`, which raises `ValidationError`.
- `verify_client`: now requires `VERIFICATION_PENDING`. This blocks REJECTED → VERIFIED. Today the only path is from pending anyway, because the view blocks already-verified clients.
- New `reject_client(client, admin)`: requires PENDING. Sets the status and saves `update_fields=["status","updated_at"]`. Notifies with `NotificationEvent.CLIENT_REJECTED`.
- New `reopen_client(client, admin)`: requires REJECTED and sets VERIFICATION_PENDING.
- Update the `update_client_core` docstring.

**Notifications**: `aggregator/NotificationOperations.py`
- Add `CLIENT_REJECTED` to `NotificationEvent`, with `EventSpec("Client rejected", "was rejected", Screen.CLIENT_DETAIL)`. It reuses the existing `notify_client_event` and `_client_message`.

**Endpoints**: `api/sales_admin/`
- `RejectClientView.py` (`POST /api/sales-admin/reject-client/`) and `ReopenClientView.py` (`POST /api/sales-admin/reopen-client/`).
  - Both mirror `VerifyClientView.py`: same `{public_id}` serializer, `admin_required`, `get_object_or_404`, and a response of `client_payload(client)`.
  - Reuse `VerifyClientSerializer`, or rename it to a shared `ClientPublicIdSerializer` and keep the old name as an alias.
  - Turn the operation's `ValidationError` into a DRF 400 the same way the other views do.
- `VerifyClientView.py`: keep the current "already verified" message. Add a 400 for a rejected client ("Re-open the client before verifying it"). Update the module docstring, which says "the only endpoint that may change a client's status".
- `api/sales_admin/urls.py`: register both routes.
- `common/openapi_tags.py:136`: add both routes to the client tag group.
- Update the docstrings that list `?status=` values (`api/sales_admin/GetClientsView.py:22`, `android/api/v1/GetClientsView.py:13`).

**Unchanged on purpose:** bag-order and custom-order booking already require `status == VERIFIED` (`android/api/v1/CreateMultiSelectBagOrderView.py:199`, `api/sales_admin/CreateCustomOrderView.py:214`), so rejected clients cannot book. Android `update-client` stays lists-only.

---

## Part 2: Optional ProductPackaging image

**Schema**
- `aggregator/models/ProductPackaging.py`: add `image_url = CharField(max_length=500, blank=True, default="")`. This follows the `Product.image_url` convention, where empty means unset (not NULL).
- Add a `display_image_url` property that returns `self.image_url or self.product.image_url`.
- `sql/ddl.sql`, table `aggregator_productpackaging`: add `image_url varchar(500) NOT NULL DEFAULT ''`, plus the comment `-- Production (Neon) needs: ALTER TABLE public.aggregator_productpackaging ADD COLUMN image_url varchar(500) NOT NULL DEFAULT '';`. The default keeps existing rows valid.

**Create**: `api/sales_admin/ProductPackagingsView.py`
- `CreateProductPackagingSerializer`: add `image = serializers.ImageField(required=False)`.
- The view has no custom parser, so the DRF defaults apply (JSON, form and multipart). Existing JSON clients keep working, and multipart carries the image.
- In `post`: upload before the transaction with `upload_image(image, folder="product-packagings")` (from `common.storage`, the same pattern as `ProductsView.py:227`). Then pass `image_url` to `create()`.
- `packaging_payload` and `ProductPackagingPayloadSerializer`: add `image_url` (the packaging's own image, which may be blank) and `display_image_url` (resolved). Both keys are additive.

**Edit**: `api/sales_admin/UpdateProductPackagingView.py`
- Add `image = ImageField(required=False)` and `remove_image = BooleanField(required=False)`. The image is optional, so clearing it brings back the product-image fallback. Reject requests that send both.
- Follow `UpdateProductView.py:102-128`:
  - Upload first.
  - Save `update_fields` with `image_url` added, inside the existing `assert_products_usable` transaction.
  - Call `delete_image(old_url)` only after the save commits.
- Update the module docstring ("Only the selling price can be edited" becomes "selling price and image").

**Django admin**: `aggregator/admin.py` `ProductPackagingAdmin`
- Mirror the product admin's upload handling at `aggregator/admin.py:410-488`: an image form field, upload in save, delete the replaced image, and a readonly `image_url`.

**Image resolution in app-facing payloads** (existing keys now return packaging image, falling back to product image)
- `aggregator/ProductOperations.py` `catalogue_packaging_payload`: `"product": {..."image_url": packaging.display_image_url}`. Also add a top-level `image_url` (resolved).
- `aggregator/OrderOperations.py:845` order card: `"image_url": item.product_packaging.display_image_url`. The existing `select_related("product_packaging__product")` already covers it, so no extra queries.
- `android/api/v1/GodownProductPackagingsView.py:53`: the same resolved value. Update the help text and docstring.
- Schema serializers: update help text in `api/order_serializers.py` (`OrderCardProductSerializer.image_url`) and `android/api/v1/SalesPersonCatalogueView.py:70`.
- Leave `ProductOperations.packaging_payload` (embedded in order, dispatch and sales-admin payloads) and `product_payload` alone.
- Custom orders (`CustomOrderOperations.py:1291`) are product-based with no packaging, so they are unchanged.

---

## Docs
- Regenerate `docs/api/openapi.yml` (drf-spectacular: `python manage.py spectacular --file docs/api/openapi.yml`).
- Update `docs/knowledge-graph.md`: the Client row, the routes, and the ProductPackaging row.

## Tests (pytest, `tests/`)
- `tests/test_client_api.py` and `tests/test_client_model.py`:
  - reject pending → 200, CLIENT_REJECTED, notification queued;
  - reject verified or rejected → 400;
  - reopen rejected → pending, and reopen pending or verified → 400;
  - verify rejected → 400;
  - non-admin → 403;
  - the get-clients `?status=CLIENT_REJECTED` filter;
  - analytics `by_status` includes CLIENT_REJECTED: 0. Update the exact-dict assert in `tests/android/test_orders.py:223` and the status catalogue assert in `tests/android/test_clients.py:502`.
- `tests/test_product_packaging_api.py`:
  - create with JSON (no image) still works;
  - create multipart with an image sets `image_url`;
  - PATCH image replaces it and deletes the old one;
  - `remove_image` clears it;
  - image plus `remove_image` → 400.
- `tests/android/test_sales_person_catalogue.py`, the order card tests in `tests/android/test_orders.py`, and `tests/android/test_godown_stock_count.py` / godown packagings: the resolved image is the packaging image when set and the product image otherwise.
- Reuse the image fixtures and storage mocking from `tests/conftest.py` and `tests/test_image_storage.py`.

## Verification
- Run the suite on the Windows host with `.venv` and the docker DB env vars, per the memory note. Apply `sql/ddl.sql` and `sql/dml.sql` to the test DB first, since DDL is checked separately.
- Smoke test against a running dev server:
  - POST reject-client, then reopen-client, then verify-client on a seeded pending client (client 5 in dml).
  - Multipart POST and PATCH on product-packagings with an image, then GET the Android catalogue and order cards to confirm the resolved `image_url`.
- Confirm that old JSON packaging create/patch payloads and `VERIFIED`/`VERIFICATION_PENDING` flows behave exactly as before.
