"""Shared base for the custom-order lifecycle endpoints.

``dispatch-custom-order`` and ``revert-custom-order-dispatch`` differ only in
which operations function they call; loading the custom order under a row lock
and returning the full detail payload are shared here -- the custom-order
counterpart of ``OrderTransitionView``, for the same reason: without the lock
two concurrent dispatches would both pass the status guard and both write.
"""

from __future__ import annotations

from django.db import transaction
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import custom_order_detail_payload
from aggregator.models import CustomOrder
from api.admin import AdminApiView

from .CustomOrderView import custom_order_detail_queryset, get_locked_custom_order


class CustomOrderTransitionView(AdminApiView):
    """One custom-order lifecycle verb: load, apply the transition, return the order."""

    admin_required = True

    def apply_transition(self, order: CustomOrder, request: Request) -> None:
        """Move ``order`` to its new status. Implemented by each subclass."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement apply_transition(self, order, request)."
        )

    def transition(self, request: Request, public_id: str) -> Response:
        with transaction.atomic():
            order = get_locked_custom_order(public_id)
            self.apply_transition(order, request)
        order = custom_order_detail_queryset().get(pk=order.pk)
        return Response(custom_order_detail_payload(order))
