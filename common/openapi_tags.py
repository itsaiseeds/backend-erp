"""Swagger / OpenAPI grouping: which tag(s) each endpoint is listed under.

Only the *documentation* grouping lives here -- URLs and views are untouched.
:class:`common.openapi.GroupedAutoSchema` looks each operation's path up in
:data:`ROUTE_TAGS` (first match wins); :data:`OPENAPI_TAGS` is the ordered tag
list (with descriptions) Swagger UI renders the groups in.

A new endpoint must be added to :data:`ROUTE_TAGS`;
``tests/test_openapi_tags.py`` fails for any operation left ungrouped.

Kept free of Django / DRF imports so ``config.settings`` can import it.
"""

from __future__ import annotations

import re

ADMIN_AUTH = "Admin · Auth"
ADMIN_USERS = "Admin · Users"
ADMIN_CLIENTS = "Admin · Clients"
ADMIN_ORDERS = "Admin · Orders"
ADMIN_DISPATCH = "Admin · Dispatch"
ADMIN_FIELD_TRIPS = "Admin · Field trips"
ADMIN_INWARD = "Admin · Inward"
ADMIN_STOCK_COUNT = "Admin · Stock count"
ADMIN_STOCK_LEVELS = "Admin · Stock levels"
ADMIN_MASTER_DATA = "Admin · Master data"
ADMIN_EXPORTS = "Admin · Exports"
ADMIN_UTILITIES = "Admin · Utilities"
ANDROID_AUTH = "Android · Auth"
ANDROID_CLIENTS = "Android · Clients"
ANDROID_ORDERS = "Android · Orders"
ANDROID_NOTIFICATIONS = "Android · Notifications"
ANDROID_CATALOGUE = "Android · Catalogue"
ANDROID_FIELD_TRIPS = "Android · Field trips"
ANDROID_GODOWN = "Android · Godown"
ANDROID_LAB = "Android · Lab"
ANDROID_UTILITIES = "Android · Utilities"
DEVELOPER = "Developer tools"

# Swagger renders groups in this order.
OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": ADMIN_AUTH, "description": "Sales-admin website sign-in and session."},
    {
        "name": ADMIN_USERS,
        "description": "Admin, sales-person, godown-manager and lab-tester accounts.",
    },
    {"name": ADMIN_CLIENTS, "description": "Client records and verification."},
    {
        "name": ADMIN_ORDERS,
        "description": "Order review: verify, hold, reject, edit; and client returns.",
    },
    {"name": ADMIN_DISPATCH, "description": "Dispatching orders, challans and LR numbers."},
    {
        "name": ADMIN_FIELD_TRIPS,
        "description": "Sales people's field trips: review, edit, approve, and the farmers met.",
    },
    {
        "name": ADMIN_INWARD,
        "description": "Inward movement: raw and other material received into stock.",
    },
    {
        "name": ADMIN_STOCK_COUNT,
        "description": "Daily bag and sample-packet stock counts.",
    },
    {
        "name": ADMIN_STOCK_LEVELS,
        "description": "Read-only current stock positions (bags, packets, materials).",
    },
    {
        "name": ADMIN_MASTER_DATA,
        "description": "Crops, products, packagings, material types, recipes and parties.",
    },
    {
        "name": ADMIN_EXPORTS,
        "description": "Report exports; each also appears under its own domain group.",
    },
    {"name": ADMIN_UTILITIES, "description": "Geography look-ups for the admin website."},
    {"name": ANDROID_AUTH, "description": "Android app sign-in and session (either role)."},
    {"name": ANDROID_CLIENTS, "description": "The sales person's clients, addresses, transport."},
    {
        "name": ANDROID_ORDERS,
        "description": "Placing and listing the sales person's orders, and their returns.",
    },
    {
        "name": ANDROID_NOTIFICATIONS,
        "description": "Push-notification device registration and the in-app inbox.",
    },
    {"name": ANDROID_CATALOGUE, "description": "Products the sales person can sell."},
    {
        "name": ANDROID_FIELD_TRIPS,
        "description": "Planning, running and ending field trips, and recording farmers met.",
    },
    {
        "name": ANDROID_GODOWN,
        "description": "Godown manager: inward lots, stock positions and recipes.",
    },
    {
        "name": ANDROID_LAB,
        "description": "Lab tester: lots waiting for a test, and submitting / editing lab tests.",
    },
    {
        "name": ANDROID_UTILITIES,
        "description": (
            "Look-ups for the app (either role): geography, crops, products, "
            "parties, material types and sales-admin contacts."
        ),
    },
    {"name": DEVELOPER, "description": "Internal debugging endpoints."},
]

_ADMIN = "/api/sales-admin/"
_ADMIN_UTILITIES = "/api/utilities/"
_ANDROID = "/android/api/v1/"


def _route(base: str, *segments: str) -> re.Pattern[str]:
    """Match ``base`` followed by any of ``segments`` as a whole path segment."""
    names = "|".join(re.escape(segment) for segment in segments)
    return re.compile(rf"^{re.escape(base)}(?:{names})(?:/|$)")


# (path pattern, tags) -- checked in order, first match wins.
ROUTE_TAGS: list[tuple[re.Pattern[str], tuple[str, ...]]] = [
    # -- sales-admin website ------------------------------------------------
    (_route(_ADMIN, "auth"), (ADMIN_AUTH,)),
    (_route(_ADMIN_UTILITIES, "reauthenticate"), (ADMIN_AUTH,)),
    (_route(_ADMIN, "admins", "sales-people", "godown-managers", "lab-testers"), (ADMIN_USERS,)),
    (
        _route(_ADMIN, "client", "get-clients", "update-client", "verify-client"),
        (ADMIN_CLIENTS,),
    ),
    (
        _route(
            _ADMIN,
            "order",
            "orders",
            "edit-order",
            "hold-order",
            "reject-order",
            "unverify-order",
            "verify-order",
            "custom-order",
            "custom-orders",
            "create-custom-order",
            "edit-custom-order",
            "return-orders",
            "edit-return-order",
            "return-order-recipes",
            "accept-return-order",
            "reject-return-order",
            "unreject-return-order",
            "revert-accept-return-order",
        ),
        (ADMIN_ORDERS,),
    ),
    (
        _route(
            _ADMIN,
            "dispatch-order",
            "revert-dispatch",
            "dispatch-challans",
            "dispatch-lot-numbers",
            "upload-lr-number",
            "dispatch-custom-order",
            "revert-custom-order-dispatch",
        ),
        (ADMIN_DISPATCH,),
    ),
    (
        _route(
            _ADMIN,
            "inward-raw-material",
            "inward-raw-materials",
            "inward-other-material",
            "inward-other-materials",
            "raw-material-waste",
            "raw-material-wastes",
            "lab-testing",
            "lab-testings",
            "non-stock-inward",
            "non-stock-inwards",
        ),
        (ADMIN_INWARD,),
    ),
    (
        _route(_ADMIN, "update-bag-stock", "update-sample-packet-stock", "check-todays-inventory"),
        (ADMIN_STOCK_COUNT,),
    ),
    (
        _route(
            _ADMIN,
            "bag-stock",
            "sample-packet-stock",
            "get-stock",
            "raw-material-stock",
            "other-material-stock",
            "product-stock-ledger",
        ),
        (ADMIN_STOCK_LEVELS,),
    ),
    (
        _route(
            _ADMIN,
            "crops",
            "products",
            "product-packagings",
            "other-material-types",
            "other-material-recipe",
            "other-material-recipes",
            "parties",
        ),
        (ADMIN_MASTER_DATA,),
    ),
    (
        _route(
            _ADMIN,
            "field-trip",
            "field-trips",
            "field-trip-farmer-visits",
            "edit-field-trip",
            "approve-field-trip",
            "unapprove-field-trip",
            "farmers",
        ),
        (ADMIN_FIELD_TRIPS,),
    ),
    (_route(_ADMIN, "export/orders", "export/custom-orders"), (ADMIN_ORDERS, ADMIN_EXPORTS)),
    (_route(_ADMIN, "export/farmer-visits"), (ADMIN_FIELD_TRIPS, ADMIN_EXPORTS)),
    (_route(_ADMIN, "export/dispatch-receipts"), (ADMIN_DISPATCH, ADMIN_EXPORTS)),
    (_route(_ADMIN, "export/inward-entries"), (ADMIN_INWARD, ADMIN_EXPORTS)),
    (_route(_ADMIN, "export/inventory-snapshots"), (ADMIN_STOCK_COUNT, ADMIN_EXPORTS)),
    (_route(_ADMIN_UTILITIES, "cities", "countries", "states"), (ADMIN_UTILITIES,)),
    # -- android app ------------------------------------------------------------
    (_route(_ANDROID, "auth"), (ANDROID_AUTH,)),
    (
        _route(
            _ANDROID,
            "client",
            "create-client",
            "get-clients",
            "update-client",
            "utilities/client-addresses",
            "utilities/client-transport-agencies",
        ),
        (ANDROID_CLIENTS,),
    ),
    (
        _route(
            _ANDROID,
            "create-multi-select-bag-order",
            "get-orders",
            "analytics",
            "return-order",
            "get-return-orders",
            "get-challans",
            "get-challan",
        ),
        (ANDROID_ORDERS,),
    ),
    (
        _route(_ANDROID, "devices", "notifications", "notification"),
        (ANDROID_NOTIFICATIONS,),
    ),
    (_route(_ANDROID, "sales-person-catalogue"), (ANDROID_CATALOGUE,)),
    (_route(_ANDROID, "godown"), (ANDROID_GODOWN,)),
    (_route(_ANDROID, "lab"), (ANDROID_LAB,)),
    (
        _route(
            _ANDROID,
            "create-field-trip",
            "get-field-trips",
            "edit-field-trip",
            "start-field-trip",
            "end-field-trip",
            "delete-field-trip",
            "field-trip-farmer-visits",
            "create-farmer-visit",
            "edit-farmer-visit",
        ),
        (ANDROID_FIELD_TRIPS,),
    ),
    (
        _route(
            _ANDROID,
            "utilities/cities",
            "utilities/countries",
            "utilities/states",
            "utilities/crops",
            "utilities/products",
            "utilities/parties",
            "utilities/other-material-types",
            "utilities/sales-admins",
        ),
        (ANDROID_UTILITIES,),
    ),
    # -- internal -----------------------------------------------------------------
    (_route("/api/", "execute-code", "test-sentry"), (DEVELOPER,)),
]


def tags_for_path(path: str) -> tuple[str, ...] | None:
    """The tags for ``path`` (an OpenAPI path like ``/api/sales-admin/crops``),
    or ``None`` when no rule covers it."""
    for pattern, tags in ROUTE_TAGS:
        if pattern.match(path):
            return tags
    return None
