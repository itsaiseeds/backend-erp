"""Party master-data endpoint: ``GET``/``POST`` ``/api/sales-admin/parties``.

Only an application Admin may view or create parties (``admin_required`` on
``AdminApiView``). Soft-deleted parties are never returned. A party is a lookup
row addressed by its primary key (like ``Crop``); it is never exposed as a
public id.

Every party has a ``party_type`` (``RAW_MATERIAL`` / ``OTHER_MATERIAL``):
``?type=<value>`` narrows the list to one type, and every list response carries
the full set of types as ``party_types`` (beside ``results``) for the picker.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import party_payload, party_type_options
from aggregator.models import City, Party, PartyType
from api.inward_serializers import parse_party_type
from api.paginated_views import AdminPaginatedDateRangeListView
from authentication.validators import validate_phone_number
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_str,
)


class PartyCityRefSerializer(serializers.Serializer):
    """Output shape for the ``city`` reference on a party."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class PartyPayloadSerializer(serializers.Serializer):
    """Output shape for one party row."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    city = PartyCityRefSerializer()
    party_type = serializers.ChoiceField(choices=PartyType.choices)
    contact_number = serializers.CharField(allow_null=True)


class PartyTypeOptionSerializer(serializers.Serializer):
    """Output shape for one entry of ``party_types`` (schema only)."""

    value = serializers.CharField()
    label = serializers.CharField()


class CreatePartySerializer(serializers.Serializer):
    """Request validation for creating a new ``Party``."""

    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Party name is required.",
            "required": "Party name is required.",
        },
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        error_messages={"required": "City is required."},
    )
    party_type = serializers.ChoiceField(
        choices=PartyType.choices,
        error_messages={"required": "Party type is required."},
    )
    contact_number = serializers.CharField(
        max_length=10,
        required=False,
        allow_null=True,
        allow_blank=True,
        validators=[validate_phone_number],
    )

    def validate_contact_number(self, value):
        return value or None

    def validate(self, attrs):
        name = attrs["name"].strip()
        attrs["name"] = name
        if Party.all_objects.filter(name=name, city=attrs["city"]).exists():
            raise serializers.ValidationError(
                "A party with this name already exists in this city."
            )
        return attrs


class PartyListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = PartyPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)
    party_types = PartyTypeOptionSerializer(many=True)


def _party_cities(request: Request) -> list[dict]:
    """Every distinct city at least one party is in."""
    rows = (
        Party.objects.values_list("city_id", "city__name")
        .distinct()
        .order_by("city__name")
    )
    return [{"value": city_id, "label": name} for city_id, name in rows]


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "city_id",
        label="City",
        lookup="city_id__in",
        description="City id(s) of the party's city (see options).",
        options=_party_cities,
    ),
    QuerysetFilter(
        "name",
        label="Name",
        lookup="name__icontains",
        parse=parse_str,
        multi=False,
        description="Case-insensitive substring of the party name.",
    ),
    QuerysetFilter(
        "type",
        label="Type",
        lookup="party_type__in",
        parse=parse_party_type,
        description="Party type(s): RAW_MATERIAL / OTHER_MATERIAL (see options).",
        options=party_type_options(),
    ),
)
_SORT_OPTIONS = (
    SortOption("name", label="Name", description="Party name, A->Z (default)."),
    SortOption("created_at", label="Created", description="When the party was added."),
)


class PartiesView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) parties (app admin only)."""

    serializer_class = CreatePartySerializer
    enforce_date_range_filters = False
    default_sort = ("name", "pk")
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_parties_list",
        summary="List parties (filter by city / name / type, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: PartyListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.data["party_types"] = party_type_options()
        return response

    def get_queryset(self, request: Request) -> QuerySet:
        return Party.objects.select_related("city")

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [party_payload(party) for party in page_items]

    @extend_schema(
        summary="Create a party",
        request=CreatePartySerializer,
        responses={201: PartyPayloadSerializer},
    )
    def post(self, request):
        serializer = CreatePartySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        party = Party.objects.create(
            name=data["name"],
            city=data["city"],
            party_type=data["party_type"],
            contact_number=data.get("contact_number"),
            created_by=request.user,
        )
        return Response(
            party_payload(party), status=status.HTTP_201_CREATED
        )
