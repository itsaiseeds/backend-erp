"""Serializers for the field-trip endpoints, shared by both clients.

The request serializers validate what the sales person (Android) and the sales
admin (web) send; the output serializers are schema-only -- trip and visit
payloads are built by hand in ``aggregator.FieldTripOperations`` and these
classes exist so drf-spectacular can document their shape.
"""

from __future__ import annotations

from rest_framework import serializers

from aggregator.models import City, Crop, Product
from api.order_serializers import ProductRefSerializer
from authentication.validators import validate_phone_number
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    SortCatalogueEntrySerializer,
)

# -- Requests ------------------------------------------------------------------


class FieldTripWriteSerializer(serializers.Serializer):
    """A trip's plan: where and when. Every field is required on create; an
    edit validates it with ``partial=True`` and applies only what was sent.

    That the expected end falls after the expected start is checked on the
    merged trip by ``FieldTrip.clean()``, so a partial edit sending only one
    bound is still judged against the other.
    """

    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source="city",
        help_text="A city id from utilities/cities.",
    )
    village = serializers.CharField(max_length=255)
    expected_start_at = serializers.DateTimeField()
    expected_end_at = serializers.DateTimeField()

    def validate_village(self, value: str) -> str:
        return value.strip()


class CreateFarmerVisitSerializer(serializers.Serializer):
    """A farmer met on an in-progress trip.

    ``crop_ids`` come from ``utilities/crops`` and ``product_public_ids`` from
    ``utilities/products``. An empty (or omitted) product list records that the
    farmer does not use our products.
    """

    is_lead = serializers.BooleanField(required=False, default=False)
    field_trip_public_id = serializers.CharField(max_length=20)
    farmer_name = serializers.CharField(max_length=255)
    contact_number = serializers.CharField(validators=[validate_phone_number])
    village = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        help_text="Defaults to the field trip's village.",
    )
    land_area_bigha = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=0, help_text="Land held, in bigha."
    )
    crop_ids = serializers.PrimaryKeyRelatedField(
        queryset=Crop.objects.all(),
        many=True,
        allow_empty=False,
        source="crops",
        help_text="At least one crop the farmer grows.",
    )
    product_public_ids = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="public_id",
        many=True,
        required=False,
        source="products",
        help_text="Our products the farmer uses; empty if none.",
    )

    def validate_farmer_name(self, value: str) -> str:
        return value.strip()


class CreateFarmerSerializer(serializers.Serializer):
    """A farmer a sales person records on their own, outside any field trip.

    Same fields as :class:`CreateFarmerVisitSerializer` minus the trip; with no
    trip to default from, ``village`` is required.
    """

    farmer_name = serializers.CharField(max_length=255)
    contact_number = serializers.CharField(validators=[validate_phone_number])
    village = serializers.CharField(max_length=255)
    land_area_bigha = serializers.DecimalField(
        max_digits=12, decimal_places=4, min_value=0, help_text="Land held, in bigha."
    )
    is_lead = serializers.BooleanField(required=False, default=False)
    crop_ids = serializers.PrimaryKeyRelatedField(
        queryset=Crop.objects.all(),
        many=True,
        allow_empty=False,
        source="crops",
        help_text="At least one crop the farmer grows.",
    )
    product_public_ids = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="public_id",
        many=True,
        required=False,
        source="products",
        help_text="Our products the farmer uses; empty if none.",
    )

    def validate_farmer_name(self, value: str) -> str:
        return value.strip()

    def validate_village(self, value: str) -> str:
        return value.strip()


class EditFarmerVisitSerializer(serializers.Serializer):
    """A partial correction to a recorded farmer: send only what changed.

    Every field is optional, but one that is sent may not be blank: the name,
    contact number and village must have text and ``crop_ids`` at least one
    crop. ``product_public_ids`` may be empty -- the farmer does not use our
    products. Anything else sent is ignored.
    """

    is_lead = serializers.BooleanField(required=False)
    farmer_name = serializers.CharField(max_length=255, required=False)
    contact_number = serializers.CharField(required=False, validators=[validate_phone_number])
    village = serializers.CharField(max_length=255, required=False)
    land_area_bigha = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        min_value=0,
        required=False,
        help_text="Land held, in bigha.",
    )
    crop_ids = serializers.PrimaryKeyRelatedField(
        queryset=Crop.objects.all(),
        many=True,
        allow_empty=False,
        required=False,
        source="crops",
        help_text="Replaces the farmer's crops; at least one.",
    )
    product_public_ids = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="public_id",
        many=True,
        required=False,
        source="products",
        help_text="Replaces the products the farmer uses; empty if none.",
    )

    def validate_farmer_name(self, value: str) -> str:
        return value.strip()

    def validate_village(self, value: str) -> str:
        return value.strip()

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError(
                "Send at least one of farmer_name, contact_number, village, land_area_bigha, "
                "is_lead, crop_ids, product_public_ids."
            )
        return attrs


# -- Responses (schema only) ---------------------------------------------------


class UserContactRefSerializer(serializers.Serializer):
    """A ``{id, name, phone_number}`` user reference -- the sales person or approver."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    phone_number = serializers.CharField()


class IdNameSerializer(serializers.Serializer):
    """An ``{id, name}`` reference (a city, a crop)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class FieldTripPayloadSerializer(serializers.Serializer):
    """Output shape for one trip (``FieldTripOperations.field_trip_payload``)."""

    public_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["PLANNED", "APPROVED", "IN_PROGRESS", "COMPLETED"])
    city = IdNameSerializer()
    village = serializers.CharField()
    expected_start_at = serializers.DateTimeField()
    expected_end_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
    sales_person = UserContactRefSerializer()
    approved_by = UserContactRefSerializer(
        allow_null=True, help_text="Sales admin who approved it; null until approved."
    )
    approved_at = serializers.DateTimeField(allow_null=True)
    farmer_visit_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class FieldTripPageSerializer(serializers.Serializer):
    """Output shape for a paginated page of trips."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = FieldTripPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


class FarmerVisitPayloadSerializer(serializers.Serializer):
    """Output shape for one farmer visit (``FieldTripOperations.farmer_visit_payload``)."""

    public_id = serializers.CharField()
    farmer_name = serializers.CharField()
    contact_number = serializers.CharField()
    village = serializers.CharField()
    land_area_bigha = serializers.CharField()
    is_lead = serializers.BooleanField()
    field_trip_public_id = serializers.CharField(
        allow_null=True, help_text="Null for a farmer recorded outside any trip."
    )
    crops = IdNameSerializer(many=True)
    uses_our_products = serializers.BooleanField()
    products = ProductRefSerializer(many=True)
    created_at = serializers.DateTimeField()


class FarmerVisitPageSerializer(serializers.Serializer):
    """Output shape for a paginated page of farmer visits."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = FarmerVisitPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


class FarmerPayloadSerializer(serializers.Serializer):
    """Output shape for one farmer across every trip.

    A farmer is one ``contact_number``, whatever the number of trips they were
    recorded on: ``farmer_name`` / ``village`` / ``city`` / ``land_area_bigha``
    come from their latest visit, while ``crops`` / ``products`` are merged over
    all of them and ``visits`` lists the meetings behind the row.
    ``FieldTripOperations.farmer_payload`` builds it.
    """

    contact_number = serializers.CharField(help_text="The farmer's identity across trips.")
    farmer_name = serializers.CharField(help_text="Name given at the latest visit.")
    village = serializers.CharField(help_text="Village of the latest visit.")
    city = IdNameSerializer(
        allow_null=True,
        help_text="City of the latest visit's field trip; null for a farmer recorded without a trip.",
    )
    land_area_bigha = serializers.CharField(help_text="Land held at the latest visit, in bigha.")
    is_lead = serializers.BooleanField(help_text="Lead flag of the latest record.")
    crops = IdNameSerializer(many=True, help_text="Every crop they grow, merged over visits.")
    uses_our_products = serializers.BooleanField()
    products = ProductRefSerializer(
        many=True, help_text="Every product of ours they use, merged over visits."
    )
    visit_count = serializers.IntegerField(help_text="How many visits they have in all.")
    last_visited_at = serializers.DateTimeField(help_text="When they were last recorded.")
    sales_people = UserContactRefSerializer(
        many=True, help_text="Sales people who have recorded a visit of theirs."
    )
    visits = serializers.ListField(
        child=serializers.DictField(),
        help_text="Their visits, newest first: public_id, field_trip_public_id, created_at.",
    )


class FarmerPageSerializer(serializers.Serializer):
    """Output shape for a paginated page of farmers (all trips)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = FarmerPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)
