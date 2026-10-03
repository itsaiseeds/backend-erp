"""Accept endpoint: ``POST /api/sales-admin/accept-return-order/<public_id>``.

Accepts a PENDING return. Its goods become **inward stock**: for every line the
raw kilograms (packets x packet weight) are booked as an In Use raw-material lot,
dated today, with no party and the return's public id as its lot number.

``include_in_other_raw_materials`` is required and is the admin's choice whether
the packing materials come back too. When true, ``recipe_public_ids`` names the
recipes to book them against -- live or soft-deleted ones, the latter because
stock booked against a since-replaced recipe still counts -- and each recipe books
``recipe.quantity x packets`` of its material. The recipes must satisfy:

* each matches a line of the return by ``(product, packet_weight)``;
* each line has at most one recipe per material type;
* every line has at least one recipe.

When the flag is false, ``recipe_public_ids`` must be empty or omitted. A breach
is a 400 and nothing is written; ``GET return-order-recipes/<public_id>`` lists
the candidates per line.

The order's returnable limit is re-checked, and the stock ledger records one
``RETURN_OPERATIONS`` / ``RETURN_ACCEPTED`` event per product.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ReturnOrder
from aggregator.ReturnOrderOperations import accept_return_order
from api.return_order_serializers import (
    AcceptReturnOrderSerializer,
    ReturnOrderPayloadSerializer,
)

from .ReturnOrderTransitionView import RETURN_PUBLIC_ID_PARAMETER, ReturnOrderTransitionView


class AcceptReturnOrderView(ReturnOrderTransitionView):
    """Accept a return, booking its raw (and optionally packing) material back in."""

    serializer_class = AcceptReturnOrderSerializer

    @extend_schema(
        summary="Accept a return (PENDING -> ACCEPTED), booking inward stock",
        request=AcceptReturnOrderSerializer,
        parameters=[RETURN_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        # Validated before the row is locked: a malformed body costs nothing.
        serializer = AcceptReturnOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.accept = serializer.validated_data
        return self.transition(request, public_id)

    def apply_transition(self, ret: ReturnOrder, request: Request) -> None:
        accept_return_order(
            ret,
            include_other=self.accept["include_in_other_raw_materials"],
            recipe_public_ids=self.accept.get("recipe_public_ids"),
            admin=request.user,
        )
