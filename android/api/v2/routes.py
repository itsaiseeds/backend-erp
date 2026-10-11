"""Routes introduced or changed at Android API v2.

Everything not listed here is inherited from v1 (see ``android.api.routing``).
"""

from __future__ import annotations

from .GodownOtherMaterialStockView import GodownOtherMaterialStockView
from .ReturnOrderView import ReturnOrderView

ROUTES = {
    "godown/other-material-stock": GodownOtherMaterialStockView,
    "return-order/<order_public_id>": ReturnOrderView,
}
