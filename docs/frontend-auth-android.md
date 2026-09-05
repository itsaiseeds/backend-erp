# [Sales-Person Android App] Auth handling — bearer-token flow

**Assignee:** sales-person Android team
**Scope:** how to log in, stay logged in, log out, and handle expiry on the sales-person Android app.

---

## TL;DR

The Android app authenticates via a **bearer token** in the `Authorization` header. There are **no cookies** anywhere in the app flow. The token is opaque, has a **fixed 24-hour lifetime from login**, and the app is responsible for:

1. Sending phone + TOTP on login and storing the returned token securely.
2. Attaching `Authorization: Token <value>` on every subsequent request.
3. Routing the user back to login on `401` and clearing the stored token.

No cookies. No CSRF header. No refresh token (a fresh login gives a fresh token).

---

## The mental model

- **Login returns a token, not a cookie.** The app stores it and echoes it on every later call.
- **One token per user, ever.** Logging in on device B invalidates the token on device A — the server deletes the old row and creates a new one on every successful login. If a user swaps phones, the old phone will start getting `401`s on its next request; that is expected. Route it back to the login screen.
- **Fixed 24-hour lifetime**, measured from the moment the token was issued. **Not sliding** — making requests does not extend it. A token issued at `T` is dead at `T + 24h` regardless of usage, and the very request that finds it expired also causes the server to delete it. There is no refresh flow; expired means the user must log in again.
- **Android never touches sessions.** Do not send cookies. Do not call any URL that starts with `/api/sales_admin/…` or `/api/utilities/…` — those are session-only and will refuse a bearer token.

---

## Endpoints

Base URL is the same host the web app talks to (e.g. `https://api.example.com`).

The Android app is served under `/android/api/<version>/…`. **`v1` is the current version.** Every version inherits everything from earlier versions, so a route introduced at `v1` is also served at `v2`, `v3`, … unless a later version deliberately overrides it. Use `v1` for now; bump to a newer version only when this doc says so.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/android/api/v1/auth/login` | Login: exchange phone + TOTP → bearer token |
| `POST` | `/android/api/v1/auth/logout` | Logout: revoke the token server-side |
| `GET`  | `/android/api/v1/auth/reauthenticate` | On startup / resume, "is my token still valid?" |
| `GET`  | `/android/api/v1/utilities/cities` | Grouped state → city picker data |

More endpoints will land here as the app grows. All of them will follow the same `Authorization: Token …` rules.

---

## 1. Login

```
POST /android/api/v1/auth/login
Content-Type: application/json

{"phone_number": "7777777777", "otp": "123456"}
```

**Success (200):**

```json
{
  "token": "b1a2c3d4e5f6…",
  "user": {
    "id": 42,
    "name": "Salesperson Name",
    "phone_number": "7777777777",
    "role": "salesperson"
  }
}
```

**Store `token` securely** — Android Keystore, `EncryptedSharedPreferences`, or your platform's secure-storage equivalent. Do **not** put it in plain `SharedPreferences`, in a file, or in a log line.

**Failure (400):** `{"detail": "Invalid phone number or TOTP code."}` — same generic body whether the phone is unknown, the account isn't a sales-person, the code is wrong, or the account is locked. Do not try to distinguish them from the client.

**Rate limit (429):** the endpoint is throttled per source IP. Surface a "Too many attempts, try again later" message.

---

## 2. Every subsequent request

Attach the token on every call:

```
Authorization: Token b1a2c3d4e5f6…
```

Note the scheme is the literal word **`Token`** followed by a space and the token value — not `Bearer`.

OkHttp interceptor sketch (Kotlin):

```kotlin
class AuthInterceptor(private val tokenStore: TokenStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = tokenStore.read() ?: return chain.proceed(chain.request())
        val req = chain.request().newBuilder()
            .header("Authorization", "Token $token")
            .build()
        return chain.proceed(req)
    }
}
```

Register the interceptor on the single `OkHttpClient` you share across the app. No CSRF header. No cookie jar.

---

## 3. Startup / resume — is the token still valid?

Call **once** on app boot (and on app resume from background if you want that behavior):

```
GET /android/api/v1/auth/reauthenticate
Authorization: Token <stored>
```

- `200` with `{"user": {...}}` → token valid; hydrate state and go to the home screen.
- `401` → token expired or was revoked (e.g. the user logged in on another device, or an admin soft-deleted their sales-person profile). **Clear the stored token** and show the login screen.

The server auto-deletes expired tokens on the request that discovers them, so no client-side cleanup call is needed for expired-token hygiene.

---

## 4. Logout

```
POST /android/api/v1/auth/logout
Authorization: Token <stored>
```

- `204 No Content` on success. The server deletes the token row so any further request with it gets `401`.
- Regardless of the response (success, network error, 401 because it was already gone), **clear the stored token locally** and navigate to the login screen. Logout must be idempotent from the user's perspective.

---

## 5. Handling 401 anywhere else

Any endpoint that returns `401` on an authenticated request means the token is no longer valid. The correct handling is universal:

1. Clear the stored token from secure storage.
2. Drop all in-memory user state.
3. Navigate to the login screen.
4. Do **not** retry the request, and do **not** attempt to refresh — there is no refresh flow.

---

## 6. Errors you should surface

| Status | Meaning | UX |
|---|---|---|
| `400` on login | wrong phone / OTP / locked / not a sales-person | Show the generic message from `detail` |
| `401` anywhere else | token dead | Clear token + kick to login |
| `403` | authenticated but not authorized (e.g. account lost its sales-person profile) | Show "your account no longer has access" and kick to login |
| `429` | rate-limited (login only) | Show retry-later message |
| `5xx` | server error | Generic error toast |

---

## Definition of done

- [ ] Login stores the returned `token` in secure storage (Keystore-backed).
- [ ] Every non-login request goes through an interceptor that adds `Authorization: Token <value>`.
- [ ] The scheme name is exactly `Token`, not `Bearer`.
- [ ] App boot calls `GET /android/api/v1/auth/reauthenticate` and routes based on `200` vs `401`.
- [ ] Logout call is made, then local token is cleared **whatever the response**.
- [ ] Any `401` on a business call clears the stored token and returns the user to the login screen.
- [ ] No cookie jar is attached to the HTTP client; no `Cookie` header is ever sent.
- [ ] The token never appears in a log line, crash report, or analytics event.

---

## Out of scope (do not touch)

- The sales-admin website has an entirely separate flow — see [`frontend-auth-sales-admin.md`](./frontend-auth-sales-admin.md). Do not touch anything under `/api/sales_admin/…` or `/api/utilities/…`; those refuse bearer tokens.
- There is no `refresh_token` endpoint. A user whose 24-hour window has elapsed re-logs in with phone + TOTP; that's the entire refresh flow.
