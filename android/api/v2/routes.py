"""Routes introduced or changed at Android API v2.

Everything not listed here is inherited from v1 (see ``android.api.routing``).
"""

from __future__ import annotations

from .ReturnOrderView import ReturnOrderView

ROUTES = {
    "return-order/<order_public_id>": ReturnOrderView,
}
