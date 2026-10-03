"""Notification inbox endpoint: ``GET /android/api/v1/notifications``.

Lists the calling sales person's notifications, newest first -- the in-app copy
of every push, so one that was missed (phone off, permission denied) is still
here. Scoped to the caller. Paginated through ``AndroidPaginatedDateRangeListView``:

* ``?is_read=<true|false>`` -- only read, or only unread (``false`` plus
  ``total_count`` is the badge number).

A bare request returns the first page of everything.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.models import Notification
from aggregator.NotificationOperations import notification_payload
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    list_query_parameters,
    parse_str,
)

_BOOLEANS = {"true": True, "false": False}


def _parse_is_read(raw: str) -> str:
    value = parse_str(raw).lower()
    if value not in _BOOLEANS:
        raise serializers.ValidationError(f"Unknown is_read '{raw}'. Allowed: true, false.")
    return value


def _apply_is_read(queryset: QuerySet, values: list[str]) -> QuerySet:
    wanted = {_BOOLEANS[value] for value in values}
    if wanted == {True, False}:
        return queryset
    return queryset.filter(read_at__isnull=not wanted.pop())


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "is_read",
        label="Read",
        parse=_parse_is_read,
        apply=_apply_is_read,
        description="Whether the notification has been marked read.",
        options=[{"value": "true", "label": "Read"}, {"value": "false", "label": "Unread"}],
    ),
)


class NotificationItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    screen = serializers.CharField(help_text="App screen to open on tap, e.g. order_detail.")
    data = serializers.DictField(help_text="What the screen needs, e.g. {order_public_id}.")
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class NotificationListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = NotificationItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


class GetNotificationsView(AndroidPaginatedDateRangeListView):
    """List the caller's own notifications, newest first."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS

    @extend_schema(
        operation_id="android_api_v1_get_notifications_list",
        summary="List my notifications (filter by read state)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=(),
            date_window="none",
        ),
        responses={200: NotificationListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return Notification.objects.filter(recipient=request.user).select_related("order")

    def serialize_page(self, page_items: list[Notification], request: Request) -> list[dict]:
        return [notification_payload(item) for item in page_items]
