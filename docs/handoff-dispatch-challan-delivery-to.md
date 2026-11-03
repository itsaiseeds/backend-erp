# [Sales Admin Flutter + Android] Per-dispatch `delivery_to` on the delivery challan

**Assignee:** sales-admin Flutter team, Android team
**Scope:** the "To" printed on a delivery challan is now chosen per dispatch.

---

## What changed

Each dispatch can now carry its own `delivery_to` — the "To" printed on the delivery challan. Until now it was read from the address (`Address.delivery_to`), so it was shared by every order for that address.

The value is stored on the dispatch record and **snapshotted on the challan**, so a reprinted challan always shows what went out with the goods.

---

## Request (sales-admin only)

A new optional field on four endpoints:

| Endpoint | Field |
|---|---|
| `POST /api/sales-admin/dispatch-order/<public_id>` | `delivery_to` |
| `POST /api/sales-admin/dispatch-custom-order/<public_id>` | `delivery_to` |
| `POST /api/sales-admin/dispatch-waste-order/<public_id>` | `delivery_to` |
| `POST /api/sales-admin/create-rejected-order` | `delivery_to` |

- Type: `string | null`, max 255, optional.
- If it is omitted, `null` or blank, the server uses the **booked-for party's address `delivery_to`** when the order has `booked_for`, else the **order's delivery address `delivery_to`**. That is exactly what the challan printed before this change.
- A re-dispatch (revert, then dispatch again) takes the value again; send it again if it should differ.

**Flutter UI:** in `order_dispatch_dialog.dart` (and the custom, waste and rejected dispatch forms), make the existing read-only Delivery-to field editable. Prefill it with the same default and send it in the payload. Remove the "dispatch endpoint has no `delivery_to` field" comment.

---

## Response — every challan payload

Applies to the sales-admin challan list (`GET /api/sales-admin/dispatch-challans/`), the dispatch-receipt export (`/api/sales-admin/export/dispatch-receipts`), and the Android challan endpoints (`get-challans`, `get-challan/<order_public_id>`).

```json
"dispatch": { "...": "...", "delivery_to": "Navkar Roadlines, Surat" }
```

- Always a non-empty string. Legacy challans fall back, on the server, to the same default as above.
- `receiver_details.address.delivery_to` and `booked_for.address.delivery_to` still exist, but they are the **address's own** values. Read the challan's "To" from **`dispatch.delivery_to`**.

### Flutter

Add `deliveryTo` to the challan dispatch model and change the `deliveryTo` getter in `dispatch_challan_model.dart` to prefer `dispatch.deliveryTo`, keeping the current logic as a fallback for older servers. Do the same in `challan_generator.dart` and `dispatch_challans_table.dart`.

### Android

No request change: Android does not dispatch. Print the challan's "To" from `dispatch.delivery_to`.

---

## Rollout

The change is additive and backward compatible. Old clients keep working, and the backend can ship first.

The database needs `sql/migrations/2026-11-03_dispatch_delivery_to.sql` run once before the backend is deployed.
