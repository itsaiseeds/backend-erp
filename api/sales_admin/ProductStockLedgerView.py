"""Product stock ledger: ``GET`` ``/api/sales-admin/product-stock-ledger/<public_id>``.

Over a date range, what happened to one product's stock, and what the figures
were after each step. Every row lists the full state of the product's pools --
sealed bags per packaging, loose packets per packet weight, raw material, and
packing (other) materials -- plus the ``change`` that event made. The first row
of page 1 is a synthetic ``OPENING_BALANCE`` and the last row of the last page a
synthetic ``CLOSING_BALANCE``; running totals cover the whole range and are then
sliced into pages.

The ledger starts when ``seed_stock_ledger`` ran: a ``start_date`` before that
is a 400. See ``docs/prd/product-stock-ledger.md``.

**Caching and rate limit** (to save database and server egress):

* The whole range's rows are cached per ``(product, start_date, end_date)`` --
  not per page -- so paging through a range, and every other admin asking for the
  same window, costs no database reads. A window that ended before today cannot
  change (events are only ever appended at "now"), so it is cached for a day; a
  window that includes today is cached for five minutes. Both are overridable
  with ``STOCK_LEDGER_CACHE_SECONDS_CLOSED`` / ``..._OPEN`` in settings.
* The response carries ``Cache-Control: private, max-age=<remaining cache time>``,
  so the browser does not call again for the same URL while the entry is fresh.
* A request that has to **build** the rows (a cache miss) uses one unit of a
  per-user, per-product allowance of :data:`DAILY_BUILDS_PER_PRODUCT` a day
  (``429`` with ``Retry-After`` beyond it). Cache hits are free, so a window
  already built by anyone is never refused. The day is the IST calendar day.

The cache is Django's default cache. With ``LocMemCache`` (the project default)
it is per worker process, so each gunicorn worker keeps its own copy and its own
allowance counter; point ``CACHES`` at a shared backend (Redis, database cache)
for a single global one.
"""

from __future__ import annotations

import datetime

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, serializers
from rest_framework.response import Response

from aggregator.models import Product
from aggregator.StockLedgerReport import (
    LedgerNotStarted,
    LedgerRangeError,
    product_ledger_rows,
)
from api.admin import AdminApiView
from api.export_views import EXPORT_QUERY_PARAMETERS, ExportDateRangeQuerySerializer

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
DAILY_BUILDS_PER_PRODUCT = 2
CACHE_VERSION = 3  # bump to drop every cached window after a change to the row shape


def _cache_seconds(end_date: datetime.date) -> int:
    """How long a window is cached: a day once it is closed, minutes while it is open."""
    if end_date < timezone.localdate():
        return getattr(settings, "STOCK_LEDGER_CACHE_SECONDS_CLOSED", 24 * 3600)
    return getattr(settings, "STOCK_LEDGER_CACHE_SECONDS_OPEN", 300)


def _seconds_until_midnight() -> int:
    now = timezone.localtime()
    midnight = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(int((midnight - now).total_seconds()), 1)


def _quota_key(user_id: int, product_id: int) -> str:
    return f"stock-ledger-builds:{user_id}:{product_id}:{timezone.localdate().isoformat()}"


def _assert_build_allowed(user_id: int, product_id: int) -> None:
    if cache.get(_quota_key(user_id, product_id), 0) >= DAILY_BUILDS_PER_PRODUCT:
        raise exceptions.Throttled(
            wait=_seconds_until_midnight(),
            detail=(
                f"Stock ledger limit reached: {DAILY_BUILDS_PER_PRODUCT} new ledger "
                "builds per product per day. Windows already built are still served."
            ),
        )


def _record_build(user_id: int, product_id: int) -> None:
    key = _quota_key(user_id, product_id)
    cache.add(key, 0, timeout=_seconds_until_midnight())
    try:
        cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, timeout=_seconds_until_midnight())


class LedgerQuerySerializer(ExportDateRangeQuerySerializer):
    """``start_date`` / ``end_date`` (max 31 days) plus ``page`` / ``page_size``."""

    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.IntegerField(
        min_value=1, max_value=MAX_PAGE_SIZE, required=False, default=DEFAULT_PAGE_SIZE
    )


class LedgerProductSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    name = serializers.CharField()


class LedgerSourceSerializer(serializers.Serializer):
    kind = serializers.CharField()
    public_id = serializers.CharField()
    label = serializers.CharField(allow_blank=True)


class LedgerActorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class LedgerCountChangeSerializer(serializers.Serializer):
    on_hand = serializers.IntegerField()
    reserved = serializers.IntegerField()
    consumed = serializers.IntegerField()
    available = serializers.IntegerField()


class LedgerPackagingSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    packet_weight = serializers.CharField()
    packets = serializers.IntegerField()


class LedgerBagPoolSerializer(LedgerCountChangeSerializer):
    packaging = LedgerPackagingSerializer()
    change = LedgerCountChangeSerializer()


class LedgerPacketPoolSerializer(LedgerCountChangeSerializer):
    packet_weight = serializers.CharField()
    change = LedgerCountChangeSerializer()


class LedgerRawChangeSerializer(serializers.Serializer):
    incoming = serializers.CharField()
    packed = serializers.CharField()
    rejected = serializers.CharField()
    wasted = serializers.CharField()
    available = serializers.CharField()


class LedgerRawMaterialSerializer(LedgerRawChangeSerializer):
    change = LedgerRawChangeSerializer()


class LedgerMaterialTypeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField()


class LedgerOtherChangeSerializer(serializers.Serializer):
    incoming = serializers.CharField()
    packed = serializers.CharField()
    available = serializers.CharField()


class LedgerOtherMaterialSerializer(LedgerOtherChangeSerializer):
    packet_weight = serializers.CharField()
    material_type = LedgerMaterialTypeSerializer()
    change = LedgerOtherChangeSerializer()


class LedgerRowSerializer(serializers.Serializer):
    event = serializers.CharField()
    detail = serializers.CharField(allow_null=True)
    occurred_at = serializers.CharField()
    source = LedgerSourceSerializer(allow_null=True)
    actor = LedgerActorSerializer(allow_null=True)
    bag_pools = LedgerBagPoolSerializer(many=True)
    packet_pools = LedgerPacketPoolSerializer(many=True)
    raw_material = LedgerRawMaterialSerializer()
    other_materials = LedgerOtherMaterialSerializer(many=True)


class ProductStockLedgerSerializer(serializers.Serializer):
    product = LedgerProductSerializer()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = LedgerRowSerializer(many=True)


# Gzip is applied to this endpoint alone: every row repeats every pool, so the
# JSON compresses roughly 20-25x and a page is the largest response the API sends.
# ``gzip_page`` only compresses when the client sends ``Accept-Encoding: gzip``.
@method_decorator(gzip_page, name="dispatch")
class ProductStockLedgerView(AdminApiView):
    """One product's stock ledger over a date range (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Product stock ledger over a date range",
        parameters=[
            *EXPORT_QUERY_PARAMETERS,
            OpenApiParameter("page", int, required=False, description="Page number."),
            OpenApiParameter(
                "page_size",
                int,
                required=False,
                description=f"Rows per page (default {DEFAULT_PAGE_SIZE}, max {MAX_PAGE_SIZE}).",
            ),
        ],
        responses={200: ProductStockLedgerSerializer},
    )
    def get(self, request, public_id: str):
        product = get_object_or_404(Product.objects.all(), public_id=public_id)
        query = LedgerQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        cache_key = (
            f"stock-ledger:v{CACHE_VERSION}:{product.pk}:"
            f"{params['start_date'].isoformat()}:{params['end_date'].isoformat()}"
        )
        cached = cache.get(cache_key)
        if cached is not None:
            rows, expires_at = cached
        else:
            _assert_build_allowed(request.user.pk, product.pk)
            rows = expires_at = None
        try:
            if rows is None:
                rows = product_ledger_rows(product, params["start_date"], params["end_date"])
                ttl = _cache_seconds(params["end_date"])
                expires_at = timezone.now().timestamp() + ttl
                cache.set(cache_key, (rows, expires_at), timeout=ttl)
                _record_build(request.user.pk, product.pk)
        except LedgerNotStarted:
            raise serializers.ValidationError(
                {"start_date": "The stock ledger has not started yet."}
            ) from None
        except LedgerRangeError as exc:
            raise serializers.ValidationError({"start_date": str(exc)}) from None

        page, page_size = params["page"], params["page_size"]
        offset = (page - 1) * page_size
        response = Response(
            {
                "product": {"public_id": product.public_id, "name": product.name},
                "start_date": params["start_date"].isoformat(),
                "end_date": params["end_date"].isoformat(),
                "count": len(rows),
                "page": page,
                "page_size": page_size,
                "results": rows[offset : offset + page_size],
            }
        )
        remaining = max(int(expires_at - timezone.now().timestamp()), 0)
        response["Cache-Control"] = f"private, max-age={remaining}"
        return response
