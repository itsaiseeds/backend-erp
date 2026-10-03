# [Sales-Person Android App] Push notifications — handoff

**Assignee:** sales-person Android (Flutter) team
**Backend status:** implemented and tested; branch `order-push-notifications`. Pushes arrive once the backend has `FCM_SERVICE_ACCOUNT_JSON` set (see [Backend prerequisites](#backend-prerequisites)).
**Scope:** register the phone for pushes, show them, open the right screen on tap, and show an in-app inbox.

---

## TL;DR

1. Add Firebase Messaging to the app (Firebase project `sales-saiseeds`, package `com.saiseeds.sales`).
2. After every login, and whenever FCM rotates the token, `POST /android/api/v1/devices/register`.
3. Create an Android notification channel with id **`order_updates`** (the backend sends every push to it).
4. On a push tap, read `screen` + `data` from the message and navigate.
5. Optionally build an inbox screen on `GET /android/api/v1/notifications`.

Only **sales persons** get notifications today. Godown managers are not notified and the endpoints below are sales-person-only (godown tokens get `403`).

---

## What triggers a push

Sent to the sales person who **created** the thing an admin acted on.

| Event (`type`) | When | Title | Body example | `screen` | `data` |
|---|---|---|---|---|---|
| `ORDER_CONFIRMED` | Admin verifies the order | Order confirmed | `ORD-X for Acme Seeds was confirmed.` | `order_detail` | `{"order_public_id"}` |
| `ORDER_UNDER_REVIEW` | Admin un-verifies | Order under review | `… is back under review.` | `order_detail` | same |
| `ORDER_ON_HOLD` | Admin puts it on hold | Order on hold | `… was put on hold.` | `order_detail` | same |
| `ORDER_REJECTED` | Admin rejects it | Order rejected | `… was rejected.` | `order_detail` | same |
| `ORDER_DISPATCHED` | Dispatch recorded | Order dispatched | `… has been dispatched.` | `order_detail` | same |
| `ORDER_DISPATCH_REVERTED` | Dispatch reverted | Dispatch reverted | `… had its dispatch reverted.` | `order_detail` | same |
| `ORDER_DELIVERED` | Marked delivered | Order delivered | `… has been delivered.` | `order_detail` | same |
| `CLIENT_VERIFIED` | Admin verifies a client you onboarded | Client verified | `Acme Seeds was verified.` | `client_detail` | `{"client_public_id"}` |
| `RETURN_ACCEPTED` | Admin accepts your return | Return accepted | `RET-X against ORD-X for Acme Seeds was accepted.` | `return_order_detail` | `{"return_order_public_id", "order_public_id"}` |
| `RETURN_REJECTED` | Admin rejects your return | Return rejected | `… was rejected.` | `return_order_detail` | same |

Not notified: un-rejecting a return, reverting an accepted return, admin edits to an order.
`type` is an open set — **ignore unknown `type` / `screen` values gracefully** (show the notification, open the home screen) so new events never need an app release.

---

## Push message format

FCM message with a `notification` block (title + body, shown by the system when the app is in the background) and a `data` block:

```json
{
  "notification": { "title": "Order confirmed", "body": "ORD-ABC for Acme Seeds was confirmed." },
  "data": {
    "type": "ORDER_CONFIRMED",
    "screen": "order_detail",
    "notification_id": "42",
    "data": "{\"order_public_id\": \"ORD-ABC\"}"
  },
  "android": { "priority": "HIGH", "notification": { "channel_id": "order_updates" } }
}
```

- FCM only allows **string** values in `data`, so **`data.data` is a JSON-encoded string** — `jsonDecode(message.data['data'])` gives the map from the table above.
- `notification_id` (string) is the inbox row id; use it to mark the item read when the user opens it.
- `screen` values to map to routes: **`order_detail`**, **`client_detail`**, **`return_order_detail`**. The names are the backend's choice; map them to whatever your routes are called.

Opening a screen from `data`:

| `screen` | Use | Existing endpoint to load it |
|---|---|---|
| `order_detail` | `data.order_public_id` | `GET /android/api/v1/get-orders?public_id=<ORD-…>` |
| `client_detail` | `data.client_public_id` | `GET /android/api/v1/client/<public_id>` |
| `return_order_detail` | `data.return_order_public_id` (+ `data.order_public_id`) | `GET /android/api/v1/get-return-orders?public_id=<RET-…>` or `GET /android/api/v1/return-order/<order_public_id>` |

---

## Endpoints

All under `/android/api/v1/`, bearer token (`Authorization: Token <value>`), sales person only. See `docs/frontend-auth-android.md` for auth, `401` and expiry handling.

### `POST devices/register`

Tell the server which FCM token reaches this user.

```json
{ "fcm_token": "<FirebaseMessaging.instance.getToken()>", "app_version": "1.4.0" }
```

- `fcm_token` required (max 512 chars); `app_version` optional (max 32).
- `204 No Content` on success. `400` if `fcm_token` is missing/blank.
- **Idempotent** — call it freely. A token already registered to another user (shared phone) **moves to the caller**.
- **When to call:** right after every successful login, on app start while logged in, and from `FirebaseMessaging.instance.onTokenRefresh`.

### `POST auth/logout`

Unchanged for the app, but it now also **forgets this user's push tokens** server-side, so a logged-out phone stops receiving their pushes. Always call it on logout (and don't just drop the token locally).

Remember tokens are one-per-user with a fixed 24h life: after a re-login you must call `devices/register` again — the old registration was removed at logout, or the user was logged in elsewhere.

### `GET notifications` — the in-app inbox

Your own notifications, **newest first**. Paginated with the usual envelope (`?page=`, `?page_size=` ≤ 100, `?all=true`):

```json
{
  "total_count": 3, "total_pages": 1, "next_page_number": null, "previous_page_number": null,
  "results": [
    {
      "id": 42,
      "event_type": "ORDER_CONFIRMED",
      "title": "Order confirmed",
      "body": "ORD-ABC for Acme Seeds was confirmed.",
      "screen": "order_detail",
      "data": { "order_public_id": "ORD-ABC" },
      "is_read": false,
      "created_at": "2026-10-03T14:05:11.123456+05:30"
    }
  ],
  "available_filters": [ … ], "available_sorts": []
}
```

- Here `data` is a **real JSON object** (not a string) and `screen`/`data` are exactly what the push carried — one tap handler can serve both the push and the inbox row.
- Filter: `?is_read=false` (unread only), `?is_read=true`. **Badge count = `total_count` of `?is_read=false`.**

### `POST notification/<id>/read` and `POST notifications/read-all`

`204` on success; marking an already-read item is fine. Another user's id is `404`. Call the first when the user opens a notification (use `notification_id` from the push), the second for a "mark all read" action.

---

## App-side checklist

**Firebase / Android project**
- [ ] `google-services.json` (from the Firebase console, package `com.saiseeds.sales`) in `android/app/`.
- [ ] Gradle: `com.google.gms.google-services` plugin version `4.5.0` (`apply false` at project level, applied in the app module). With FlutterFire the Firebase BoM line isn't needed.
- [ ] Packages: `firebase_core`, `firebase_messaging`, `flutter_local_notifications`.
- [ ] Android 13+: request the `POST_NOTIFICATIONS` runtime permission (e.g. after login). If denied, pushes won't show but the inbox still works.

**Notification channel**
- [ ] Create channel id **`order_updates`** (name "Order updates", importance high) at startup. A push naming a channel that doesn't exist is dropped on Android 8+ in some states — the id must match exactly.

**Receiving**
- [ ] Foreground: FCM shows nothing by itself — display a local notification (or an in-app banner) from `FirebaseMessaging.onMessage` using title/body from `message.notification`.
- [ ] Background/terminated tap: handle `FirebaseMessaging.instance.getInitialMessage()` (cold start) and `FirebaseMessaging.onMessageOpenedApp`.
- [ ] Top-level `@pragma('vm:entry-point')` handler for `onBackgroundMessage` if you need work while backgrounded (not required just to show the notification).
- [ ] On tap: `jsonDecode(message.data['data'])`, route by `message.data['screen']`, then `POST notification/<notification_id>/read`.
- [ ] If the user isn't logged in when a push is tapped, log in first and then continue to the target.

**Token lifecycle**
- [ ] `devices/register` after login, on app start, and on `onTokenRefresh`.
- [ ] `auth/logout` on logout.

---

## Gotchas

- **Delivery is best-effort.** The backend saves the inbox row and sends the push after the change commits, on a background thread; if the push fails (phone off, permission denied, token stale) the inbox row is still there. Don't rely on pushes alone — refresh the inbox/badge on app start and resume.
- **Dead tokens are cleaned up automatically** when FCM reports them invalid; just re-register when you get a new token.
- A push can arrive a few seconds **after** the admin action; the order/client/return may already have changed again by the time the user taps. Always load the screen fresh from the API, don't trust the push text.
- Titles/bodies come from the backend — don't build your own text from `type`.
- Unknown `type`/`screen` → open the notifications inbox or home, never crash.

## Backend prerequisites

(Backend team — listed so the app team can tell why nothing arrives.)

- Render env var `FCM_SERVICE_ACCOUNT_JSON` = contents of the `sales-saiseeds` Firebase service-account key. Unset ⇒ pushes are skipped (inbox rows are still written).
- The two new tables `aggregator_pushdevice` and `aggregator_notification` from `sql/ddl.sql` applied to Neon.
- Firebase Cloud Messaging API (V1) enabled for the project.

## Testing it end to end

1. Log in on a phone/emulator with Google Play services, grant notifications, check the app calls `devices/register` (`204`).
2. As an admin (web app), verify one of that sales person's orders → push + inbox row within a few seconds.
3. Tap it from the background and from a killed app; confirm the right screen opens and `GET notifications?is_read=false` drops by one.
4. Log out → verify the phone no longer receives that user's pushes.
5. Swagger: `/api/docs/` → group **Android · Notifications**.
