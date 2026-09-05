# [Sales Admin Web] Auth handling — session-cookie flow

**Assignee:** sales-admin web team
**Scope:** how to log in, stay logged in, log out, and handle expiry on the Flutter web app.

---

## TL;DR

The sales-admin website authenticates via a **browser session cookie**. There is **no token** anywhere in the web flow. The server sets and reads the cookie itself — the app only has to:

1. Send credentials on the login call.
2. Send cookies + the CSRF header on every mutating request afterwards.
3. Route the user back to the login screen on `401`.

No local storage of any auth material. No `Authorization` header. No token to refresh.

---

## The mental model

- **Login sets a cookie**, not returns a token. The response body carries only the user payload — do not look for a `token` field, it is gone.
- **Two cookies are set** on successful login:
  - `sessionid` — HttpOnly (invisible to JavaScript), sent by the browser automatically.
  - `csrftoken` — readable by JS; you echo it back on every non-GET request as `X-CSRFToken`.
- **Session lifetime is fixed at 24 hours from login**, not sliding. Making authenticated requests does not extend it. After 24 h the session is dead and the user must re-login.
- **One session per browser context.** Logging in a second time from the same origin replaces the previous session (Django rotates the `session_key`).

---

## Endpoints

Base URL is whatever `API_BASE_URL` resolves to at build time (e.g. `http://localhost:8000` in dev).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sales_admin/auth/otp/verify` | Login: exchange phone + TOTP → session cookie |
| `POST` | `/api/sales_admin/auth/logout` | Logout: flush session |
| `GET`  | `/api/utilities/reauthenticate` | On startup / resume, "is my cookie still valid?" |
| `GET/POST` | `/api/sales_admin/admins` | List / create app admins (superuser only) |
| `PATCH/DELETE` | `/api/sales_admin/admins/<id>` | Update / delete an admin (superuser only) |
| `GET/POST` | `/api/sales_admin/sales-people` | List / create sales-people (admin only) |
| `PATCH/DELETE` | `/api/sales_admin/sales-people/<id>` | Update / delete a sales-person (admin only) |
| `GET`  | `/api/utilities/cities` | Grouped state → city picker data (superuser only) |

Anything not listed here that lives under `/api/sales_admin/…` or `/api/utilities/…` follows the same session rules.

---

## 1. Login

```
POST /api/sales_admin/auth/otp/verify
Content-Type: application/json

{"phone_number": "9999999999", "otp": "123456"}
```

**Success (200)** — response body carries **only** the user payload:

```json
{
  "user": {
    "id": 1,
    "name": "Admin Name",
    "phone_number": "9999999999",
    "role": "superuser"
  },
  "can_create_admin": true,
  "can_create_sales_person": true
}
```

Response headers set two cookies:

```
Set-Cookie: sessionid=<opaque>; Max-Age=86400; HttpOnly; Path=/
Set-Cookie: csrftoken=<opaque>;  Max-Age=…;    Path=/
```

**Failure (400):** `{"detail": "Invalid phone number or TOTP code."}` — same generic body whether the phone is unknown, the code is wrong, or the account is locked. Do not try to distinguish them from the client.

**Rate limit (429):** the endpoint is throttled per source IP. Surface a "Too many attempts, try again later" message.

---

## 2. Every subsequent request

**GET requests:** cookies are sent automatically by the browser. Nothing to do.

**POST / PATCH / DELETE:** you must:

- Ensure the browser sends the cookie (for cross-origin fetch: `credentials: 'include'`; for `dart:http` on web this means using `BrowserClient` with `withCredentials = true`).
- Read the `csrftoken` cookie value and echo it in the `X-CSRFToken` request header.

Skeleton (Dart):

```dart
final csrf = _readCookie('csrftoken'); // small helper: parse document.cookie
final resp = await httpClient.post(
  uri,
  headers: {
    'Content-Type': 'application/json',
    if (csrf != null) 'X-CSRFToken': csrf,
  },
  body: jsonEncode(payload),
);
```

If you send a non-GET without `X-CSRFToken`, the server returns **403 with `CSRF Failed`** — that is not a permission problem, it is a missing header.

---

## 3. Startup / resume — is the session still valid?

Call **once** on app boot (and on tab refocus if you want that behavior):

```
GET /api/utilities/reauthenticate
```

- `200` with the user payload → session valid; hydrate state and go straight to the home screen.
- `401` → session expired or was revoked; drop client state and show the login screen.

The response body has the same shape as login's, including `can_create_admin` / `can_create_sales_person`, so treat it as an authoritative refresh of the user's capabilities (an admin who was demoted mid-session will see the updated flags on the next reauth).

---

## 4. Logout

```
POST /api/sales_admin/auth/logout
```

- `204 No Content` on success. The server flushes the session row and clears the cookie via `Set-Cookie: sessionid=; Max-Age=0`.
- Drop all client-side auth state and navigate to the login screen.
- Send the CSRF header (see §2).

The current app's "Sign out" button just navigates to the login screen locally; it **must** be updated to call this endpoint, otherwise the session lives on the server for the rest of the 24-hour window and a shared browser can still hit the API with the residual cookie.

---

## 5. Handling 401 anywhere else

Any endpoint that returns `401` on an authenticated request means the session is no longer valid (expired, revoked, or manually logged out from elsewhere). The correct handling is universal:

1. Drop all in-memory user state.
2. Navigate to the login screen.
3. Do **not** retry the request.

There is no refresh token and no silent-renewal flow — expired means expired.

---

## 6. Errors you should surface

| Status | Meaning | UX |
|---|---|---|
| `400` on login | wrong phone / OTP / locked | Show the generic message from `detail` |
| `401` anywhere else | session dead | Kick to login screen |
| `403` | CSRF missing, or role gate (e.g. non-superuser hitting an admin-only route) | Show a "you do not have permission" message |
| `404` on a `<id>` route | target soft-deleted or never existed | Show "not found" |
| `429` | rate-limited (login only) | Show retry-later message |
| `5xx` | server error | Generic error toast |

---

## Definition of done

- [ ] Login call reads only `user` / capability booleans; no `token` field is referenced anywhere.
- [ ] All non-GET calls send `X-CSRFToken` sourced from the `csrftoken` cookie.
- [ ] `BrowserClient.withCredentials = true` (or equivalent) is set so cookies are sent cross-origin.
- [ ] App boot calls `GET /api/utilities/reauthenticate` and routes based on `200` vs `401`.
- [ ] Sign-out button calls `POST /api/sales_admin/auth/logout` **before** navigating away.
- [ ] Any `401` on a business call kicks the user back to login.
- [ ] No token is stored in `localStorage`, `sessionStorage`, or in-memory state.

---

## Out of scope (do not touch)

- The Android app has an entirely separate flow — see [`frontend-auth-android.md`](./frontend-auth-android.md). Do not import token logic from there.
- The `authtoken_token` table and DRF `Token` model are Android-only. The web must never send an `Authorization: Token …` header.
