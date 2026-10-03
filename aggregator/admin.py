from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.serializers import ValidationError as DRFValidationError

from common.admin import AUDIT_FIELDS, SoftDeleteModelAdmin
from common.models import indian_now
from common.storage import delete_image, upload_image

from .CustomOrderOperations import assert_loose_stock_covers
from .InwardOperations import raw_status_detail
from .models import (
    Address,
    City,
    Client,
    ClientAddress,
    ClientContact,
    ClientTransportAgency,
    Contact,
    Country,
    Crop,
    CustomOrder,
    CustomOrderItem,
    DispatchDetails,
    DispatchEntry,
    DispatchEntryItem,
    FarmerVisit,
    FarmerVisitCrop,
    FarmerVisitProduct,
    FieldTrip,
    InventorySnapshot,
    InwardOtherMaterial,
    InwardRawMaterial,
    LooseStockSnapshot,
    Notification,
    Order,
    OrderItem,
    OtherMaterialRecipe,
    OtherMaterialType,
    PackedRecipeLayer,
    Party,
    Pincode,
    PrivateDispatchDetails,
    Product,
    ProductDescriptionItem,
    ProductPackaging,
    PushDevice,
    RawMaterialWaste,
    Stage,
    State,
    Status,
    StatusIds,
    StockEvent,
    StockEventDetail,
    StockEventLine,
    StockEventType,
    TransportAgency,
)
from .StockLedgerOperations import products_with_pools, recording

# An order's lifecycle and verification: moved only by the lifecycle verbs
# (verify / dispatch / revert / hold / reject ...), which carry the status
# guards and stock checks. The admin shows them but never writes them.
ORDER_LIFECYCLE_FIELDS = (
    "status",
    "verified_by",
    "verified_at",
    "dispatch_details",
    "private_dispatch_details",
)


class StockLedgerAdminMixin:
    """Record the stock an admin add/change form moves in the stock ledger.

    The admin form is parsed after the view starts, so which products it will
    touch is unknown up front: every product with a pool is tracked, which is
    affordable because these forms are rare, superuser-only maintenance. The
    whole add/change POST runs inside one recording, so the parent row and its
    inlines are covered together and a form that fails records nothing.

    ``ledger_event_type`` ``None`` means a count write (classified by packed
    packets). ``ledger_refine`` may set the detail once the saved row is known.
    """

    ledger_event_type: StockEventType | None = None
    ledger_detail: StockEventDetail = StockEventDetail.NONE

    def ledger_refine(self, rec, obj, change: bool) -> None:
        """Hook: adjust ``rec.detail`` for the row just saved."""

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method != "POST":
            return super().changeform_view(request, object_id, form_url, extra_context)
        with recording(
            self.ledger_event_type,
            self.ledger_detail,
            products_with_pools(),
            actor=request.user,
        ) as rec:
            request._stock_ledger_recording = rec
            return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        rec = getattr(request, "_stock_ledger_recording", None)
        if rec is not None:
            rec.source = obj
            self.ledger_refine(rec, obj, change)


class UnusableProductAdminMixin:
    """Freeze the rows of an unusable product in the admin (``Product.is_usable``).

    A row whose product is frozen is read-only -- no change, no delete -- and a
    form cannot add or move a row onto a frozen product. Deleting several rows
    at once is stopped by each model's own ``guard_soft_delete``, like every other
    refusal.

    ``product_path`` is the dotted path from the saved row to its product, and
    ``form_product_path`` the same path from the form's cleaned data (they differ
    where the product is reached through another field).
    """

    product_path = "product"
    form_product_path = "product"

    @staticmethod
    def _walk(start, path: str):
        current = start
        for part in path.split("."):
            current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def _is_frozen(self, obj) -> bool:
        product = self._walk(obj, self.product_path)
        return product is not None and not product.is_usable

    def has_change_permission(self, request, obj=None):
        if obj is not None and self._is_frozen(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and self._is_frozen(obj):
            return False
        return super().has_delete_permission(request, obj)

    def get_form(self, request, obj=None, change=False, **kwargs):
        base = super().get_form(request, obj, change=change, **kwargs)
        first, _, rest = self.form_product_path.partition(".")
        walk = self._walk

        class UsableProductForm(base):
            def clean(self):
                cleaned = super().clean()
                value = (cleaned or {}).get(first)
                product = walk(value, rest) if rest and value is not None else value
                if product is not None and not product.is_usable:
                    raise forms.ValidationError(
                        f"Product '{product.name}' is not usable, so nothing can be "
                        "created or changed for it."
                    )
                return cleaned

        return UsableProductForm


class ReturnLotAdminMixin:
    """Make a lot an accepted return booked read-only, and unassignable.

    Such a lot (``return_order`` set) is owned by its return: only reverting the
    accept removes it (``ReturnOrderOperations``), so the admin may neither
    change nor delete it. ``return_order`` is never editable here, so a lot
    cannot be pointed at a return by hand either.
    """

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.return_order_id is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.return_order_id is not None:
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), "return_order")


class CreatedByStampInlineMixin:
    """Base for inlines on ``CreatedByModel`` children.

    ``created_by`` is required (``blank=False``) but must not be filled in by
    hand, so it is excluded from the inline form and stamped with the acting
    user in the parent admin ``save_formset``.
    """

    exclude = ("created_by", *AUDIT_FIELDS)


class SoftDeleteParentAdmin(SoftDeleteModelAdmin):
    """``SoftDeleteModelAdmin`` that also stamps ``created_by`` on inline rows."""

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if hasattr(obj, "created_by_id") and obj.created_by_id is None:
                obj.created_by = request.user
            obj.save()
        formset.save_m2m()
        for obj in formset.deleted_objects:
            obj.delete(deleted_by=request.user)


@admin.register(Country)
class CountryAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "iso_code", "created_by", "created_at")
    search_fields = ("name", "iso_code")
    ordering = ("name",)


@admin.register(State)
class StateAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "code", "country", "created_by", "created_at")
    search_fields = ("name", "code", "country__name")
    list_filter = ("country",)
    autocomplete_fields = ("country",)
    list_select_related = ("country",)


@admin.register(City)
class CityAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "state", "country", "created_by", "created_at")
    search_fields = ("name", "state__name", "state__country__name")
    list_filter = ("state__country",)
    autocomplete_fields = ("state",)
    list_select_related = ("state__country",)


@admin.register(Pincode)
class PincodeAdmin(SoftDeleteModelAdmin):
    list_display = ("code", "city", "state", "country", "created_by", "created_at")
    search_fields = ("code", "city__name", "city__state__name")
    list_filter = ("city__state",)
    autocomplete_fields = ("city",)
    list_select_related = ("city__state__country",)


@admin.register(Address)
class AddressAdmin(SoftDeleteModelAdmin):
    list_display = (
        "address_line_1",
        "address_line_2",
        "pincode",
        "city",
        "state",
        "country",
        "created_by",
        "created_at",
    )
    search_fields = (
        "address_line_1",
        "address_line_2",
        "pincode__code",
        "city__name",
        "state__name",
        "country__name",
    )
    list_filter = ("country", "state")
    autocomplete_fields = ("pincode", "city", "state", "country")
    list_select_related = ("pincode", "city", "state", "country")
    list_per_page = 50


@admin.register(Status)
class StatusAdmin(SoftDeleteModelAdmin):
    list_display = ("code", "name", "sequence", "created_at")
    search_fields = ("code", "name")
    ordering = ("sequence", "code")


@admin.register(Stage)
class StageAdmin(SoftDeleteModelAdmin):
    list_display = ("code", "name", "sequence", "created_at")
    search_fields = ("code", "name")
    ordering = ("sequence", "code")


@admin.register(TransportAgency)
class TransportAgencyAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Contact)
class ContactAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "phone_number", "created_by", "created_at")
    search_fields = ("name", "phone_number")
    ordering = ("name",)


@admin.register(Crop)
class CropAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


class ClientAddressInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = ClientAddress
    extra = 0
    autocomplete_fields = ("address",)


class ClientContactInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = ClientContact
    extra = 0
    autocomplete_fields = ("contact",)


class ClientTransportAgencyInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = ClientTransportAgency
    extra = 0
    autocomplete_fields = ("transport_agency",)


@admin.register(Client)
class ClientAdmin(SoftDeleteParentAdmin):
    list_display = (
        "public_id",
        "company_name",
        "gst_number",
        "company_phone",
        "status",
        "verified_by",
        "created_by",
        "created_at",
    )
    search_fields = ("public_id", "company_name", "gst_number", "company_phone")
    list_filter = ("status",)
    autocomplete_fields = ("status", "verified_by")
    list_select_related = ("status", "verified_by")
    inlines = (ClientAddressInline, ClientContactInline, ClientTransportAgencyInline)


@admin.register(ClientAddress)
class ClientAddressAdmin(SoftDeleteModelAdmin):
    list_display = ("client", "address", "label", "is_primary", "created_at")
    search_fields = ("client__company_name", "address__address_line_1", "label")
    list_filter = ("is_primary",)
    autocomplete_fields = ("client", "address")
    list_select_related = ("client", "address")


@admin.register(ClientContact)
class ClientContactAdmin(SoftDeleteModelAdmin):
    list_display = ("client", "contact", "role", "is_primary", "created_at")
    search_fields = ("client__company_name", "contact__name", "role")
    list_filter = ("is_primary",)
    autocomplete_fields = ("client", "contact")
    list_select_related = ("client", "contact")


@admin.register(ClientTransportAgency)
class ClientTransportAgencyAdmin(SoftDeleteModelAdmin):
    list_display = ("client", "transport_agency", "is_primary", "created_at")
    search_fields = ("client__company_name", "transport_agency__name")
    list_filter = ("is_primary",)
    autocomplete_fields = ("client", "transport_agency")
    list_select_related = ("client", "transport_agency")


class ProductAdminForm(forms.ModelForm):
    """Admin form for ``Product``, with a file field for the picture.

    ``image_url`` itself is read-only on the admin (see ``ProductAdmin``): it is
    a location, not something to hand-edit. Uploading here goes through the same
    ``common.storage`` path the API uses -- the Supabase bucket when configured,
    ``MEDIA_ROOT`` otherwise.
    """

    image = forms.ImageField(
        required=False,
        label="image",
        help_text=(
            "Upload to set or replace the picture. JPEG, PNG or WebP, 5 MB max. "
            "Leave blank to keep the current one."
        ),
    )

    class Meta:
        model = Product
        fields = "__all__"

    def clean_image(self):
        """Validate and upload, so a rejected file is a form error, not a 500.

        The upload happens during validation rather than in ``save`` because
        that is the only place an admin can be shown a readable message. The
        cost is that a file uploaded alongside *another* invalid field is
        orphaned in the bucket -- cheap, and the alternative is an error page.
        """
        image = self.cleaned_data.get("image")
        if not image:
            return image
        try:
            # upload_image validates type and size before touching the network.
            self._uploaded_image_url = upload_image(image, folder="products")
        except DRFValidationError as exc:
            raise forms.ValidationError(exc.detail) from exc
        return image

    def save(self, commit=True):
        product = super().save(commit=False)
        uploaded = getattr(self, "_uploaded_image_url", "")
        replaced = ""
        if uploaded:
            replaced = product.image_url
            product.image_url = uploaded
        if commit:
            product.save()
            if replaced:
                delete_image(replaced)
        return product


class ProductDescriptionItemInline(CreatedByStampInlineMixin, admin.TabularInline):
    """The product's marketing bullets, edited in ``sequence`` order.

    Ordered by the model's own Meta, so the rows appear here in exactly the
    order the Android catalogue renders them.
    """

    model = ProductDescriptionItem
    extra = 0


@admin.register(Product)
class ProductAdmin(SoftDeleteParentAdmin):
    form = ProductAdminForm
    list_display = (
        "public_id",
        "name",
        "crop",
        "stage",
        "selling_price",
        "is_usable",
        "created_at",
    )
    search_fields = ("public_id", "name", "crop__name")
    list_filter = ("crop", "stage", "is_usable")
    autocomplete_fields = ("crop", "stage")
    list_select_related = ("crop", "stage")
    readonly_fields = ("image_url",)
    ordering = ("name",)
    inlines = (ProductDescriptionItemInline,)


@admin.register(ProductDescriptionItem)
class ProductDescriptionItemAdmin(SoftDeleteModelAdmin):
    list_display = ("product", "sequence", "text", "created_at")
    search_fields = ("product__name", "product__public_id", "text")
    list_filter = ("product__crop",)
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    ordering = ("product__name", "sequence")


class ProductPackagingAdminForm(forms.ModelForm):
    """Admin form for ``ProductPackaging``.

    ``selling_price`` is ``NOT NULL`` at the DB and model level, but this form
    lets an admin leave it blank -- when it does, ``clean_selling_price``
    fills in ``packets * product.price_for_weight(packet_weight)`` so the underlying
    ``ModelForm._post_clean`` sees a valid value and the model's ``full_clean``
    passes. This fallback is intentionally scoped to the admin: programmatic
    callers (``ProductOperations.add_packaging``) already handle the default.
    """

    class Meta:
        model = ProductPackaging
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selling_price = self.fields["selling_price"]
        selling_price.required = False
        selling_price.help_text = (
            "Leave blank to default to packets × packet_weight × the "
            "product's per-kilogram selling_price."
        )

    def clean_selling_price(self):
        value = self.cleaned_data.get("selling_price")
        if value not in (None, ""):
            return value
        product = self.cleaned_data.get("product")
        packets = self.cleaned_data.get("packets")
        packet_weight = self.cleaned_data.get("packet_weight")
        if product is None or packets is None or packet_weight is None:
            # Let the other fields' own validation surface first.
            return value
        return packets * product.price_for_weight(packet_weight)


@admin.register(ProductPackaging)
class ProductPackagingAdmin(UnusableProductAdminMixin, SoftDeleteModelAdmin):
    form = ProductPackagingAdminForm
    list_display = (
        "public_id",
        "product",
        "packet_weight",
        "packets",
        "selling_price",
        "created_at",
    )
    search_fields = ("public_id", "product__name", "product__crop__name")
    list_filter = ("product__crop",)
    autocomplete_fields = ("product",)
    list_select_related = ("product",)


@admin.register(DispatchDetails)
class DispatchDetailsAdmin(SoftDeleteModelAdmin):
    list_display = (
        "client",
        "lr_number",
        "dispatch_date",
        "from_city",
        "to_city",
        "dispatched_by",
    )
    search_fields = ("client__company_name", "lr_number")
    autocomplete_fields = ("client", "dispatched_by", "from_city", "to_city")
    list_select_related = ("client", "from_city", "to_city")


@admin.register(PrivateDispatchDetails)
class PrivateDispatchDetailsAdmin(SoftDeleteModelAdmin):
    list_display = (
        "client",
        "vehicle_number",
        "driver_number",
        "dispatch_date",
        "from_city",
        "to_city",
        "dispatched_by",
    )
    search_fields = ("client__company_name", "vehicle_number", "driver_number")
    autocomplete_fields = ("client", "dispatched_by", "from_city", "to_city")
    list_select_related = ("client", "from_city", "to_city")


class DispatchEntryItemInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = DispatchEntryItem
    extra = 0
    autocomplete_fields = ("product_packaging",)


@admin.register(DispatchEntry)
class DispatchEntryAdmin(SoftDeleteParentAdmin):
    list_display = (
        "public_id",
        "challan_number",
        "order",
        "client",
        "lr_number",
        "dispatch_date",
        "from_city",
        "to_city",
        "vehicle_number",
    )
    search_fields = (
        "public_id",
        "challan_number",
        "order__public_id",
        "client__company_name",
        "dispatch_details__lr_number",
        "vehicle_number",
    )
    autocomplete_fields = (
        "order",
        "dispatch_details",
        "client",
        "client_address",
        "from_city",
        "to_city",
    )
    list_select_related = ("order", "client", "dispatch_details", "from_city", "to_city")
    inlines = (DispatchEntryItemInline,)

    @admin.display(description="LR number")
    def lr_number(self, obj):
        return obj.lr_number or "-"


@admin.register(DispatchEntryItem)
class DispatchEntryItemAdmin(SoftDeleteModelAdmin):
    list_display = (
        "dispatch_entry",
        "product_packaging",
        "lot_number",
        "quantity",
        "negotiated_selling_price",
        "created_at",
    )
    search_fields = (
        "dispatch_entry__public_id",
        "lot_number",
        "product_packaging__product__name",
    )
    autocomplete_fields = ("dispatch_entry", "product_packaging")
    list_select_related = ("dispatch_entry", "product_packaging__product")


class OrderItemInline(CreatedByStampInlineMixin, admin.TabularInline):
    """An order's lines, view-only.

    Lines are reservations once the order is confirmed; they change only
    through ``edit-order``, which re-checks stock.
    """

    model = OrderItem
    extra = 0
    autocomplete_fields = ("product_packaging",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(SoftDeleteParentAdmin):
    list_display = (
        "public_id",
        "client",
        "status",
        "expected_delivery_date",
        "actual_delivery_date",
        "created_by",
        "created_at",
    )
    search_fields = ("public_id", "client__company_name", "special_comments")
    list_filter = ("status",)
    autocomplete_fields = (
        "client",
        "delivery_address",
        "status",
        "dispatch_details",
        "private_dispatch_details",
    )
    list_select_related = ("client", "status")
    inlines = (OrderItemInline,)

    def has_add_permission(self, request):
        """Orders are booked from the app, never here."""
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), *ORDER_LIFECYCLE_FIELDS)


class ViewOnlyAdminMixin:
    """View-only: the rows are maintained by the operations layer alone."""

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(OrderItem)
class OrderItemAdmin(ViewOnlyAdminMixin, SoftDeleteModelAdmin):
    list_display = (
        "order",
        "product_packaging",
        "negotiated_selling_price",
        "quantity",
        "created_at",
    )
    search_fields = ("order__client__company_name", "product_packaging__product__name")
    autocomplete_fields = ("order", "product_packaging")
    list_select_related = ("order", "product_packaging__product")


# -- Stock ---------------------------------------------------------------------
#
# Two pools in two tables: sealed bags per packaging (InventorySnapshot) and
# loose packets per (product, packet_weight) (LooseStockSnapshot). Writing
# either requires ``Admin.can_update_stock_count``, enforced by each model's
# ``clean()`` against the stamped ``created_by`` -- so an admin user without
# that flag will be rejected on save here just as through the API.


@admin.register(InventorySnapshot)
class InventorySnapshotAdmin(
    UnusableProductAdminMixin, StockLedgerAdminMixin, SoftDeleteModelAdmin
):
    product_path = "product_packaging.product"
    form_product_path = "product_packaging.product"
    ledger_detail = StockEventDetail.BAG_COUNT

    list_display = (
        "public_id",
        "snapshot_date",
        "product_packaging",
        "bags",
        "total_packets",
        "counted_at",
        "created_by",
        "created_at",
    )
    search_fields = (
        "public_id",
        "product_packaging__product__name",
        "product_packaging__public_id",
    )
    list_filter = ("snapshot_date", "product_packaging__product__crop")
    autocomplete_fields = ("product_packaging",)
    # total_packets reads product_packaging.packets; select_related keeps the
    # changelist off an N+1.
    list_select_related = ("product_packaging__product",)
    date_hierarchy = "snapshot_date"
    ordering = ("-snapshot_date", "product_packaging__product__name")


@admin.register(LooseStockSnapshot)
class LooseStockSnapshotAdmin(
    UnusableProductAdminMixin, StockLedgerAdminMixin, SoftDeleteModelAdmin
):
    ledger_detail = StockEventDetail.LOOSE_COUNT

    list_display = (
        "public_id",
        "snapshot_date",
        "product",
        "packet_weight",
        "packets",
        "total_weight",
        "counted_at",
        "created_by",
        "created_at",
    )
    search_fields = ("public_id", "product__name", "product__crop__name")
    list_filter = ("snapshot_date", "product__crop")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    date_hierarchy = "snapshot_date"
    ordering = ("-snapshot_date", "product__name", "packet_weight")


# -- Custom orders -------------------------------------------------------------


class CustomOrderItemFormSet(forms.BaseInlineFormSet):
    """A new custom order's lines, checked against loose stock as a whole.

    The same gate as ``CustomOrderOperations.create_custom_order``: lines are
    summed per ``(product, packet_weight)`` pool before the check, under the
    pools' locks, which Django's atomic add view holds until the order is
    saved. A shortfall is an ordinary form error.
    """

    def clean(self):
        super().clean()
        if self.instance.pk is not None or any(self.errors):
            return  # lines are view-only on an existing order
        needed: dict = {}
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE"):
                continue
            pool = (data["product"], data["packet_weight"])
            needed[pool] = needed.get(pool, 0) + data["packets"]
        if not needed:
            raise forms.ValidationError("A custom order needs at least one line.")
        try:
            assert_loose_stock_covers(needed)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages) from None


class CustomOrderItemInline(CreatedByStampInlineMixin, admin.TabularInline):
    """A custom order's lines: written once, when the order is added.

    A custom order confirms -- reserves its packets -- as it is created, so its
    lines are fixed from then on.
    """

    model = CustomOrderItem
    formset = CustomOrderItemFormSet
    extra = 0
    autocomplete_fields = ("product",)

    def has_add_permission(self, request, obj=None):
        return obj is None

    def has_change_permission(self, request, obj=None):
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return obj is None


@admin.register(CustomOrder)
class CustomOrderAdmin(StockLedgerAdminMixin, SoftDeleteParentAdmin):
    ledger_event_type = StockEventType.ORDER_CONFIRMED
    ledger_detail = StockEventDetail.CUSTOM_ORDER_CREATED

    list_display = (
        "public_id",
        "client",
        "status",
        "expected_delivery_date",
        "actual_delivery_date",
        "verified_by",
        "created_by",
        "created_at",
    )
    search_fields = ("public_id", "client__company_name", "special_comments")
    list_filter = ("status",)
    autocomplete_fields = (
        "client",
        "delivery_address",
        "status",
        "dispatch_details",
        "private_dispatch_details",
        "verified_by",
    )
    list_select_related = ("client", "status", "verified_by")
    inlines = (CustomOrderItemInline,)

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), *ORDER_LIFECYCLE_FIELDS)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        if obj is not None:
            return form
        user = request.user

        class AddCustomOrderForm(form):
            def clean(self):
                cleaned = super().clean()
                if not (user.is_admin_user or user.is_superuser):
                    raise forms.ValidationError(
                        "Custom orders can only be booked by a sales admin."
                    )
                return cleaned

        return AddCustomOrderForm

    def save_model(self, request, obj, form, change):
        """A new custom order is born CONFIRMED and verified by its creator.

        The same as ``CustomOrderOperations.create_custom_order``: creating one
        *is* verifying it, and its lines were checked against loose stock by
        ``CustomOrderItemFormSet``.
        """
        if not change:
            obj.status = Status.by_id(StatusIds.CONFIRMED)
            obj.verified_by = request.user
            obj.verified_at = indian_now()
        super().save_model(request, obj, form, change)


@admin.register(CustomOrderItem)
class CustomOrderItemAdmin(ViewOnlyAdminMixin, SoftDeleteModelAdmin):
    list_display = (
        "custom_order",
        "product",
        "packet_weight",
        "negotiated_selling_price",
        "packets",
        "created_at",
    )
    search_fields = ("custom_order__public_id", "product__name")
    autocomplete_fields = ("custom_order", "product")
    list_select_related = ("custom_order", "product")


# -- Inward movements ---------------------------------------------------------


@admin.register(Party)
class PartyAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "city", "created_by", "created_at")
    search_fields = ("name", "city__name", "city__state__name")
    autocomplete_fields = ("city",)
    list_select_related = ("city__state",)
    ordering = ("name",)


@admin.register(InwardRawMaterial)
class InwardRawMaterialAdmin(
    UnusableProductAdminMixin,
    ReturnLotAdminMixin,
    StockLedgerAdminMixin,
    SoftDeleteModelAdmin,
):
    ledger_event_type = StockEventType.INWARD_OPERATIONS
    ledger_detail = StockEventDetail.RAW_LOT_IN_USE

    def ledger_refine(self, rec, obj, change):
        rec.detail = raw_status_detail(obj)

    list_display = (
        "public_id",
        "product",
        "party",
        "lot_no",
        "quantity_kg",
        "status",
        "effective_date",
        "lab_sampling_date",
        "created_by",
        "created_at",
    )
    search_fields = (
        "public_id",
        "product__name",
        "product__crop__name",
        "party__name",
        "lot_no",
    )
    list_filter = ("status", "effective_date")
    autocomplete_fields = ("product", "party", "status")
    list_select_related = ("product", "party", "status")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(RawMaterialWaste)
class RawMaterialWasteAdmin(
    UnusableProductAdminMixin, StockLedgerAdminMixin, SoftDeleteModelAdmin
):
    ledger_event_type = StockEventType.RAW_WASTED
    ledger_detail = StockEventDetail.WASTE_RECORDED

    def ledger_refine(self, rec, obj, change):
        if change:
            rec.detail = StockEventDetail.WASTE_EDITED

    list_display = (
        "public_id",
        "product",
        "quantity_kg",
        "reason",
        "created_by",
        "created_at",
    )
    search_fields = ("public_id", "product__name", "reason")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(OtherMaterialType)
class OtherMaterialTypeAdmin(SoftDeleteModelAdmin):
    list_display = ("name", "unit_type", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(OtherMaterialRecipe)
class OtherMaterialRecipeAdmin(UnusableProductAdminMixin, SoftDeleteModelAdmin):
    list_display = (
        "public_id",
        "product",
        "material_type",
        "packet_weight",
        "quantity",
        "created_at",
    )
    search_fields = ("public_id", "product__name", "material_type__name")
    list_filter = ("material_type", "product__crop")
    autocomplete_fields = ("product", "material_type")
    list_select_related = ("product", "material_type")
    ordering = ("product__name", "packet_weight")


@admin.register(InwardOtherMaterial)
class InwardOtherMaterialAdmin(
    UnusableProductAdminMixin,
    ReturnLotAdminMixin,
    StockLedgerAdminMixin,
    SoftDeleteModelAdmin,
):
    product_path = "recipe.product"
    form_product_path = "recipe.product"
    ledger_event_type = StockEventType.INWARD_OPERATIONS
    ledger_detail = StockEventDetail.OTHER_MATERIAL_RECEIVED

    def ledger_refine(self, rec, obj, change):
        if change:
            rec.detail = StockEventDetail.OTHER_MATERIAL_EDITED

    list_display = (
        "public_id",
        "recipe",
        "party",
        "quantity",
        "effective_date",
        "created_by",
        "created_at",
    )
    search_fields = (
        "public_id",
        "recipe__product__name",
        "recipe__material_type__name",
        "party__name",
    )
    autocomplete_fields = ("party", "recipe")
    list_select_related = ("recipe__product", "recipe__material_type", "party")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(FieldTrip)
class FieldTripAdmin(SoftDeleteModelAdmin):
    list_display = (
        "public_id",
        "created_by",
        "city",
        "village",
        "status",
        "expected_start_at",
        "started_at",
        "ended_at",
        "approved_by",
    )
    search_fields = ("public_id", "village", "city__name", "created_by__name")
    list_filter = ("status",)
    autocomplete_fields = ("city", "status")
    list_select_related = ("created_by", "city", "status", "approved_by")
    date_hierarchy = "expected_start_at"
    ordering = ("-expected_start_at",)


class FarmerVisitCropInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = FarmerVisitCrop
    extra = 0


class FarmerVisitProductInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = FarmerVisitProduct
    extra = 0
    autocomplete_fields = ("product",)


@admin.register(FarmerVisit)
class FarmerVisitAdmin(SoftDeleteParentAdmin):
    list_display = (
        "public_id",
        "field_trip",
        "farmer_name",
        "contact_number",
        "village",
        "land_area_bigha",
        "created_at",
    )
    search_fields = ("public_id", "farmer_name", "contact_number", "village")
    autocomplete_fields = ("field_trip",)
    list_select_related = ("field_trip",)
    ordering = ("-created_at",)
    inlines = (FarmerVisitCropInline, FarmerVisitProductInline)


@admin.register(FarmerVisitCrop)
class FarmerVisitCropAdmin(SoftDeleteModelAdmin):
    list_display = ("farmer_visit", "crop", "created_at")
    autocomplete_fields = ("farmer_visit",)
    list_select_related = ("farmer_visit", "crop")


@admin.register(FarmerVisitProduct)
class FarmerVisitProductAdmin(SoftDeleteModelAdmin):
    list_display = ("farmer_visit", "product", "created_at")
    autocomplete_fields = ("farmer_visit", "product")
    list_select_related = ("farmer_visit", "product")


# -- Push notifications ---------------------------------------------------------
#
# Both tables are written by ``NotificationOperations`` (and, for the device
# token, by the app at login). They are registered here with full CRUD so a
# mis-sent notification can be pulled and a phone that should no longer receive
# pushes can be un-registered by hand.


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    """The phones a user is signed in on, so support can spot stale registrations.

    ``updated_at`` is the app's last login or token refresh, so this doubles as
    a "last seen" list. Deleting a row un-registers that one phone; the token
    comes back only when that app next logs in.
    """

    list_display = ("id", "user", "app_version", "token", "updated_at")
    list_filter = ("app_version",)
    search_fields = ("fcm_token", "user__name", "user__phone_number")
    date_hierarchy = "updated_at"
    ordering = ("-updated_at", "-id")
    list_select_related = ("user",)

    @admin.display(description="token", ordering="fcm_token")
    def token(self, obj):
        return f"{obj.fcm_token[:12]}..."


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """The in-app inbox: what was sent, to whom, and who has read it."""

    list_display = ("id", "recipient", "title", "event_type", "order", "read", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = (
        "title",
        "body",
        "recipient__name",
        "recipient__phone_number",
        "order__public_id",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    autocomplete_fields = ("order",)
    list_select_related = ("recipient", "order")

    @admin.display(description="read", boolean=True, ordering="read_at")
    def read(self, obj):
        return obj.read_at is not None


# -- Stock ledger ---------------------------------------------------------------
#
# The product stock ledger is append-only and written only by
# ``StockLedgerOperations.recording``. Nobody edits or deletes it by hand -- not
# even a superuser -- because a hand-edited delta makes it disagree with the live
# figures (``manage.py check_stock_ledger`` would then report the drift). These
# admins are therefore strictly read-only, for inspection and support.


class ReadOnlyLedgerAdminMixin:
    """No add, change or delete for anyone."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StockEventLineInline(ReadOnlyLedgerAdminMixin, admin.TabularInline):
    """What one event moved in each pool, as signed deltas."""

    model = StockEventLine
    extra = 0
    can_delete = False
    fields = (
        "pool_kind",
        "product_packaging",
        "packet_weight",
        "material_type",
        "d_on_hand",
        "d_reserved",
        "d_consumed",
        "d_incoming",
        "d_packed",
        "d_rejected",
        "d_wasted",
    )
    readonly_fields = fields


@admin.register(StockEvent)
class StockEventAdmin(ReadOnlyLedgerAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "occurred_at",
        "product",
        "event",
        "detail_name",
        "source",
        "actor",
        "line_count",
    )
    list_filter = ("event_type", "detail", "occurred_at")
    search_fields = (
        "product__name",
        "product__public_id",
        "order__public_id",
        "custom_order__public_id",
        "inward_raw_material__public_id",
        "inward_raw_material__lot_no",
        "inward_other_material__public_id",
        "raw_material_waste__public_id",
        "inventory_snapshot__public_id",
        "loose_stock_snapshot__public_id",
        "actor__name",
    )
    date_hierarchy = "occurred_at"
    ordering = ("-occurred_at", "-id")
    inlines = (StockEventLineInline,)
    list_select_related = (
        "product",
        "actor",
        "order",
        "custom_order",
        "inward_raw_material",
        "inward_other_material",
        "raw_material_waste",
        "inventory_snapshot",
        "loose_stock_snapshot",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("lines")

    @admin.display(description="event", ordering="event_type")
    def event(self, obj):
        return StockEventType(obj.event_type).name

    @admin.display(description="detail", ordering="detail")
    def detail_name(self, obj):
        return StockEventDetail(obj.detail).name

    @admin.display(description="source")
    def source(self, obj):
        for name in (
            "order",
            "custom_order",
            "inward_raw_material",
            "inward_other_material",
            "raw_material_waste",
            "inventory_snapshot",
            "loose_stock_snapshot",
        ):
            row = getattr(obj, name)
            if row is not None:
                return row.public_id
        return "-"

    @admin.display(description="lines")
    def line_count(self, obj):
        return len(obj.lines.all())


@admin.register(PackedRecipeLayer)
class PackedRecipeLayerAdmin(ReadOnlyLedgerAdminMixin, admin.ModelAdmin):
    """Packets of a count row packed under one recipe (frozen packing-material usage)."""

    list_display = (
        "id",
        "inventory_snapshot",
        "loose_stock_snapshot",
        "material_type",
        "recipe",
        "packets",
        "opened_at",
    )
    list_filter = ("material_type",)
    search_fields = (
        "inventory_snapshot__public_id",
        "loose_stock_snapshot__public_id",
        "recipe__public_id",
    )
    ordering = ("-opened_at", "-id")
    list_select_related = (
        "inventory_snapshot__product_packaging__product",
        "loose_stock_snapshot__product",
        "material_type",
        "recipe",
    )
