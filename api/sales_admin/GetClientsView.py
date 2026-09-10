"""Client list endpoint: ``GET /api/sales-admin/get-clients/``.

The sales-admin counterpart of ``GET /android/api/v1/get-clients``. Same compact
card per client (company details plus the primary address and primary contact),
same pagination / filter / sort contract -- but scoped to *every* client rather
than the caller's own, and with one extra filter: ``created_by``, the id of the
sales person who onboarded the client.

Paginated, filterable and sortable through ``AndroidPaginatedDateRangeListView``
(shared mixin):

* ``?created_by=<id1,id2,...>`` -- clients a given sales person created. The
  ``available_filters`` entry lists the eligible ``{value, label}`` sales people
  (exactly the ones who have clients), so the picker needs no second call.
* ``?city_id=<id1,id2,...>`` -- clients whose *primary* address is in one of
  those cities; the entry lists every city some client's primary address sits
  in.
* ``?status=<code,...>`` -- ``VERIFICATION_PENDING`` / ``VERIFIED``.
* ``?company_name=<term>`` -- case-insensitive substring of the company name.
* ``?address=<term>`` -- case-insensitive substring of the *primary* address
  (line 1/2, pincode or city name).
* ``?created_gte=`` / ``?created_lte=`` -- ISO 8601 datetime bounds on when the
  client was added (inclusive; send either or both).
* ``?sort=<-?name,...>`` over ``created_at`` / ``company_name``; default newest
  first.

A bare request returns the first page of every client.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.ClientOperations import client_list_payload
from aggregator.models import Client, ClientAddress, ClientContact
from aggregator.models.Status import StatusIds
from api.client_serializers import (
    ClientAddressPayloadSerializer,
    ClientContactPayloadSerializer,
)
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    RangeFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_datetime,
    parse_str,
)

_CLIENT_STATUS_CODES = [status.name for status in StatusIds.client_statuses()]


class ClientListItemSerializer(serializers.Serializer):
    """Output shape for one client card (schema only)."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()
    company_phone = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    created_by = serializers.CharField(allow_null=True)
    primary_contact = ClientContactPayloadSerializer(allow_null=True)
    primary_address = ClientAddressPayloadSerializer(allow_null=True)


class ClientListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = ClientListItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _by_primary_address_city(queryset: QuerySet, city_ids: list[int]) -> QuerySet:
    """Keep clients whose *primary* address sits in one of ``city_ids``.

    The join is spelled out (rather than reusing ``Client.primary_address``) so
    it stays a single query; ``is_deleted=False`` is explicit because a lookup
    that spans the relation does not pick up ``ClientAddress``'s default
    soft-delete manager.
    """
    return queryset.filter(
        client_addresses__is_primary=True,
        client_addresses__is_deleted=False,
        client_addresses__address__city_id__in=city_ids,
    ).distinct()


def _salespeople_with_clients(request: Request) -> list[dict]:
    """The distinct sales people who have created a client.

    The eligible value set for the ``created_by`` filter: the picker only ever
    needs to show a sales person who actually owns at least one client.
    """
    rows = (
        Client.objects.values_list("created_by_id", "created_by__name")
        .distinct()
        .order_by("created_by__name")
    )
    return [{"value": user_id, "label": name} for user_id, name in rows]


def _primary_address_cities(request: Request) -> list[dict]:
    """Every distinct primary-address city across all clients."""
    rows = (
        ClientAddress.objects.filter(is_primary=True)
        .values_list("address__city_id", "address__city__name")
        .distinct()
        .order_by("address__city__name")
    )
    return [{"value": city_id, "label": name} for city_id, name in rows]


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in _CLIENT_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(_CLIENT_STATUS_CODES)}."
        )
    return code


def _by_primary_address_text(queryset: QuerySet, terms: list[str]) -> QuerySet:
    """Substring match against the client's *primary* address.

    Matches line 1 / line 2 / pincode / city name of the one primary address
    (all conditions on a single join, so a non-primary address never satisfies
    it). ``terms`` always has one entry -- the filter is ``multi=False``.
    """
    term = terms[0]
    primary = Q(client_addresses__is_primary=True, client_addresses__is_deleted=False)
    text = (
        Q(client_addresses__address__address_line_1__icontains=term)
        | Q(client_addresses__address__address_line_2__icontains=term)
        | Q(client_addresses__address__pincode__code__icontains=term)
        | Q(client_addresses__address__city__name__icontains=term)
    )
    return queryset.filter(primary & text).distinct()


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "created_by",
        lookup="created_by_id__in",
        description="User id(s) of the sales person who created the client (see options).",
        options=_salespeople_with_clients,
    ),
    QuerysetFilter(
        "city_id",
        apply=_by_primary_address_city,
        description="City id(s) of the client's primary address (see options).",
        options=_primary_address_cities,
    ),
    QuerysetFilter(
        "status",
        parse=_parse_status,
        apply=lambda queryset, codes: queryset.filter(status__code__in=codes),
        description="Client verification status.",
        options=[
            {"value": code, "label": code.replace("_", " ").title()}
            for code in _CLIENT_STATUS_CODES
        ],
    ),
    QuerysetFilter(
        "company_name",
        lookup="company_name__icontains",
        parse=parse_str,
        multi=False,
        description="Case-insensitive substring of the company name.",
    ),
    QuerysetFilter(
        "address",
        parse=parse_str,
        multi=False,
        apply=_by_primary_address_text,
        description="Case-insensitive substring of the primary address "
        "(line 1/2, pincode or city).",
    ),
    RangeFilter(
        "created",
        field="created_at",
        parse=parse_datetime,
        suffixes=("gte", "lte"),
        description="When the client was added (ISO 8601).",
    ),
)
_SORT_OPTIONS = (
    SortOption("created_at", description="When the client was added (default: newest first)."),
    SortOption("company_name", description="Company name, A->Z."),
)


class GetClientsView(AdminPaginatedDateRangeListView):
    """List every client: filter by sales person / city / status / created window, sort."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_get_clients_list",
        summary=(
            "List clients (filter by sales person / city / status / name / "
            "address / created, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: ClientListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        primary_addresses = ClientAddress.objects.filter(is_primary=True).select_related(
            "address",
            "address__pincode",
            "address__city",
            "address__state",
            "address__country",
        )
        return (
            Client.objects.select_related("status", "created_by")
            .prefetch_related(
                Prefetch("client_addresses", queryset=primary_addresses),
                Prefetch(
                    "client_contacts",
                    queryset=ClientContact.objects.filter(
                        is_primary=True
                    ).select_related("contact"),
                ),
            )
        )

    def serialize_page(self, page_items: list[Client], request: Request) -> list[dict]:
        return [
            {
                **client_list_payload(client),
                "created_by": client.created_by.name if client.created_by else None,
            }
            for client in page_items
        ]
