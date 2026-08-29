from django.contrib import admin

from common.admin import SoftDeleteModelAdmin

from .models import Address, City, Country, Pincode, State


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
