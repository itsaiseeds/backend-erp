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

## Paginated date-range list views

For any `GET` list endpoint whose results must be filtered by a required
`start_date_time`..`end_date_time` window (on the object's own `created_at`,
or on a related object's timestamp), subclass one of the two concrete bases
instead of hand-rolling pagination and query-param parsing:

- Web: `api.paginated_views.AdminPaginatedDateRangeListView`
  (defaults to `admin_required = True`; tighten with `superuser_required =
  True` or relax by setting `admin_required = False` on the subclass).
- Android: `android.api.paginated_views.AndroidPaginatedDateRangeListView`
  (inherits `salesperson_required = True` from `AndroidBaseView`).

Both compose the private mixin in
`common/views/paginated_date_range.py` and only override `get()`.

### What a subclass must provide

- `get_queryset(self, request) -> QuerySet` — the base queryset (pre
  date-filter).
- `serialize_page(self, page_items, request) -> list | dict` — turn one
  page of ORM objects into the JSON payload (project's hand-built-dict style).
- Optional `date_field` (default `"created_at"`) — the ORM path used for the
  range filter, supports Django `__` lookups for related fields, e.g.
  `date_field = "order__created_at"`.

### Query contract

- `start_date_time` and `end_date_time` (ISO 8601) are **required**; missing,
  invalid, or `start > end` returns **400**.
- `page` (default `1`) and `page_size` (default `10`, capped at `30`) are
  optional.

### Response shape

DRF standard envelope: `{count, next, previous, results}` (from
`StandardPageNumberPagination`).

### Minimal subclass (illustrative)

```python
from api.paginated_views import AdminPaginatedDateRangeListView

class OrdersView(AdminPaginatedDateRangeListView):
    # date_field defaults to "created_at" — override for related lookups.
    def get_queryset(self, request):
        return Order.objects.select_related("customer").order_by("-id")

    def serialize_page(self, page_items, request):
        return [order_payload(o) for o in page_items]
```

## The pre-auth TOTP login POST needs no X-CSRFToken

The verify-OTP POST itself works without a CSRF header: DRF never runs the
global middleware on API routes, and `SessionAuthentication` skips `enforce_csrf`
for unauthenticated requests. A `X-CSRFToken` header is only required once the
request is **session-authenticated**.