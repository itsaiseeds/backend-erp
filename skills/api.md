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

`page`, `page_size`, `sort`, `start_date_time`, `end_date_time` are **reserved** —
no filter param may reuse those names (raises at request time if it does).

### Filters

Every `available_filters` entry carries a **`kind`** (`select`, `int`, `text`,
`date`, `datetime`, `date_range`, `datetime_range`, ...) so the frontend picks a
widget with no guessing. Two filter types:

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
```

- up to `MAX_FILTER_VALUES` (100) values, each through `parse` (`parse_int`
  default, or `parse_str` / `parse_date` / `parse_datetime`); empty /
  unparseable / too many → **400**; duplicates collapsed; **undeclared** param
  ignored.
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
- `?<filter>=<csv>` / `?<name>_after=&<name>_before=` per declared filter, AND-ed.
- `?sort=<-?name,...>` per `sort_options`; unknown key → **400**.
- `?start_date_time=` / `?end_date_time=` (ISO 8601) — the built-in window; see
  `enforce_date_range_filters`. Prefer a `RangeFilter` for new views so the
  bound shows up in the catalogue.

Example: `?city_id=12,15&status=VERIFIED&created_gte=2026-01-01T00:00:00Z&sort=-created_at&page=2`

### Response shape

DRF envelope `{count, next, previous, results}` **plus**, when the view declares
them, `available_filters` (`[{filter, kind, description, params?, options?}]`)
and `available_sorts` (`[{sort, description}]`) — on **every** response, so the
frontend discovers the contract without a second endpoint.

### OpenAPI

Feed the view's own catalogues to `list_query_parameters(...)` in
`@extend_schema` so `docs/api/openapi.yml` documents exactly what the view
accepts; regenerate with `bash scripts/run.sh schema`. Type the response with a
serializer whose `available_filters` / `available_sorts` fields reuse
`FilterCatalogueEntrySerializer` / `SortCatalogueEntrySerializer`.

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

## The pre-auth TOTP login POST needs no X-CSRFToken

The verify-OTP POST itself works without a CSRF header: DRF never runs the
global middleware on API routes, and `SessionAuthentication` skips `enforce_csrf`
for unauthenticated requests. A `X-CSRFToken` header is only required once the
request is **session-authenticated**.