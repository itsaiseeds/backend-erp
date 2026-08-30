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

## The pre-auth TOTP login POST needs no X-CSRFToken

The verify-OTP POST itself works without a CSRF header: DRF never runs the
global middleware on API routes, and `SessionAuthentication` skips `enforce_csrf`
for unauthenticated requests. A `X-CSRFToken` header is only required once the
request is **session-authenticated**.