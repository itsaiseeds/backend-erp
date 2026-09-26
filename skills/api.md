# API & Auth

> How the API layer, authentication, and the CSRF token flow fit together.

---

## Auth model

- Global DRF defaults: `authentication_classes = SessionAuthentication +
  ExpiringTokenAuthentication`, `permission_classes = IsAuthenticated`.
- Both classes live in `api/authentication.py`:
  - `SessionAuthentication` — session-cookie auth for the sales-admin SPA (DRF
    subclass that returns a `WWW-Authenticate` challenge header, keeping
    anonymous callers at **401** instead of DRF's default 403).
  - `ExpiringTokenAuthentication` — bearer-token auth for the Android app;
    rejects tokens older than `TOKEN_TTL_HOURS` (default 24) and **deletes an
    expired token on first use**.
- Pre-auth endpoint (`VerifyOTPView`, TOTP login) opts out with
  `authentication_classes = []` + `permission_classes = [AllowAny]`.
- Client base views pick credentials:
  - `AdminApiView` (sales-admin website) → **session cookie**.
  - `AndroidBaseView` (salesperson Android app) → **bearer token**.
- DRF `APIView` handlers are wrapped in `csrf_exempt`, so the global Django
  `CsrfViewMiddleware` never gates DRF endpoints. CSRF is enforced **only** by
  DRF `SessionAuthentication` (on session-authenticated POST/PUT/PATCH/DELETE).

## Design principles

- **DRY:** every endpoint reuses the shared auth pair (`SessionAuthentication` +
  `ExpiringTokenAuthentication`) and one of the base views (`AdminApiView` /
  `AndroidBaseView`); views only redeclare auth/permission classes when they
  deliberately differ (pre-auth endpoints, superuser/role gates).
- **KISS:** views stay thin — validate with a serializer, then delegate writes
  to the operations layer (`OrderOperations`, `ClientOperations`,
  `UserOperations`).
- **YAGNI:** `android/v1/` is empty on purpose; add endpoints only when a
  client actually needs them.

## CSRF token flow — `get_token(request)` in `VerifyOTPView`

`VerifyOTPView.post` does two things after a successful TOTP check:

1. `login(request, user)` — opens a browser session (`sessionid` cookie).
2. `get_token(request)` — ensures a CSRF token exists and that the **login
   response carries a `Set-Cookie: csrftoken=<value>` header**. The token value
   is *not* included in the JSON body.

How the frontend receives it:

1. The browser auto-stores the `csrftoken` cookie from the login response.
2. The CSRF cookie is **not** `HttpOnly`, so JS/Flutter can read it via
   `document.cookie`.
3. On every later state-changing request the SPA must echo the value back via
   the `X-CSRFToken` header, or DRF `SessionAuthentication` returns 403.

Flutter web (sales-admin SPA) recipe:

```dart
import 'package:web/web.dart' as web;

String? csrfToken() {
  final raw = web.document.cookie ?? '';
  for (final part in raw.split(';')) {
    final kv = part.trim().split('=');
    if (kv.isNotEmpty && kv[0] == 'csrftoken') {
      return kv.sublist(1).join('=');
    }
  }
  return null;
}

// On state-changing requests:
headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
```

`package:http` on web delegates to the browser, so it stores the cookie for you,
but it cannot read cookies back — that is why reading `document.cookie` is
required.

### Alternative (no cookie parsing)

Since `get_token(request)` returns the token value, the backend can also surface
it in the response body — e.g. `"csrf_token": get_token(request)` in the
`VerifyOTPView` payload — so the SPA can grab it straight from the JSON instead
of parsing cookies. Do not mix the two approaches across endpoints.

## Paginated list views (date window + filters + sorting)

For any `GET` list endpoint, subclass one of the two concrete bases instead of
hand-rolling pagination, query-param parsing, filtering or sorting:

- Web: `api.paginated_views.AdminPaginatedDateRangeListView`
  (defaults to `admin_required = True`; tighten with `superuser_required =
  True` or relax by setting `admin_required = False` on the subclass).
- Android: `android.api.paginated_views.AndroidPaginatedDateRangeListView`
  (inherits `salesperson_required = True` from `AndroidBaseView`).

Both compose the private mixin in `common/views/paginated_date_range.py`.

### What a subclass must provide

- `get_queryset(self, request) -> QuerySet` — the base queryset (before the
  window / filters / sort are layered on).
- `serialize_page(self, page_items, request) -> list | dict` — turn one page of
  ORM objects into the JSON payload (project's hand-built-dict style).

### What a subclass may set

| Attr | Default | Meaning |
|---|---|---|
| `date_field` | `"created_at"` | ORM path for the `start_date_time`..`end_date_time` window (`__` lookups ok, e.g. `"order__created_at"`). |
| `enforce_date_range_filters` | `True` | `True` → a request with **neither** bound is a **400**. `False` → served unfiltered. A **partial** pair is always a 400. |
| `queryset_filters` | `()` | Tuple of `ListFilter` (`QuerysetFilter` and/or `RangeFilter`). The ones whose param(s) are present are sanitized and **AND-ed** onto the queryset. |
| `sort_options` | `()` | Tuple of `SortOption`. Client sends `?sort=<-?name,...>` (comma list, `-` = descending). A `pk` tie-breaker is always appended. |
| `default_sort` | `()` | ORM ordering (str or sequence) used when `?sort` is absent. |

`page`, `page_size`, `all`, `sort`, `start_date_time`, `end_date_time` are **reserved** —
no filter param may reuse those names (raises at request time if it does).

### Filters

Every `available_filters` entry carries a **`label`** (human-readable field
name for the widget title, defaulted from the filter name by `humanize()` —
`city_id` -> `City`, `created_by` -> `Created By` — and overridable with
`label=`) and a **`kind`** (`select`, `int`, `text`, `date`, `datetime`,
`date_range`, `datetime_range`, ...) so the frontend picks a widget with no
guessing. Two filter types:

**`QuerysetFilter`** — one param, `?<name>=<v1,v2,...>` (comma list OR-ed):

```python
QuerysetFilter("status_id__in", parse=parse_int, description="...")   # name == ORM lookup
QuerysetFilter(
    "city_id",
    apply=lambda qs, ids: qs.filter(       # custom apply: relation spans / .distinct()
        client_addresses__is_primary=True,
        client_addresses__address__city_id__in=ids,
    ).distinct(),
    options=lambda request: [{"value": c.id, "label": c.name} for c in ...],  # or a static list
    description="...",
)
QuerysetFilter(                            # free-text substring search
    "company_name",
    lookup="company_name__icontains",     # public param name != ORM lookup
    parse=parse_str, multi=False,         # whole value is one term, no comma split
    description="...",
)
```

- multi (default): up to `MAX_FILTER_VALUES` (100) comma-separated values, each
  through `parse` (`parse_int` default, or `parse_str` / `parse_date` /
  `parse_datetime`); duplicates collapsed. `multi=False`: the whole param value
  is one term (a comma is data) — for substring / `__icontains` search.
- empty / unparseable / too many → **400**; **undeclared** param ignored.
- `lookup=` overrides the ORM lookup the default `apply` uses, so the public
  param name stays clean (`company_name`, not `company_name__icontains`).
- `options` (static list or `(request) -> list`) → the eligible `{value, label}`
  choices, echoed on the entry (**no second lookup**) and flips `kind` to
  `select`.

**`RangeFilter`** — the answer for open-ended filters (dates, numbers): a comma
list names a set but can't say *between*, so a range gets a **two-param pair**,
`?<name>_after=` / `?<name>_before=` (inclusive `>=` / `<=`; send either or
both; suffixes configurable, e.g. `("gte", "lte")`):

```python
RangeFilter("created", field="created_at", parse=parse_datetime,
            suffixes=("gte", "lte"), description="...")   # -> ?created_gte= / ?created_lte=
```

The entry carries `params: [<lower>, <upper>]` and `kind: "<type>_range"`.
Inverted bounds → **400**.

### Query contract

- `?page` (default 1), `?page_size` (default 10, max 30).
- `?all=true` (default `false`; bare `?all` also means true) — paging off: every
  row matching the filters in one page of the same envelope (`total_pages: 1`,
  both page numbers `null`); `page` / `page_size` ignored. Bad value → **400**.
- `?<filter>=<csv>` / `?<name>_after=&<name>_before=` per declared filter, AND-ed.
- `?sort=<-?name,...>` per `sort_options`; unknown key → **400**.
- `?start_date_time=` / `?end_date_time=` (ISO 8601) — the built-in window; see
  `enforce_date_range_filters`. Prefer a `RangeFilter` for new views so the
  bound shows up in the catalogue.

Example: `?city_id=12,15&status=VERIFIED&created_gte=2026-01-01T00:00:00Z&sort=-created_at&page=2`

### Response shape

Page-number envelope from `StandardPageNumberPagination`:

```jsonc
{
  "total_count": 37,            // rows matching the query, across every page
  "total_pages": 4,             // at this page_size; always >= 1
  "next_page_number": 3,        // or null on the last page
  "previous_page_number": 1,    // or null on the first page
  "results": [ ... ]
}
```

**plus**, when the view declares them, `available_filters`
(`[{filter, label, kind, description, params?, options?}]`) and
`available_sorts` (`[{sort, label, description}]`) — on **every** response, so
the frontend discovers the contract without a second endpoint. `label` on both
is what the client shows a human; `filter` / `sort` are what it sends back.

### OpenAPI

Feed the view's own catalogues to `list_query_parameters(...)` in
`@extend_schema` so `docs/api/openapi.yml` documents exactly what the view
accepts; regenerate with `bash scripts/run.sh schema`. Type the response with a
serializer whose `available_filters` / `available_sorts` fields reuse
`FilterCatalogueEntrySerializer` / `SortCatalogueEntrySerializer`. Those spell
out `options` as `FilterOptionSerializer` (`{value, label}`) rather than a bare
`DictField` — a free-form dict is what makes Swagger render placeholder
`additionalProp1` keys instead of the real shape.

### Illustrative subclass

```python
_FILTERS = (
    QuerysetFilter("city_id", apply=..., options=..., description="..."),
    QuerysetFilter("status", parse=..., apply=..., options=[...], description="..."),
    RangeFilter("created", field="created_at", parse=parse_datetime,
                suffixes=("gte", "lte"), description="..."),
)
_SORTS = (SortOption("created_at", description="..."), SortOption("company_name", description="..."))

class GetClientsView(AndroidPaginatedDateRangeListView):
    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _FILTERS
    sort_options = _SORTS

    @extend_schema(
        parameters=list_query_parameters(
            queryset_filters=_FILTERS, sort_options=_SORTS, date_window="none"
        ),
        responses={200: ClientListPageSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request):
        return Client.objects.filter(created_by=request.user)

    def serialize_page(self, page_items, request):
        return [client_list_payload(c) for c in page_items]
```

See `android/api/v1/GetClientsView.py` for the real thing.

## Reading clients

| Endpoint | Scope | Payload |
|---|---|---|
| `GET /android/api/v1/get-clients` | the caller's own clients | compact card per client (`client_list_payload` — primary address + primary contact only), paginated / filtered / sorted |
| `GET /android/api/v1/client/<public_id>` | the caller's own clients | one client in full (`client_payload` — core + **every** address / contact / transport agency) |
| `GET /api/sales-admin/client/<public_id>` | **any** client (admin) | same full `client_payload` |

`client_payload` / `client_list_payload` live in `aggregator/ClientOperations.py`;
the detail views are three lines each (`get_object_or_404` + `Response(client_payload(client))`).
`GET /api/sales-admin/get-clients/` is still a 501 stub.

## Reading orders

| Endpoint | Scope | Payload |
|---|---|---|
| `GET /android/api/v1/get-orders` | the caller's **own** orders | compact card per order (`order_list_payload` — client, delivery city, totals, and the bags ordered), paginated / filtered / sorted |
| `GET /api/sales-admin/orders/` | **every** order (admin) | the same card plus the transport agency, the bags, who booked it, who approved it and who onboarded the client |
| `GET /api/sales-admin/order/<public_id>` | **any** order (admin) | the order in full (`order_detail_payload`) — every line, plus the client's own full payload with address and agency ids |

Filters are `?client=` (client public ids), `?product=` (product public ids),
`?city_id=` (delivery city) and `?status=` (order lifecycle code); sorts are
`created_at` (default, newest first) and `price` (the order total). Every
option list is built from the caller's own orders, so the pickers never name a
client, product or city that belongs to another sales person.

The scoping is the queryset itself (`Order.objects.filter(created_by=request.user)`)
— no filter can widen it. `price` is a per-order `Subquery`, not a `Sum` over
the item join, so `?product=` narrowing that join cannot make the sort (or the
card total) count only the matching lines.

`order_payload` / `order_list_payload` / `order_detail_payload` live in
`aggregator/OrderOperations.py`. An order card's `packagings` is one entry per
line -- the **bag** ordered, how many of it, and the product it holds (with
the picture the card renders). The bag is the unit an order is placed in, so
two sizes of the same seed are two entries rather than one product listed
twice. Its `selling_price` is the bag's own list price, not what the order
was charged -- the negotiated figure is on the detail payload's `items`. The admin list adds one more filter,
`?created_by=` (the booking sales person), and its option lists are unscoped —
an admin picks from every sales person, client, product and city.

## The order lifecycle

Six sales-admin verbs move an order between statuses, each with its reversal.
Which statuses a verb may be applied from lives beside the transition itself in
`aggregator/OrderOperations.py` (`VERIFIABLE_STATUS_CODES` and friends, all
derived from `StatusIds`), so the rule holds however the function is reached —
`api/sales_admin/OrderTransitionView.py` is only the shared HTTP shape.

| Verb | From | To |
|---|---|---|
| `POST verify-order/<public_id>` | BOOKED, UNDER_REVIEW, ON_HOLD | CONFIRMED |
| `POST unverify-order/<public_id>` | CONFIRMED | UNDER_REVIEW |
| `POST dispatch-order/<public_id>` | CONFIRMED | DISPATCHED |
| `POST revert-dispatch/<public_id>` | DISPATCHED | CONFIRMED |
| `POST hold-order/<public_id>` | BOOKED, UNDER_REVIEW, CONFIRMED | ON_HOLD |
| `POST reject-order/<public_id>` | BOOKED, UNDER_REVIEW, CONFIRMED, ON_HOLD | REJECTED |

UNDER_REVIEW is verifiable **because** `unverify-order` lands there — otherwise
unverifying would be a one-way trap. REJECTED appears in no `from` set:
rejection is terminal. Only a verified order can be dispatched.

Which kind of dispatch `dispatch-order` records is read off the **order**, not
the request: an order carrying a `transport_agency` goes by that carrier and one
without it goes on our own vehicle -- the same rule `dispatch_mode` reports on
every order payload. An agency dispatch's `lr_number` is **optional**, because
the transporter usually issues the consignment note after collection; it is
stored blank and filled in later by `POST upload-lr-number/<public_id>`. A
private dispatch requires `vehicle_number` and `driver_number`. Fields belonging
to the other kind are refused rather than ignored.

`dispatch-order` also takes `items` � **one lot number per line**, keyed by
`product_packaging_public_id` (the id `GET order/<public_id>` hands back for each
line), which must name every line of the order exactly once. That is what writes
the order's **challan**: a `DispatchEntry` (`DE-�`, one per order) plus a
`DispatchEntryItem` per line. The entry **snapshots** the receiver � the client's
address and primary contact as they stood at dispatch � so a challan reprinted
next year still says what went out with the goods. Re-dispatching an order
rewrites the same entry in place rather than making a second one, so `DE-�` names
that order's challan for as long as the order lives.

## Dispatch challans

`POST /api/sales-admin/upload-lr-number/<public_id>` records the transporter's
consignment note on the order's `DispatchDetails`. **A private dispatch is a
400**: the number identifies a third party's consignment, and when the goods went
on our own vehicle there is no third party to issue one. The challan reads it
through `DispatchEntry.lr_number` rather than storing a second copy.

`GET /api/sales-admin/dispatch-challans/` lists dispatched orders whose challan
is complete, each row being the printable challan itself: our consignor block
(`aggregator/CompanyDetails.py` � placeholder values until the real registration
details land), the snapshotted consignee, a hard-coded HSN code, the Indian
financial year (April�March, so `2026-2027`), the journey and every lot-numbered
line. What "complete" means depends on who carried the goods: an **agency**
dispatch appears only once its LR is recorded, while a **private** one appears
straight away � there is no note to wait for. Either way the order must still
**be** dispatched (DISPATCHED or DELIVERED): `revert-dispatch` rewinds the status
but leaves the dispatch rows attached, so the status is what takes a reverted
order off the list.

Unlike `orders/`, its **date window is required**, and it filters on
`dispatch_entry.dispatched_at` � a challan belongs to the period the goods left
in, not the period the order was booked in. Filter by `?client=` / `?city_id=`
(destination), sort by `dispatch_date` (default, newest first) or `created_at`.

`verify-order` is gated on **today's** stock count being complete and on every
bag having enough available stock; the check and the status change are one
atomic transaction, so a shortfall leaves the order exactly as it was. Holding
or rejecting a CONFIRMED order releases the bags it reserved, with no
bookkeeping — reserved and consumed are derived from `Order.status`, never stored.

`PATCH /api/sales-admin/edit-order/<public_id>` corrects everything else, with
`items` as a declarative list (see below). It is **refused outright once the
order is DISPATCHED or DELIVERED**: the goods have left, so the order is
history. `verified_by` / `verified_at` / `created_by` / `created_at` are not
fields on it at all.

Two rules that are not merely conventions there:

- **the client cannot be changed.** An order belongs to the client it was booked
  for; moving it would invalidate its delivery address, its transport agency and
  the prices its lines were negotiated at. There is no client field, and the
  address and agency are named by *link* id scoped to the order's own client, so
  a foreign one cannot be attached either.
- **`special_comments` accumulates.** Whatever is sent is appended as a new line
  (`OrderOperations.appended_comment`), so a later remark can never erase an
  earlier one; a blank one is a no-op rather than a blank line.

## Client lists are declarative

A client's addresses, contact people and transport agencies are never patched
entry by entry. Whoever writes them (`POST /android/api/v1/create-client`,
`POST /android/api/v1/update-client`, `POST /api/sales-admin/update-client/`)
sends the **complete desired list**, and the `sync_client_*` helpers in
`aggregator/ClientOperations.py` reconcile the link rows against it: entries are
matched by their content, missing ones are unlinked, new ones are created.

Two rules hold on every one of those endpoints:

- each list keeps **at least one** entry;
- exactly one entry is `is_primary` -- forced when the list has a single entry,
  otherwise taken from the caller's flag, defaulting to the first entry.

Who may write what differs by client, not by the contract: a sales person may
only replace the three lists of a client they created, while a sales admin may
also change `company_name` / `company_phone` / `gst_number` on any client.
Status, `verified_by` and `verified_at` belong to
`POST /api/sales-admin/verify-client/` alone.

**Order items follow the same idiom.** `PATCH /api/sales-admin/edit-order/<public_id>`
takes the complete desired `items` list and `sync_order_items` reconciles it,
matching lines by their `product_packaging` -- the natural key the
`uniq_orderitem_order_packaging` constraint already enforces. A line the admin
leaves out is removed; a list must keep at least one entry.

Two traps that constraint sets, both handled in `sync_order_items`:

- it is **not** soft-delete aware, so a packaging removed and later re-added must
  have its original row **restored**, not re-inserted -- a second insert would
  raise `IntegrityError` and surface as a 500 rather than a 400. Existing lines
  are therefore looked up through `OrderItem.all_objects`.
- removal cannot call `SoftDeletedModel.delete()`, which demands the Django
  `delete_<model>` permission no app admin holds. `SoftDeletedModel.mark_deleted(actor)`
  is the shared bypass for every API-maintained table -- it still records
  `deleted_by`, and skips only the permission gate.

## The pre-auth TOTP login POST needs no X-CSRFToken

The verify-OTP POST itself works without a CSRF header: DRF never runs the
global middleware on API routes, and `SessionAuthentication` skips `enforce_csrf`
for unauthenticated requests. A `X-CSRFToken` header is only required once the
request is **session-authenticated**.