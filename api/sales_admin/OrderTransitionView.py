"""Shared base for the order lifecycle endpoints.

Six sales-admin endpoints move one order from one status to another --
``verify-order`` / ``unverify-order``, ``dispatch-order`` / ``revert-dispatch``,
``hold-order`` and ``reject-order``. They differ only in which operations
function they call; loading the order, returning the full detail payload and
documenting the path parameter are identical in all six, so they live here.

Which statuses a verb may be applied from is **not** decided here: those guards
live beside the transitions themselves in ``aggregator.OrderOperations``, so the
rule holds however the function is reached. This base is only the HTTP shape.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import order_detail_payload
from api.admin import AdminApiView

from .GetOrderView import order_detail_queryset


class OrderTransitionView(AdminApiView):
    """One order lifecycle verb: load, apply the transition, return the order.

    A subclass implements :meth:`apply_transition` and declares its own
    ``@extend_schema`` on a ``post`` that simply defers to
    :meth:`transition`. No subclass catches anything: a guard that refuses the
    transition raises ``ValidationError`` from the operations layer, which the
    project's exception handler renders as a 400.
    """

    admin_required = True

    def apply_transition(self, order: Order, request: Request) -> None:
        """Move ``order`` to its new status. Implemented by each subclass."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement apply_transition(self, order, request)."
        )

    def transition(self, request: Request, public_id: str) -> Response:
        order = get_object_or_404(order_detail_queryset(), public_id=public_id)
        self.apply_transition(order, request)
        order.refresh_from_db()
        return Response(order_detail_payload(order))
