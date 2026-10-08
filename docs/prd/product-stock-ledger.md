# PRD — Product stock ledger (cumulative view)

Status: implemented (see "Implementation notes" at the end)
Date: 2026-10-03

## 1. Why

Admins need one view per product that answers: *over this date range, what happened
to this product's stock, and what were the figures after each step?* The view covers
sealed bags, loose packets, raw material and packing (other) material.

Today this cannot be answered, because the system keeps **no history**:

| Figure | How it is held today | Why the past is lost |
|---|---|---|
| Bag / loose on hand | `InventorySnapshot` / `LooseStockSnapshot`, one row per day per pool | A recount on the same day overwrites `bags` / `packets` and `counted_at` |
| Reserved | Derived live from the **current** `Order.status` / `CustomOrder.status` (`InventoryOperations.reserved_bags`, `reserved_loose_packets`) | Status changes overwrite `status_id`; there is no transition log |
| Consumed | Derived live from `DispatchEntryItem.quantity` and `DispatchEntry.dispatched_at` | `dispatched_at` is re-stamped on re-dispatch; lines are edited in place |
| Raw incoming / rejected | `InwardRawMaterial.status` + `effective_date` | A Lab Testing round-trip overwrites `effective_date` |
| Raw waste | `RawMaterialWaste`, undated by design | Only `created_at` / `deleted_at` |
| Packing material used | `other_material_used` values every packed packet at the product's **current** recipe | A recipe change silently re-values all past packing |

So past figures cannot be rebuilt from today's tables. This PRD adds a compact,
append-only **delta ledger** that is seeded once at go-live, plus a report endpoint
over it.

## 2. Goals

1. `GET` a per-product, date-ranged list of events. Each event row gives the running
   figures after that event:
   - **Packed bag data** — per `ProductPackaging`, in bags: `on_hand`, `reserved`,
     `consumed`, `available`.
   - **Packed packet data** — per `(product, packet_weight)` loose pool, in packets:
     `on_hand`, `reserved`, `consumed`, `available`.
   - **Raw material** — per product, in kg: `incoming`, `packed`, `rejected`,
     `available` (plus `wasted`, which `available` needs in order to reconcile).
   - **Other raw material** — per material type, in that type's own unit: `incoming`,
     `packed`, `available` (plus `used_by_other_products`, which reconciles the
     pool-wide `available`).
2. Every figure change is explained by exactly one row. Running row *k* + change in row
   *k+1* = running row *k+1*.
3. The ledger equals the live screens **by construction**. Closing figures match
   `bag-stock`, `sample-packet-stock`, `raw-material-stock` and `other-material-stock`.
4. Small DB footprint: only signed deltas are stored, never derived figures, text or
   JSON.
5. Packing-material usage is frozen at packing time, so a recipe change no longer
   rewrites history.

Non-goals:
- The Flutter admin screen (follow-up).
- Rebuilding history from before go-live.
- Changing reserved / consumed semantics. The ledger mirrors them, and known quirks
  are listed in §7.

## 3. Rules

### 3.1 Events

`OPENING_BALANCE` and `CLOSING_BALANCE` are **synthetic**: they are built in the
response and never stored. Every stored event has an `event_type` and a `detail` code
(both smallint enums).

| event_type | detail codes | Written by |
|---|---|---|
| `LEDGER_START` | `SEED` | `seed_stock_ledger` command (once) |
| `INWARD_OPERATIONS` | `RAW_LOT_IN_USE`, `RAW_LOT_REJECTED`, `RAW_LOT_BACK_TO_LAB`, `RAW_LOT_DELETED`, `OTHER_MATERIAL_RECEIVED`, `OTHER_MATERIAL_EDITED`, `OTHER_MATERIAL_DELETED` | Inward raw / other-material write paths (sales-admin + Android) |
| `RAW_WASTED` | `WASTE_RECORDED`, `WASTE_EDITED`, `WASTE_DELETED` | `record_raw_waste`, waste update / delete |
| `PACKED` | `BAG_COUNT`, `LOOSE_COUNT` | Count writes where packed packets went **up** |
| `STOCK_ADJUSTED` | `BAG_COUNT`, `LOOSE_COUNT`, `COUNT_DELETED` | Count writes where packed packets went **down**, or a count row was deleted |
| `STOCK_COUNTED` | `BAG_COUNT`, `LOOSE_COUNT`, `CARRIED_FORWARD` | Count writes with no packing change, but `on_hand` / `consumed` were reset |
| `ORDER_CONFIRMED` | `ORDER_VERIFIED`, `CUSTOM_ORDER_CREATED` | `verify_order`, `create_custom_order` (+ Django admin path) |
| `ORDER_EDITED` | `ORDER_LINES_CHANGED`, `CUSTOM_ORDER_LINES_CHANGED` | `sync_order_items`, `sync_custom_order_items` on a confirmed order |
| `ORDER_RELEASED` | `UNVERIFIED`, `HELD`, `REJECTED`, `CUSTOM_ORDER_WITHDRAWN` | `unverify_order`, `hold_order`, `reject_order`, `delete_custom_order` |
| `ORDER_DISPATCHED` | `FULL`, `PARTIAL` | `dispatch_order`, `dispatch_custom_order` |
| `DISPATCH_REVERTED` | — | `revert_dispatch` (orders and custom orders) |
| `RETURN_OPERATIONS` | `RETURN_ACCEPTED`, `RETURN_ACCEPT_REVERTED` | `accept_return_order`, `revert_accept_return_order` (`docs/prd/return-orders.md`; rejecting a return moves no stock and writes no row) |

- **No change → no row.** A write that moves no figure writes no event. Examples:
  marking an order delivered, booking a raw lot into Lab Testing, a recount that finds
  identical stock, or a recipe change.
- One write can create **several events for one product**. For example, one bag-count
  upload can raise one packaging (`PACKED`), lower another (`STOCK_ADJUSTED`) and only
  reset a third (`STOCK_COUNTED`).
- A write that touches several products writes one event per product.

### 3.2 Figure semantics (identical to today's screens)

All bag figures are read at `latest_snapshot_date()`, as `BagStockView` does. All loose
figures are read at `loose_date()`.

| Figure | Definition |
|---|---|
| bag `on_hand` | The last count (`on_hand_bags`) |
| bag `reserved` | `reserved_bags`: CONFIRMED order lines, plus the unshipped gap of DISPATCHED/DELIVERED lines |
| bag `consumed` | `consumed_bags`: dispatched **after** the last count. It **resets** at each count |
| bag `available` | `on_hand − reserved − consumed` |
| loose `on_hand` / `reserved` / `consumed` / `available` | The `*_loose_packets` equivalents |
| raw `incoming` | `raw_inward_kg`: In Use lots |
| raw `packed` | `raw_bagged_kg + raw_loose_kg` (count + dispatched before the count, × weight) |
| raw `rejected` | kg of Rejected lots (`InwardOperations._dated_raw_kg_by_product`) |
| raw `wasted` | `raw_wasted_kg` |
| raw `available` | `incoming − packed − wasted` (rejected is never available) |
| other `incoming` | `other_material_inward` for the material type (**pool-wide**) |
| other `packed` | Material used by **this product's** packed packets (§3.4) |
| other `used_by_other_products` | Material used by every other product's packed packets |
| other `available` | `incoming − packed − used_by_other_products` (= the pool-wide figure on `other-material-stock`) |

### 3.3 Classifying a count write

For each pool touched by a count write, compute Δpacked, the change in packed packets
(count + dispatched before the count):

- Δpacked > 0 → `PACKED`
- Δpacked < 0 → `STOCK_ADJUSTED`
- Δpacked = 0 but `on_hand` / `consumed` changed → `STOCK_COUNTED`. This is the normal
  morning recount after yesterday's dispatches: on_hand 100 → 80 and consumed 20 → 0,
  while available is unchanged.
- No figure changed → no row.

### 3.4 Frozen packing-material usage (recipe layers)

Recipes are one row per `(product, packet_weight, material_type)`. A "change" is
delete-old + create-new (`DeleteOtherMaterialRecipeView`, `OtherMaterialRecipesView.post`).

Today `other_material_used` multiplies **all** packed packets by the **current** recipe,
so a change re-values history. From now on, usage is frozen through a link table,
`packed_recipe_layer`, from each count row to the recipes used. Each link row stores
how many packets were packed under that recipe.

On every write that changes a pool's packed packets (count writes, count deletion,
revert of a dispatch made before the count):

1. **New count row for a date:** copy the layers from the pool's previous live row.
2. **Δ > 0:** for each **live** recipe of `(product, packet_weight)`, add Δ packets to
   that recipe's layer. If a material type already has layers but no live recipe now,
   add a layer with `recipe = NULL` ("packed while no recipe existed").
3. **Δ < 0 (unpacking):** for each material type, remove |Δ| packets from its layers
   **newest first** (LIFO, by `opened_at`). Any remainder comes off the implicit
   "unlayered" packets at the bottom, which were packed before that type's first recipe.
4. `other_material_used` = Σ `recipe.quantity × packets` over the layers of the latest
   live bag rows and loose rows. Recipes are read with `all_objects`, so a deleted
   recipe still values its own layer.

- Invariant, per latest pool row and material type: Σ layer packets ≤ packed packets.
- **Behaviour change:** adding a recipe no longer charges packets that are already
  packed, and deleting one no longer frees material already used.

Example: 100 packets were packed at 1 leaflet/packet, the recipe changed to 2, then 50
more were packed. Leaflets used = 100×1 + 50×2 = **200**, not 300.

### 3.5 Count carry-forward (fixes a live bug)

`PATCH update-bag-stock` / `update-sample-packet-stock` can open a **new** day naming
only some pools. Today every unnamed pool then reads 0 bags on hand at the latest date.
Its raw kg and packing material are silently "returned", and order availability can go
negative.

Now, when a count write opens a new date, every pool with a live row on the previous
latest date that the write does not name gets a row on the new date:
- count = last count − consumed since that count (its physical figure);
- `counted_at` = now;
- recipe layers copied from the previous row.

Packed and available are unchanged, and on_hand / consumed reset. The ledger records
this as `STOCK_COUNTED` / `CARRIED_FORWARD`. `POST` (a full count) keeps its meaning:
unnamed packagings are an explicit 0.

### 3.6 Packing material in a product's view

- Only material types used by this product's recipes (live or deleted with layers)
  are shown.
- **Rows listed:** this product's events, plus `INWARD_OPERATIONS` and `RETURN_OPERATIONS`
  for those material types even when booked against another product's recipe (detail
  names that product).
- Other products' packing of a shared material is **not** listed as a row. It shows up
  in the running `used_by_other_products`, so every row still reconciles:
  `incoming − packed − used_by_other_products = available`.

### 3.7 History and range

- Go-live runs `seed_stock_ledger` once. It writes a `LEDGER_START` event per product
  (deltas from zero up to the live position), plus layers for every existing live count
  row at the current recipes. No live figure moves at go-live.
- A `start_date` before the go-live date → 400 (`"Stock ledger starts on <date>"`).
- Dates are inclusive IST dates: the window is `[start 00:00, end + 1 day 00:00)`.
- `OPENING_BALANCE` = Σ deltas with `occurred_at` < start.
  `CLOSING_BALANCE` = OPENING + Σ deltas in the window.
- Maximum range is 31 days (`MAX_EXPORT_RANGE_DAYS`). `end_date < start_date` → 400.

### 3.8 Recording (the ledger cannot drift)

All recording goes through one context manager,
`StockLedgerOperations.recording(event_type, detail, product_ids, source, actor)`. It
runs inside the write's `transaction.atomic`, after the write has taken its locks:

1. It reads the live figures of every pool of `product_ids` using the **existing**
   functions in §3.2.
2. The write runs.
3. It reads them again and writes one `stock_event_line` per pool whose figures
   changed, plus the `stock_event` header. If nothing changed, it writes nothing.

- Because the ledger is the diff of the same functions the screens read, it equals
  live by construction.
- A rolled-back write (e.g. `ValueError` on a raw shortfall) rolls back its ledger rows
  too.
- If a count write moves `latest_snapshot_date` / `latest_loose_snapshot_date`, the
  tracked products widen to every product with a pool of that kind.
- Lock order stays raw → bag → loose → materials, as the existing writers do.
- Write logic that lives in views today moves into the operations layer, so it is
  wrapped exactly once. Today this covers inward raw / other-material create, update
  and delete in `api/sales_admin/*` and `android/api/v1/Godown*`, plus waste
  update / delete.
- The Django admin write paths (custom order create, count edits) are wrapped as well,
  or made read-only.

## 4. API surface

### New — sales-admin web

`GET /api/sales-admin/product-stock-ledger/<P-…>?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&page=&page_size=`

- `admin_required`, session auth.
- Unknown or deleted product → 404.
- Validation errors → 400 (§3.7).
- Paginated. `OPENING_BALANCE` is the first row of page 1 and `CLOSING_BALANCE` the
  last row of the last page. Running totals are computed over the whole range, then
  sliced.

```json
{
  "product": {"public_id": "P-…", "name": "…"},
  "start_date": "2026-10-01", "end_date": "2026-10-02",
  "count": 17, "page": 1, "page_size": 50,
  "results": [
    {
      "event": "ORDER_DISPATCHED",
      "detail": "PARTIAL",
      "occurred_at": "2026-10-01T13:00:00+05:30",
      "source": {"kind": "order", "public_id": "ORD-…", "label": "<client name>"},
      "actor": {"public_id": "…", "name": "…"},
      "bag_pools": [
        {
          "packaging": {"public_id": "PP-…", "packet_weight": "1.000", "packets": 20},
          "on_hand": 10, "reserved": 1, "consumed": 3, "available": 6,
          "change": {"on_hand": 0, "reserved": -3, "consumed": 3, "available": 0}
        }
      ],
      "packet_pools": [
        {
          "packet_weight": "1.000",
          "on_hand": 30, "reserved": 5, "consumed": 0, "available": 25,
          "change": {"on_hand": 0, "reserved": 0, "consumed": 0, "available": 0}
        }
      ],
      "raw_material": {
        "incoming": "500.000", "packed": "230.000", "rejected": "100.000",
        "wasted": "0.000", "available": "270.000",
        "change": {"incoming": "0.000", "packed": "0.000", "rejected": "0.000",
                   "wasted": "0.000", "available": "0.000"}
      },
      "other_materials": [
        {
          "material_type": {"id": 1, "name": "Pouch", "unit_type": "count"},
          "incoming": "1000.000", "packed": "230.000",
          "used_by_other_products": "0.000", "available": "770.000",
          "change": {"incoming": "0.000", "packed": "0.000",
                     "used_by_other_products": "0.000", "available": "0.000"}
        }
      ]
    }
  ]
}
```

- Every row lists **every** pool of the product (full state after the event). `change`
  says what this event moved.
- Quantities: bags and packets are integers; kg and material units are 3-dp strings.
- Event details (order id, client, lot no, party, snapshot id) are joined at read time
  from the source FKs. Nothing descriptive is stored on the ledger.

### Changed

- `PATCH update-bag-stock`, `PATCH update-sample-packet-stock`: carry-forward on a new
  date (§3.5).
- `other-material-stock`, plus every material-availability check (`_assert_material_available`,
  `guard_stock_deletion`, `InwardOperations.other_material_on_hand`): usage now comes from
  recipe layers (§3.4).

## 5. Implementation map

### Schema (raw SQL in `sql/ddl.sql` — there are no migrations)

```sql
CREATE TABLE stock_event (
    id                        bigserial PRIMARY KEY,
    event_type                smallint    NOT NULL,
    detail                    smallint    NOT NULL,
    occurred_at               timestamptz NOT NULL,
    product_id                integer     NOT NULL REFERENCES aggregator_product(id),
    actor_id                  integer     NULL     REFERENCES authentication_user(id),
    order_id                  integer     NULL,
    custom_order_id           integer     NULL,
    inward_raw_material_id    integer     NULL,
    inward_other_material_id  integer     NULL,
    raw_material_waste_id     integer     NULL,
    inventory_snapshot_id     integer     NULL,
    loose_stock_snapshot_id   integer     NULL
);
CREATE INDEX ix_stock_event_product_time ON stock_event (product_id, occurred_at, id);

CREATE TABLE stock_event_line (
    id                    bigserial PRIMARY KEY,
    event_id              bigint   NOT NULL REFERENCES stock_event(id),
    pool_kind             smallint NOT NULL,           -- 1 BAG, 2 LOOSE, 3 RAW, 4 OTHER
    product_packaging_id  integer  NULL,               -- BAG
    packet_weight         numeric(8,3) NULL,           -- LOOSE
    material_type_id      integer  NULL,               -- OTHER
    d_on_hand    numeric(14,3) NULL,
    d_reserved   numeric(14,3) NULL,
    d_consumed   numeric(14,3) NULL,
    d_incoming   numeric(14,3) NULL,
    d_packed     numeric(14,3) NULL,
    d_rejected   numeric(14,3) NULL,
    d_wasted     numeric(14,3) NULL
    -- plus a CHECK that exactly the pool reference matching pool_kind is set
);
CREATE INDEX ix_stock_event_line_event ON stock_event_line (event_id);
CREATE INDEX ix_stock_event_line_material ON stock_event_line (material_type_id, event_id)
    WHERE material_type_id IS NOT NULL;

CREATE TABLE packed_recipe_layer (
    id                       bigserial PRIMARY KEY,
    inventory_snapshot_id    integer NULL,
    loose_stock_snapshot_id  integer NULL,
    material_type_id         integer NOT NULL,
    recipe_id                integer NULL,             -- NULL = packed while no recipe existed
    packets                  integer NOT NULL CHECK (packets > 0),
    opened_at                timestamptz NOT NULL,     -- LIFO order
    CHECK ((inventory_snapshot_id IS NULL) <> (loose_stock_snapshot_id IS NULL))
);
```

(Exact table and column names follow the conventions in `sql/ddl.sql` at implementation
time. All FKs are real FKs there.)

- **Footprint:** one event header plus one line per changed pool per write. Unused
  delta columns are NULL, costing one bitmap bit each. Layers are about one row per
  pool per material type per count day.

### Code

| Area | File |
|---|---|
| Models | `aggregator/models/StockEvent.py`, `StockEventLine.py`, `PackedRecipeLayer.py`, `__init__.py` |
| Recording, positions, classification, report | `aggregator/StockLedgerOperations.py` (new) |
| Carry-forward, layers, `other_material_used`, count-delete | `aggregator/InventoryOperations.py` |
| Wrap transitions | `aggregator/OrderOperations.py`, `aggregator/CustomOrderOperations.py` |
| Inward write functions (moved out of views) | `aggregator/InwardOperations.py` (its "read-only" docstring is updated) |
| Thin views | `api/sales_admin/InwardRawMaterialsView.py`, `UpdateInwardRawMaterialView.py`, `InwardOtherMaterialsView.py`, `UpdateInwardOtherMaterialView.py`, `UpdateRawMaterialWasteView.py`; `android/api/v1/Godown*View.py` |
| Django admin paths | `aggregator/admin.py` |
| Endpoint | `api/sales_admin/ProductStockLedgerView.py` (new), `api/sales_admin/urls.py` |
| Commands | `seed_stock_ledger`, `check_stock_ledger` (compares ledger totals with live figures for every product; exits non-zero on a mismatch) |

### Docs and grouping

- `docs/knowledge-graph.md`: add the data model and URL map entries.
- `docs/api/openapi.yml`: regenerate.
- `common/openapi_tags.py`: group the endpoint with the inventory reports.

## 6. Acceptance criteria

### 6.1 Golden worked example (asserted row by row in `tests/test_stock_ledger_golden.py`)

Setup:
- `PP-1` = 1 kg × 20 packets (20 kg per bag), plus a loose 1 kg pool.
- Recipe A: 1 pouch per 1 kg packet.

A dash in a cell means unchanged.

| # | When | Event | Bags oh/res/con/avail | Loose oh/res/con/avail | Raw inc/packed/rej/waste/avail (kg) | Pouch inc/packed/avail |
|---|---|---|---|---|---|---|
| 1 | D1 09:00 | INWARD IR-1 500 kg → In Use | 0/0/0/0 | 0/0/0/0 | 500/0/0/0/500 | 0/0/0 |
| 2 | D1 09:30 | INWARD IR-2 100 kg → Rejected | – | – | 500/0/100/0/500 | – |
| 3 | D1 09:40 | INWARD 1000 pouches | – | – | – | 1000/0/1000 |
| 4 | D1 10:00 | PACKED bag count 10 | 10/0/0/10 | – | 500/200/100/0/300 | 1000/200/800 |
| 5 | D1 10:05 | PACKED loose count 30 | – | 30/0/0/30 | 500/230/100/0/270 | 1000/230/770 |
| 6 | D1 11:00 | ORDER_CONFIRMED ORD-1, 4 bags | 10/4/0/6 | – | – | – |
| 7 | D1 12:00 | ORDER_CONFIRMED CORD-1, 5 packets | – | 30/5/0/25 | – | – |
| 8 | D1 13:00 | ORDER_DISPATCHED PARTIAL, 3 of 4 bags | 10/1/3/6 | – | – | – |
| 9 | D1 14:00 | RAW_WASTED 20 kg | – | – | 500/230/100/20/250 | – |
| 10 | D2 09:00 | STOCK_COUNTED bags 7 (Δpacked 0) | 7/1/0/6 | – | – | – |
| 11 | D2 10:00 | PACKED bags 9 | 9/1/0/8 | – | 500/270/100/20/210 | 1000/270/730 |
| 12 | D2 11:00 | ORDER_DISPATCHED FULL CORD-1 | – | 30/0/5/25 | – | – |
| 13 | D2 12:00 | Recipe A deleted; B = 2 pouches/packet | *no row* | | | |
| 14 | D2 13:00 | PACKED bags 10 (+20 packets @ B) | 10/1/0/9 | – | 500/290/100/20/190 | 1000/310/690 |
| 15 | D2 14:00 | STOCK_ADJUSTED bags 8 (−40 packets, LIFO: B −20, A −20) | 8/1/0/7 | – | 500/250/100/20/230 | 1000/250/750 |

Checks:
- **Final bag layers:** A 220 packets, B 0 (row removed). Loose layer A 30.
  Pouches used = 220×1 + 30×1 = **250** ✓
- **Raw packed** = (8 counted + 3 dispatched before the D2 count) × 20 + 30 loose
  = **250 kg** ✓
- **Raw available** = 500 − 250 − 20 = **230 kg** ✓ (the 100 kg rejected is never
  available)
- **Row 10:** packed = 10 + 0 before and 7 + 3 after, so Δpacked = 0 → `STOCK_COUNTED`.
  on_hand −3 and consumed −3; available unchanged.
- **Row 12:** the loose latest date is still D1 (counted 10:05); the dispatch on D2 is
  after it, so consumed = 5.
- **A report for D2..D2 opens at:** bags 10/1/3/6, loose 30/5/0/25, raw
  500/230/100/20/250, pouches 1000/230/770.
- **Closing D2:** bags 8/1/0/7, loose 30/0/5/25, raw 500/250/100/20/230, pouches
  1000/250/750.

### 6.2 Tests (all must be green; they follow `docs/testing.md`)

- **`tests/test_stock_ledger_operations.py`**
  - One labelled `subTest` per (event_type, detail), asserting exact deltas, and that
    untouched pools get no line.
  - Order flows: partial dispatch; revert before and after the count on the same day;
    re-dispatch; unverify / hold / reject / withdraw; edits up and down; delivery
    writes no row.
  - Inward and waste: every raw-lot transition, including back-to-lab and delete;
    other-material inward create / edit / delete; waste create / edit / delete.
  - A failed write (`ValueError` on a raw or material shortfall) leaves **zero** ledger
    rows.
- **`tests/test_packed_recipe_layers.py`**
  - Carry-forward of layers; Δ>0; Δ<0 with LIFO across layers.
  - Recipe delete + recreate; a new material type added later; NULL-recipe layers;
    count deletion.
  - Invariant Σ layers ≤ packed; `other_material_used` equals a hand-computed value.
- **`tests/test_stock_count_carry_forward.py`**
  - PATCH on a new day, for bags and loose: unnamed pools keep their physical figure.
  - Available and packed are unchanged; a `CARRIED_FORWARD` row is written.
  - POST still zeroes unnamed packagings.
- **`tests/test_stock_ledger_golden.py`**
  - §6.1 verbatim, including the D2..D2 opening and the closing.
- **`tests/test_stock_ledger_reconciliation.py`**
  - A seeded-random sequence of 200 operations, run through the real operation
    functions.
  - After every step, ledger totals == live figures for every pool of every product.
  - closing(range N) == opening(range N+1).
  - row *k* + change(*k+1*) == row *k+1*.
- **`tests/test_stock_ledger_api.py`**
  - 400 cases (before go-live, range > 31 days, end < start, bad date) and 404
    (unknown / deleted product).
  - Pagination places OPENING / CLOSING correctly.
  - Response keys match the documented serializers (`_documented_keys_mismatches`
    pattern, `tests/test_export_api.py`).
  - Two products sharing a material type: incoming − packed − used_by_other_products
    = available on every row, and the other product's inward is listed.
- **Seed and check commands**
  - `seed_stock_ledger` writes the seed, refuses a second run, and leaves live figures
    unchanged.
  - `check_stock_ledger` exits 0 when in sync and non-zero after a tampered line.
- **Suite-wide guard**
  - An autouse fixture in `tests/conftest.py` asserts ledger == live at the end of every
    DML test that wrote ledger rows, which catches any write path that was missed.
  - An opt-out marker is allowed only for tests that seed through raw ORM on purpose.
  - The `book_raw_material*` helpers in `tests/common.py` go through the operations
    layer.
- **View contract**
  - `"api/sales-admin/product-stock-ledger/<str:public_id>"` is added to
    `EXPECTED_CONTRACTS`.

### 6.3 Ops

- `seed_stock_ledger` then `check_stock_ledger`, run on a Neon branch copy, report no
  mismatch.
- For a busy product over 31 days, the closing row matches the four stock screens.

## 7. Known adjacent defects (mirrored, not fixed)

1. **Revert + re-dispatch around a count.** Take a dispatch made *before* the day's
   count that is reverted and re-dispatched the same day. `dispatched_at` is re-stamped
   after the count, so the bags are subtracted twice (once by the count, once as
   consumed). The ledger mirrors this faithfully.
2. **The partial-dispatch gap stays reserved forever** after the dispatch day. A
   DISPATCHED order cannot be edited, and a revert works only on the same day.
3. **Consumed loose packets read `CustomOrderItem.packets`,** not the challan
   `DispatchEntryItem.quantity`. This is safe only while custom-order dispatch is always
   full.

## 8. Implementation notes

Where the build differs from, or adds to, the sections above:

- **Report module.** The report lives in `aggregator/StockLedgerReport.py`, not in
  `StockLedgerOperations.py`, to keep recording and reading apart.
- **Recipe uniqueness.** §3.4 says a recipe change is delete-old + create-new, but
  the old unique constraint on `(product, material_type, packet_weight)` counted
  deleted rows, so re-creating the same variant was refused (a 400). It now covers
  **live** recipes only (partial unique index; `OtherMaterialRecipe` model,
  `sql/ddl.sql`, the create serializer and `test_other_material_recipe_api.py`
  updated).
- **Table names** follow the Django convention (`aggregator_stockevent`,
  `aggregator_stockeventline`, `aggregator_packedrecipelayer`); ids are `int8`.
- **`used_by_other_products` is derived at read time**, as the sum of other
  products' `d_packed` lines for the same material type, not stored.
- **Seed** writes a `LEDGER_START` event for every product (even an all-zero one),
  because the earliest one is the go-live date. It refuses to run if the ledger
  already holds any event.
- **Django admin.** The count, inward lot, waste and custom-order admins run each
  add/change POST inside one recording. The remaining admins that can edit
  stock-moving rows as a superuser (order lines, dispatch entries) are not wrapped.
- **Not recorded:** raw ORM writes and the `execute-code` page. `check_stock_ledger`
  reports them as a mismatch.
- **Known limitation:** `recording` widens to every product with a pool whenever a
  count opens a new date, which is the expensive case (once a day).
