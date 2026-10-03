"""Shared base for the return-order lifecycle endpoints.

Four sales-admin endpoints move one return from one status to another --
``accept-return-order``, ``reject-return-order``, ``unreject-return-order`` and
``revert-accept-return-order``. They differ only in which operations function
they call, so loading the return, returning its payload and documenting the path
parameter live here, mirroring ``OrderTransitionView``.

Which statuses a verb may be applied from is **not** decided here: those guards
live in ``aggregator.ReturnOrderOperations``, so the rule holds however the
function is reached. This base is only the HTTP shape.

**The return row is locked for the whole transition**, so two concurrent calls
(a double accept, an accept racing a reject) cannot both pass the guard: the
second waits, re-reads the status the first one left, and is refused with an
ordinary 400. The operations then lock the order row, so the lock order is
always return, then order -- the order verbs and a return's creation take the
order row alone.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch, QuerySet
from django.http import Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ReturnOrder, ReturnOrderItem
from aggregator.ReturnOrderOperations import return_order_payload
from api.admin import AdminApiView

RETURN_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The return's public id, e.g. RET-E79QA0E2OIHF.",
)


def return_order_queryset() -> QuerySet:
    """The fully joined single-return queryset behind every return payload."""
    return ReturnOrder.objects.select_related(
        "status",
        "order__status",
        "order__client",
        "created_by",
        "verified_by",
        "rejected_by",
    ).prefetch_related(
        Prefetch("items", queryset=ReturnOrderItem.objects.select_related("product"))
    )


def get_locked_return_order(public_id: str) -> ReturnOrder:
    """Lock the return row ``FOR UPDATE``, then load it through :func:`return_order_queryset`.

    Two queries on purpose, for the reason ``get_locked_order`` gives: the lock
    is taken on the bare row so a caller that waited does not lose it to a join
    re-check against the changed row (a 404 instead of the guard's 400).

    Must be called inside ``transaction.atomic``.
    """
    pk = (
        ReturnOrder.objects.select_for_update()
        .filter(public_id=public_id)
        .values_list("pk", flat=True)
        .first()
    )
    if pk is None:
        raise Http404("No ReturnOrder matches the given query.")
    return return_order_queryset().get(pk=pk)


class ReturnOrderTransitionView(AdminApiView):
    """One return lifecycle verb: load, apply the transition, return the return.

    A subclass implements :meth:`apply_transition` and declares its own
    ``@extend_schema`` on a ``post`` that simply defers to :meth:`transition`.
    No subclass catches anything: a guard that refuses the transition raises
    ``ValidationError`` from the operations layer, which the project's exception
    handler renders as a 400.
    """

    admin_required = True

    def apply_transition(self, ret: ReturnOrder, request: Request) -> None:
        """Move ``ret`` to its new status. Implemented by each subclass."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement apply_transition(self, ret, request)."
        )

    def transition(self, request: Request, public_id: str) -> Response:
        with transaction.atomic():
            ret = get_locked_return_order(public_id)
            self.apply_transition(ret, request)
        return Response(return_order_payload(return_order_queryset().get(pk=ret.pk)))
