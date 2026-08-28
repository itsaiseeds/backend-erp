import base64
import io

import qrcode
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .models import Admin as AdminProfile
from .models import SalesPerson, User


def _totp_qr_base64(uri: str) -> str:
    """Render ``uri`` as a QR code image and return it base64-encoded (PNG)."""
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("phone_number",)
    list_display = ("phone_number", "name", "email", "is_verified", "totp_enabled", "is_superuser", "is_active")
    search_fields = ("phone_number", "name", "email")
    list_filter = ("is_verified", "is_superuser", "is_staff", "is_active", "totp_enabled")

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("name", "email")}),
        (
            "Authenticator app (TOTP)",
            {"fields": ("is_verified", "totp_enabled", "totp_secret", "totp_qr")},
        ),
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

    readonly_fields = ("date_joined", "last_login", "totp_qr")

    actions = ("generate_totp_qr",)

    @admin.display(description="TOTP QR code")
    def totp_qr(self, obj):
        """Render a scannable QR for this user's TOTP secret, if one is set."""
        if not obj.totp_secret:
            return format_html(
                "<p style='font-style:italic; color:#888;'>"
                "No TOTP secret set. Use the “Generate TOTP QR” action, then "
                "scan the code below into an authenticator app.</p>"
            )
        try:
            uri = obj.totp_provisioning_uri()
            qr_b64 = _totp_qr_base64(uri)
        except Exception:
            return format_html(
                "<p style='color:#c62828;'>Could not render the QR code.</p>"
            )
        status = (
            "<span style='color:#2e7d32; font-weight:600;'>Enabled</span>"
            if obj.totp_enabled
            else "<span style='color:#ef6c00; font-weight:600;'>Pending verification</span>"
        )
        return format_html(
            "<img src='data:image/png;base64,{}' width='220' height='220' "
            "style='border:1px solid #ddd; border-radius:6px;' alt='TOTP QR'/>"
            "<p>Status: {}</p>",
            qr_b64,
            status,
        )

    @admin.action(description="Generate TOTP QR code")
    def generate_totp_qr(self, request, queryset):
        """Set a fresh (unverified) TOTP secret so a QR can be displayed."""
        updated = 0
        for user in queryset:
            user.generate_totp_secret()
            user.save(update_fields=["totp_secret", "totp_enabled"])
            updated += 1
        self.message_user(request, f"Generated a TOTP secret for {updated} user(s).")



@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__name", "user__phone_number")


@admin.register(SalesPerson)
class SalesPersonAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__name", "user__phone_number", "user__created_by__name")


# Hide the default Django auth groups config in favour of our role groups
# (we still keep groups usable, but the default model admin for Group is off).
admin.site.unregister(Group)
