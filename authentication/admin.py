from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import Admin as AdminProfile
from .models import MobileVerification, SalesPerson, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("phone_number",)
    list_display = ("phone_number", "name", "email", "is_verified", "is_superuser", "is_active")
    search_fields = ("phone_number", "name", "email")
    list_filter = ("is_verified", "is_superuser", "is_staff", "is_active")

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("name", "email")}),
        ("Verification", {"fields": ("is_verified",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Account", {"fields": ("created_by", "date_joined", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "name", "email", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ("date_joined", "last_login")


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__name", "user__phone_number")


@admin.register(SalesPerson)
class SalesPersonAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__name", "user__phone_number", "user__created_by__name")


@admin.register(MobileVerification)
class MobileVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "otp", "is_used", "expires_at")
    search_fields = ("phone_number", "user__name")
    list_filter = ("is_used",)
    readonly_fields = ("user", "phone_number", "created_at")


# Hide the default Django auth groups config in favour of our role groups
# (we still keep groups usable, but the default model admin for Group is off).
admin.site.unregister(Group)
