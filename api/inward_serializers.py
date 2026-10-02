"""Serializers and filter/sort declarations for the inward domain, shared by the
sales-admin web views and the godown-manager Android views.

The business rules live in ``aggregator.InwardOperations``; this module holds the
request/response shapes and the list filter/sort catalogues so both clients
declare them exactly once (the same split as ``api.client_serializers``).
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.request import Request

from aggregator.InwardOperations import (
    DATED_RAW_STATUSES,
    assert_raw_lot_removable,
    assert_raw_status_transition,
    raw_status_of,
    status_row_for,
    today,
)
from aggregator.models import (
    InwardOtherMaterial,
    InwardRawMaterial,
    InwardRawMaterialStatus,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    Product,
    RawMaterialWaste,
)
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    RangeFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    parse_date,
    parse_str,
    public_id_filter,
)


class InwardRawMaterialProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference on a lot."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class InwardRawMaterialPartyRefSerializer(serializers.Serializer):
    """Output shape for the ``party`` reference on a lot."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class InwardCreatedByRefSerializer(serializers.Serializer):
    """Output shape for the ``created_by`` reference on a lot."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class InwardRawMaterialPayloadSerializer(serializers.Serializer):
    """Output shape for one raw-material lot."""

    public_id = serializers.CharField()
    product = InwardRawMaterialProductRefSerializer()
    party = InwardRawMaterialPartyRefSerializer()
    lot_no = serializers.CharField(help_text="The supplier's own batch number.")
    quantity_kg = serializers.CharField(help_text="Kilograms received.")
    status = serializers.CharField()
    lab_sampling_date = serializers.DateField(allow_null=True)
    effective_date = serializers.DateField(allow_null=True)
    created_by = InwardCreatedByRefSerializer(allow_null=True, help_text="Who booked the lot.")


class CreateInwardRawMaterialSerializer(serializers.Serializer):
    """Request validation for booking a new raw-material lot.

    ``status`` is not accepted: every lot starts ``Lab Testing`` and is moved to
    ``In Use`` or ``Rejected`` later with ``PATCH``. ``effective_date`` is
    stamped (today) at that flip and is deliberately absent here.
    ``lab_sampling_date`` may be given explicitly; left out, it defaults to
    today -- a lot never starts with no sampling date, since it arrives for
    lab testing the day it's booked. ``lot_no`` -- the supplier's own batch
    number on the consignment -- is required.
    """

    product = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Product.objects.all(),
        error_messages={"required": "Product is required."},
    )
    party = serializers.PrimaryKeyRelatedField(
        queryset=Party.objects.all(),
        error_messages={"required": "Party is required."},
    )
    lot_no = serializers.CharField(
        max_length=64,
        error_messages={"required": "Lot number is required.", "blank": "Lot number is required."},
        help_text="The supplier's own batch number for this consignment.",
    )
    quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity in kg is required."},
        help_text="Kilograms received from the party.",
    )
    lab_sampling_date = serializers.DateField(required=False, allow_null=True)


class InwardRawMaterialListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = InwardRawMaterialPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _products_with_raw_material_lots(request: Request) -> list[dict]:
    """Every distinct product that has an inward raw-material lot.

    The eligible value set for the ``product`` filter: the picker only ever
    needs to offer a product that actually has a lot behind it.
    """
    rows = (
        InwardRawMaterial.objects.values_list("product__public_id", "product__name")
        .distinct()
        .order_by("product__name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


RAW_LOT_QUERYSET_FILTERS = (
    public_id_filter("IR-"),
    QuerysetFilter(
        "product",
        label="Product",
        lookup="product__public_id__in",
        parse=parse_str,
        description="Product public id(s) (see options).",
        options=_products_with_raw_material_lots,
    ),
    QuerysetFilter(
        "party",
        label="Party",
        lookup="party_id__in",
        description="Party id(s).",
    ),
    QuerysetFilter(
        "status",
        label="Status",
        lookup="status__name",
        parse=parse_str,
        description="Lot status (Lab Testing / In Use / Rejected).",
        options=[
            {"value": s.value, "label": s.label}
            for s in InwardRawMaterialStatus
        ],
    ),
    RangeFilter(
        "effective_date",
        label="Effective Date",
        parse=parse_date,
        suffixes=("gte", "lte"),
        description=(
            "Day the lot started counting toward stock (YYYY-MM-DD, inclusive). "
            "Lots without an effective date are excluded."
        ),
    ),
)
RAW_LOT_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the lot was booked (default: newest first).",
    ),
    SortOption(
        "product",
        label="Product",
        fields=("product__name",),
        description="Product name, A->Z.",
    ),
    SortOption(
        "effective_date",
        label="Effective Date",
        fields=("effective_date",),
        description="Soonest effective date first (undated lots last).",
    ),
)


class RawMaterialWastePayloadSerializer(serializers.Serializer):
    """Output shape for one raw-material waste row."""

    public_id = serializers.CharField()
    product = InwardRawMaterialProductRefSerializer()
    quantity_kg = serializers.CharField(help_text="Kilograms wasted.")
    reason = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField(help_text="When the waste was recorded.")
    created_by = InwardCreatedByRefSerializer(allow_null=True)


class CreateRawMaterialWasteSerializer(serializers.Serializer):
    """Request validation for recording raw-material waste.

    There is no date field: waste is a standing deduction from the product's
    unpacked raw pool from the moment it is recorded.
    """

    product = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Product.objects.all(),
        error_messages={"required": "Product is required."},
    )
    quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity in kg is required."},
        help_text="Kilograms of raw material wasted.",
    )
    reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        if attrs["quantity_kg"] <= 0:
            raise serializers.ValidationError(
                {"quantity_kg": "Quantity must be greater than zero."}
            )
        return attrs


class RawMaterialWasteListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = RawMaterialWastePayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _products_with_waste(request: Request) -> list[dict]:
    """Every distinct product that has a waste row (the ``product`` filter's options)."""
    rows = (
        RawMaterialWaste.objects.values_list("product__public_id", "product__name")
        .distinct()
        .order_by("product__name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


RAW_WASTE_QUERYSET_FILTERS = (
    QuerysetFilter(
        "product",
        label="Product",
        lookup="product__public_id__in",
        parse=parse_str,
        description="Product public id(s) (see options).",
        options=_products_with_waste,
    ),
)
RAW_WASTE_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the waste was recorded (default: newest first).",
    ),
    SortOption(
        "product",
        label="Product",
        fields=("product__name",),
        description="Product name, A->Z.",
    ),
    SortOption(
        "quantity_kg",
        label="Quantity",
        fields=("quantity_kg",),
        description="Smallest quantity first.",
    ),
)


class InwardOtherMaterialProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference inside a recipe ref."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class InwardOtherMaterialTypeRefSerializer(serializers.Serializer):
    """Output shape for the ``material_type`` reference inside a recipe ref."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class InwardOtherMaterialRecipeRefSerializer(serializers.Serializer):
    """Output shape for the ``recipe`` reference on a lot."""

    public_id = serializers.CharField()
    material_type = InwardOtherMaterialTypeRefSerializer()
    product = InwardOtherMaterialProductRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of the covered packet, in kg.")


class InwardOtherMaterialPartyRefSerializer(serializers.Serializer):
    """Output shape for the ``party`` reference on a lot."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class InwardOtherMaterialPayloadSerializer(serializers.Serializer):
    """Output shape for one inward-other-material lot."""

    public_id = serializers.CharField()
    recipe = InwardOtherMaterialRecipeRefSerializer()
    party = InwardOtherMaterialPartyRefSerializer()
    quantity = serializers.CharField(help_text="Amount received, in the recipe's unit.")
    effective_date = serializers.DateField(allow_null=True)
    created_by = InwardCreatedByRefSerializer(allow_null=True, help_text="Who booked the lot.")


class CreateInwardOtherMaterialSerializer(serializers.Serializer):
    """Request validation for booking a new other-material lot.

    ``effective_date`` is absent on purpose: booking stamps it with today
    (see ``InwardOtherMaterialsView.post``).
    """

    party = serializers.PrimaryKeyRelatedField(
        queryset=Party.objects.all(),
        error_messages={"required": "Party is required."},
    )
    recipe = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=OtherMaterialRecipe.objects.all(),
        error_messages={"required": "Recipe is required."},
    )
    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity is required."},
        help_text="Amount received, in the recipe's material unit.",
    )

    def validate(self, attrs):
        if attrs["quantity"] <= 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )
        return attrs


class InwardOtherMaterialListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = InwardOtherMaterialPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _material_types_with_other_material_lots(request: Request) -> list[dict]:
    """Every distinct material type that has an inward other-material lot.

    The eligible value set for the ``material_type`` filter: the picker only
    ever needs to offer a material type that actually has a lot behind it.
    """
    rows = (
        InwardOtherMaterial.objects.values_list(
            "recipe__material_type_id", "recipe__material_type__name"
        )
        .distinct()
        .order_by("recipe__material_type__name")
    )
    return [{"value": material_type_id, "label": name} for material_type_id, name in rows]


def _products_with_other_material_lots(request: Request) -> list[dict]:
    """Every distinct product that has an inward other-material lot (via its recipe).

    The eligible value set for the ``product`` filter: the picker only ever
    needs to offer a product that actually has a lot behind it.
    """
    rows = (
        InwardOtherMaterial.objects.values_list(
            "recipe__product__public_id", "recipe__product__name"
        )
        .distinct()
        .order_by("recipe__product__name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


OTHER_LOT_QUERYSET_FILTERS = (
    public_id_filter("IO-"),
    QuerysetFilter(
        "party",
        label="Party",
        lookup="party_id__in",
        description="Party id(s).",
    ),
    QuerysetFilter(
        "material_type",
        label="Material Type",
        lookup="recipe__material_type_id__in",
        description="Material type id(s) (see the recipe; see options).",
        options=_material_types_with_other_material_lots,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        lookup="recipe__product__public_id__in",
        parse=parse_str,
        description="Product public id(s) (see the recipe; see options).",
        options=_products_with_other_material_lots,
    ),
    RangeFilter(
        "effective_date",
        label="Effective Date",
        parse=parse_date,
        suffixes=("gte", "lte"),
        description=(
            "Day the lot started counting toward stock (YYYY-MM-DD, inclusive)."
        ),
    ),
)
OTHER_LOT_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the lot was booked (default: newest first).",
    ),
    SortOption(
        "party",
        label="Party",
        fields=("party__name",),
        description="Party name, A->Z.",
    ),
    SortOption(
        "effective_date",
        label="Effective Date",
        fields=("effective_date",),
        description="Soonest effective date first (undated lots last).",
    ),
)


class RecipeMaterialTypeRefSerializer(serializers.Serializer):
    """Output shape for the ``material_type`` reference on a recipe."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField()


class RecipeProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference on a recipe."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class RecipePayloadSerializer(serializers.Serializer):
    """Output shape for one recipe row."""

    public_id = serializers.CharField()
    product = RecipeProductRefSerializer()
    material_type = RecipeMaterialTypeRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of the covered packet, in kg.")
    quantity = serializers.CharField(help_text="Amount per pack, in the material type's unit.")


class CreateRecipeSerializer(serializers.Serializer):
    """Request validation for creating a new ``OtherMaterialRecipe``."""

    product = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Product.objects.all(),
        error_messages={"required": "Product is required."},
    )
    material_type = serializers.PrimaryKeyRelatedField(
        queryset=OtherMaterialType.objects.all(),
        error_messages={"required": "Material type is required."},
    )
    packet_weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Packet weight is required."},
        help_text="Weight of the covered packet, in kilograms (the product variant).",
    )
    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity is required."},
        help_text=(
            "Multiples of the material per pack, in the material type's unit "
            "(2 leaflets, 2.000 kg cover, 5 litre)."
        ),
    )

    def validate(self, attrs):
        if attrs["packet_weight"] <= 0:
            raise serializers.ValidationError(
                {"packet_weight": "Packet weight must be greater than zero."}
            )
        if attrs["quantity"] <= 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )
        qs = OtherMaterialRecipe.objects.filter(
            product=attrs["product"],
            material_type=attrs["material_type"],
            packet_weight=attrs["packet_weight"],
        )
        if qs.exists():
            raise serializers.ValidationError(
                "A recipe for this product, material type and packet weight "
                "already exists."
            )
        return attrs


class RecipeListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = RecipePayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _products_with_recipes(request: Request) -> list[dict]:
    """Every distinct product that has a live recipe.

    The eligible value set for the ``product`` filter: the picker only ever
    needs to offer a product that actually has a recipe behind it.
    """
    rows = (
        OtherMaterialRecipe.objects.values_list("product__public_id", "product__name")
        .distinct()
        .order_by("product__name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


def _material_types_with_recipes(request: Request) -> list[dict]:
    """Every distinct material type that has a live recipe."""
    rows = (
        OtherMaterialRecipe.objects.values_list("material_type_id", "material_type__name")
        .distinct()
        .order_by("material_type__name")
    )
    return [{"value": material_type_id, "label": name} for material_type_id, name in rows]


RECIPE_QUERYSET_FILTERS = (
    public_id_filter("OMR-"),
    QuerysetFilter(
        "product",
        label="Product",
        lookup="product__public_id__in",
        parse=parse_str,
        description="Product public id(s) (see options).",
        options=_products_with_recipes,
    ),
    QuerysetFilter(
        "material_type",
        label="Material Type",
        lookup="material_type_id__in",
        description="Material type id(s) (see options).",
        options=_material_types_with_recipes,
    ),
)
RECIPE_SORT_OPTIONS = (
    SortOption(
        "product",
        label="Product",
        fields=("product__name",),
        description="Product name, A->Z (default).",
    ),
    SortOption(
        "packet_weight",
        label="Packet Weight",
        fields=("packet_weight",),
        description="Packet weight, lightest first.",
    ),
    SortOption(
        "created_at",
        label="Created",
        description="When the recipe was added.",
    ),
)


class UpdateInwardRawMaterialSerializer(serializers.Serializer):
    """Request validation for updating a raw-material lot (all fields optional).

    Only ``lab_sampling_date`` and ``status`` are accepted: flipping to
    ``In Use`` stamps the effective date with today, reverting to
    ``Lab Testing`` clears it, and ``product`` / ``party`` / ``quantity_kg``
    are immutable. Any unknown key is ignored.
    """

    lab_sampling_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=InwardRawMaterialStatus.choices, required=False
    )

    def validate(self, attrs):
        if self.instance is None:
            return attrs

        current_status = raw_status_of(self.instance)
        requested_status = (
            InwardRawMaterialStatus(attrs["status"]) if "status" in attrs else current_status
        )

        # A status flip may only follow the allowed transitions; sending the
        # current status again is a no-op.
        if requested_status != current_status:
            try:
                assert_raw_status_transition(current_status, requested_status)
            except ValueError as exc:
                raise serializers.ValidationError({"status": str(exc)}) from None

        # Flipping into a dated status (In Use or Rejected) stamps the
        # effective date with today -- the user never types it, and stamped +
        # that status is what the stock read counts (incoming_kg / rejected_kg
        # respectively). Reverting out of one to Lab Testing clears the date
        # so the lot drops back out of stock, and re-stamps lab_sampling_date
        # with today -- the lot is back with the lab as of today, same as a
        # fresh lot. Both keys override whatever the request sent for them
        # (undeclared/declared alike): the view below applies them from
        # validated_data like any other field.
        if (
            current_status not in DATED_RAW_STATUSES
            and requested_status in DATED_RAW_STATUSES
        ):
            attrs["effective_date"] = today()
        elif (
            current_status in DATED_RAW_STATUSES
            and requested_status not in DATED_RAW_STATUSES
        ):
            # Reverting out of In Use removes this lot's kilograms from the
            # raw pool -- refuse it if bags or sample packets are already
            # packed from them. A Rejected lot was never in that pool, so this
            # is always a no-op for it (never refused).
            try:
                assert_raw_lot_removable(self.instance)
            except ValueError as exc:
                raise serializers.ValidationError({"status": str(exc)}) from None
            attrs["effective_date"] = None
            attrs["lab_sampling_date"] = today()

        if "status" in attrs:
            attrs["status"] = status_row_for(requested_status)
        return attrs


class UpdateInwardOtherMaterialSerializer(serializers.Serializer):
    """Request validation for updating an other-material lot.

    Nothing is writable: ``effective_date`` was stamped with today at booking,
    and ``party`` / ``recipe`` / ``quantity`` are immutable -- correct a wrong
    booking by soft-deleting and re-booking.
    """


class RawMaterialStockLineSerializer(serializers.Serializer):
    """Output shape for one product's incoming position."""

    product = serializers.CharField(help_text="Product public id.")
    name = serializers.CharField(help_text="Product name.")
    incoming_kg = serializers.CharField(help_text="Sum of in-use KG with a reached effective date.")
    packed_kg = serializers.CharField(
        help_text="KG already packed into bags or sample packets."
    )
    wasted_kg = serializers.CharField(help_text="KG written off as waste (undated).")
    available_kg = serializers.CharField(
        help_text="KG left to pack: incoming_kg minus packed_kg minus wasted_kg."
    )
    rejected_kg = serializers.CharField(
        help_text="Rejected KG with a reached effective date. Reported only, never spendable."
    )


class RawMaterialStockSerializer(serializers.Serializer):
    """Output shape for the whole incoming raw-material position."""

    as_of = serializers.DateField(help_text="The day the numbers are as of.")
    lines = RawMaterialStockLineSerializer(many=True)


class OtherMaterialTypeRefSerializer(serializers.Serializer):
    """Output shape for the ``material_type`` reference on a line."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField(help_text="Count / kg / litre -- the unit of on_hand.")


class OtherMaterialStockLineSerializer(serializers.Serializer):
    """Output shape for one material type's on-hand position."""

    material_type = OtherMaterialTypeRefSerializer()
    on_hand = serializers.CharField(
        help_text=(
            "Units received (reached effective date) minus units used by the "
            "packets currently packed. Negative when the counts outrun the "
            "recorded inward lots."
        )
    )


class OtherMaterialStockSerializer(serializers.Serializer):
    """Output shape for the whole other-material position."""

    as_of = serializers.DateField(help_text="The day the numbers are as of.")
    lines = OtherMaterialStockLineSerializer(many=True)
