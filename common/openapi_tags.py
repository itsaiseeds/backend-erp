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
ADMIN_INWARD = "Admin · Inward"
ADMIN_STOCK_COUNT = "Admin · Stock count"
ADMIN_STOCK_LEVELS = "Admin · Stock levels"
ADMIN_MASTER_DATA = "Admin · Master data"
ADMIN_EXPORTS = "Admin · Exports"
ADMIN_UTILITIES = "Admin · Utilities"
ANDROID_AUTH = "Android · Auth"
ANDROID_CLIENTS = "Android · Clients"
ANDROID_ORDERS = "Android · Orders"
ANDROID_CATALOGUE = "Android · Catalogue"
ANDROID_UTILITIES = "Android · Utilities"
DEVELOPER = "Developer tools"

# Swagger renders groups in this order.
OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": ADMIN_AUTH, "description": "Sales-admin website sign-in and session."},
    {"name": ADMIN_USERS, "description": "Admin and sales-person accounts."},
    {"name": ADMIN_CLIENTS, "description": "Client records and verification."},
    {"name": ADMIN_ORDERS, "description": "Order review: verify, hold, reject, edit."},
    {"name": ADMIN_DISPATCH, "description": "Dispatching orders, challans and LR numbers."},
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
    {"name": ANDROID_AUTH, "description": "Sales-person app sign-in and session."},
    {"name": ANDROID_CLIENTS, "description": "The sales person's clients, addresses, transport."},
    {"name": ANDROID_ORDERS, "description": "Placing and listing the sales person's orders."},
    {"name": ANDROID_CATALOGUE, "description": "Products the sales person can sell."},
    {"name": ANDROID_UTILITIES, "description": "Geography look-ups for the app."},
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
    (_route(_ADMIN, "admins", "sales-people"), (ADMIN_USERS,)),
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
        ),
        (ADMIN_ORDERS,),
    ),
    (
        _route(
            _ADMIN, "dispatch-order", "revert-dispatch", "dispatch-challans", "upload-lr-number"
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
        ),
        (ADMIN_INWARD,),
    ),
    (
        _route(
            _ADMIN, "update-bag-stock", "update-sample-packet-stock", "check-todays-inventory"
        ),
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
    (_route(_ADMIN, "export/orders", "export/custom-orders"), (ADMIN_ORDERS, ADMIN_EXPORTS)),
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
    (_route(_ANDROID, "create-multi-select-bag-order", "get-orders"), (ANDROID_ORDERS,)),
    (_route(_ANDROID, "sales-person-catalogue"), (ANDROID_CATALOGUE,)),
    (
        _route(_ANDROID, "utilities/cities", "utilities/countries", "utilities/states"),
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
