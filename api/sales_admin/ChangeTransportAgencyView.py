"""Change-agency endpoint: ``PATCH /api/sales-admin/change-transport-agency/<public_id>``.

A sales admin moves a dispatched order to a different one of its client's
transport agencies, for when the goods ended up with another transporter than the
one chosen at booking.

**Only a DISPATCHED order, and only an agency dispatch.** DISPATCHED is the one
status where the goods are on the road but no LR number exists yet (recording the
LR delivers the order), so nothing issued by the old agency is left behind. An
order that went on our own vehicle has no transporter to replace and is refused
with a 400; its dispatch mode is not changed here.

``transport_agency_id`` is the ``TransportAgency`` id -- the ``transport_agency.id``
every order payload already carries -- and must be one of the order's client's
agencies. The order's ``transport_agency`` is the only place the agency is stored;
the order detail, list, export and the challan all read it live, so changing it
there changes it everywhere.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.DispatchOperations import change_transport_agency
from aggregator.models import Order
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class ChangeTransportAgencySerializer(serializers.Serializer):
    """Request validation for changing a dispatched order's transport agency."""

    transport_agency_id = serializers.IntegerField(
        error_messages={
            "required": "transport_agency_id is required.",
            "null": "transport_agency_id is required.",
            "invalid": "transport_agency_id must be an integer.",
        },
        help_text="The id of one of the order's client's transport agencies.",
    )


class ChangeTransportAgencyView(OrderTransitionView):
    """Swap the transport agency of a dispatched order (app admin only)."""

    serializer_class = ChangeTransportAgencySerializer

    @extend_schema(
        summary="Change the transport agency of a dispatched order",
        request=ChangeTransportAgencySerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        serializer = ChangeTransportAgencySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        change_transport_agency(
            order, transport_agency_id=serializer.validated_data["transport_agency_id"]
        )
