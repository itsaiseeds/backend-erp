"""Reusable pieces for a paginated ``GET`` list view filtered by a required
``start_date_time``..``end_date_time`` window.

Two concrete client bases wrap the mixin defined here:
``api.paginated_views.AdminPaginatedDateRangeListView`` (sales-admin website)
and ``android.api.paginated_views.AndroidPaginatedDateRangeListView`` (android
app). Subclass one of those -- not the mixin -- in a real view.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response


class StandardPageNumberPagination(PageNumberPagination):
    """Project default page number pagination.

    Uses ``?page=`` and ``?page_size=`` (capped at ``max_page_size``) and
    returns DRF's standard ``{count, next, previous, results}`` envelope.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DateRangeQuerySerializer(serializers.Serializer):
    """Validates the required ``start_date_time`` / ``end_date_time`` pair
    that every paginated date-range list view accepts as query params."""

    start_date_time = serializers.DateTimeField()
    end_date_time = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["start_date_time"] > attrs["end_date_time"]:
            raise serializers.ValidationError(
                "start_date_time must be less than or equal to end_date_time."
            )
        return attrs


class _PaginatedDateRangeListMixin:
    """Provides ``GET`` for a paginated date-range list view.

    A subclass must implement :meth:`get_queryset` and :meth:`serialize_page`,
    and may set :attr:`date_field` to filter by a related object's timestamp
    (e.g. ``"order__created_at"``).

    Not for direct use -- compose it through one of the concrete client bases.
    """

    date_field: str = "created_at"
    pagination_class = StandardPageNumberPagination

    def get_queryset(self, request: Request):
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_queryset(self, request)."
        )

    def serialize_page(self, page_items: list[Any], request: Request):
        raise NotImplementedError(
            f"{type(self).__name__} must implement "
            "serialize_page(self, page_items, request)."
        )

    def get(self, request: Request, *args, **kwargs) -> Response:
        params = DateRangeQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        queryset = self.get_queryset(request).filter(
            **{
                f"{self.date_field}__gte": params.validated_data["start_date_time"],
                f"{self.date_field}__lte": params.validated_data["end_date_time"],
            }
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(self.serialize_page(page, request))
