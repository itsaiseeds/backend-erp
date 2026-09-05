from django import forms
from django.contrib import admin

from common.admin import AUDIT_FIELDS, SoftDeleteModelAdmin

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
    DispatchDetails,
    Order,
    OrderItem,
    Pincode,
    PrivateDispatchDetails,
    Product,
    ProductPackaging,
    State,
    Status,
    TransportAgency,
)


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
        "company_name",
        "gst_number",
        "company_phone",
        "status",
        "verified_by",
        "created_by",
        "created_at",
    )
    search_fields = ("company_name", "gst_number", "company_phone")
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


@admin.register(Product)
class ProductAdmin(SoftDeleteModelAdmin):
    list_display = ("public_id", "name", "crop", "buying_price", "selling_price", "created_at")
    search_fields = ("public_id", "name", "crop__name")
    list_filter = ("crop",)
    autocomplete_fields = ("crop",)
    list_select_related = ("crop",)
    ordering = ("name",)


class ProductPackagingAdminForm(forms.ModelForm):
    """Admin form for ``ProductPackaging``.

    ``selling_price`` is ``NOT NULL`` at the DB and model level, but this form
    lets an admin leave it blank -- when it does, ``clean_selling_price``
    fills in ``packing_bags * product.selling_price`` so the underlying
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
            "Leave blank to default to packing_bags × product.selling_price."
        )

    def clean_selling_price(self):
        value = self.cleaned_data.get("selling_price")
        if value not in (None, ""):
            return value
        product = self.cleaned_data.get("product")
        packing_bags = self.cleaned_data.get("packing_bags")
        if product is None or packing_bags is None:
            # Let the other fields' own validation surface first.
            return value
        return packing_bags * product.selling_price


@admin.register(ProductPackaging)
class ProductPackagingAdmin(SoftDeleteModelAdmin):
    form = ProductPackagingAdminForm
    list_display = (
        "public_id",
        "product",
        "packing_bag_weight",
        "packing_bags",
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


class OrderItemInline(CreatedByStampInlineMixin, admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product_packaging",)


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


@admin.register(OrderItem)
class OrderItemAdmin(SoftDeleteModelAdmin):
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
