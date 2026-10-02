"""Sales-person analytics: ``GET /android/api/v1/analytics``.

Counts of the caller's own business inside a window, for the app's dashboard:

* ``orders`` -- orders booked in the window, by order status.
* ``clients`` -- clients created in the window, by verification status.
* ``client_orders`` -- per client, the orders booked in the window by status
  (clients with no orders in the window are omitted), busiest first.

Both ``start_date_time`` and ``end_date_time`` are required (ISO 8601,
inclusive) and are matched against each row's ``created_at``; a missing or
inverted pair is a ``400``. Every status bucket is always present, zero-filled.
Scoped to the caller -- one sales person never sees another's numbers.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.AnalyticsOperations import (
    CLIENT_STATUS_CODES,
    ORDER_STATUS_CODES,
    sales_person_analytics,
)
from android.api.base import AndroidBaseView
from common.views.paginated_date_range import DateRangeQuerySerializer

OrderStatusCountsSerializer = type(
    "OrderStatusCountsSerializer",
    (serializers.Serializer,),
    {code: serializers.IntegerField() for code in ORDER_STATUS_CODES},
)
ClientStatusCountsSerializer = type(
    "ClientStatusCountsSerializer",
    (serializers.Serializer,),
    {code: serializers.IntegerField() for code in CLIENT_STATUS_CODES},
)


class OrderCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = OrderStatusCountsSerializer()


class ClientCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = ClientStatusCountsSerializer()


class AnalyticsClientRefSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    company_name = serializers.CharField()


class ClientOrderCountsSerializer(serializers.Serializer):
    client = AnalyticsClientRefSerializer()
    total = serializers.IntegerField()
    by_status = OrderStatusCountsSerializer()


class AnalyticsResponseSerializer(serializers.Serializer):
    start_date_time = serializers.DateTimeField()
    end_date_time = serializers.DateTimeField()
    orders = OrderCountsSerializer()
    clients = ClientCountsSerializer()
    client_orders = ClientOrderCountsSerializer(many=True)


class AnalyticsView(AndroidBaseView):
    """Order, client and per-client order counts for the caller in a window."""

    @extend_schema(
        summary="Order / client counts by status within a date window",
        parameters=[
            OpenApiParameter("start_date_time", str, required=True, description="ISO 8601."),
            OpenApiParameter("end_date_time", str, required=True, description="ISO 8601."),
        ],
        responses={200: AnalyticsResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        params = DateRangeQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        return Response(
            sales_person_analytics(request.user, data["start_date_time"], data["end_date_time"])
        )
