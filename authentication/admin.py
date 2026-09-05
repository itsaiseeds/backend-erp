import base64
import io

import qrcode  # type: ignore[import-untyped]
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.utils.html import format_html

from common.admin import AuditFieldsAdminMixin, SoftDeleteModelAdmin

from .models import Admin as AdminProfile
from .models import SalesPerson, User


def _totp_qr_base64(uri: str) -> str:
    """Render ``uri`` as a QR code image and return it base64-encoded (PNG)."""
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class UserCreationForm(BaseUserCreationForm):
    """Admin form for creating users.

    Only non-superusers can be created here (superusers are seeded by the
    ``createsuperuser_if_not_exists`` command). The acting user (request.user)
    is recorded automatically as both ``created_by`` and ``verified_by``, and
    every new account ships with an active TOTP secret (``is_verified`` and
    ``totp_enabled`` are both True).

    A password is never required: the app authenticates via TOTP, and a
    password only matters for Django-admin login. When left blank, the account
    gets an unusable password.
    """

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        strip=False,
        required=False,
        help_text="Optional. Only needed if this user should log in to the Django admin.",
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput,
        strip=False,
        required=False,
    )

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("phone_number", "name", "email")

    def set_password_and_save(self, user, password_field_name="password1", commit=True):  # noqa: S107
        password = self.cleaned_data.get(password_field_name)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Admin form for editing users (password stays read-only)."""

    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password. Use the button below to set or reset it."
        ),
    )

    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_permissions = self.fields.get("user_permissions")
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related("content_type")


@admin.register(User)
class UserAdmin(AuditFieldsAdminMixin, BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    ordering = ("phone_number",)
    list_display = (
        "phone_number",
        "name",
        "email",
        "is_verified",
        "totp_enabled",
        "is_superuser",
        "is_active",
    )
    search_fields = ("phone_number", "name", "email")
    list_filter = ("is_verified", "is_superuser", "is_staff", "is_active", "totp_enabled")

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("name", "email")}),
        (
            "Authenticator app (TOTP)",
            {"fields": ("is_verified", "verified_by", "totp_enabled", "totp_secret", "totp_qr")},
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
        ("Account", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "name", "email"),
            },
        ),
        ("Password", {"fields": ("password1", "password2")}),
    )

    readonly_fields = ("date_joined", "last_login", "totp_qr")

    actions = ("generate_totp_qr",)

    def save_model(self, request, obj, form, change):
        """Auto-assign audit fields on creation.

        New accounts are verified and enrolled the moment they are created: the
        creator/verifier is the acting (logged-in) staff user, is_verified is
        True, and a fresh, activated TOTP secret is generated. On edits, keep
        verified_by consistent when an account is (re)marked verified.
        """
        if not change:
            obj.created_by = request.user
            obj.verified_by = request.user
            obj.is_verified = True
            if not obj.totp_secret:
                obj.generate_totp_secret()
            obj.totp_enabled = True
        elif obj.is_verified and obj.verified_by_id is None:
            obj.verified_by = request.user
        super().save_model(request, obj, form, change)

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
            return format_html("<p style='color:#c62828;'>Could not render the QR code.</p>")
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
class AdminProfileAdmin(SoftDeleteModelAdmin):
    list_display = ("user", "created_by", "created_at")
    search_fields = ("user__name", "user__phone_number")
    autocomplete_fields = ("user",)
    # Avoid one query per row for the FK/one-to-one columns in list_display.
    list_select_related = ("user", "created_by")

    def has_add_permission(self, request):
        """Only a superuser may promote someone to an application Admin."""
        return request.user.is_superuser


@admin.register(SalesPerson)
class SalesPersonAdmin(SoftDeleteModelAdmin):
    list_display = ("user", "created_by", "created_at")
    search_fields = ("user__name", "user__phone_number", "user__created_by__name")
    autocomplete_fields = ("user",)
    # Avoid one query per row for the FK/one-to-one columns in list_display.
    list_select_related = ("user", "created_by")

    def has_add_permission(self, request):
        """An application Admin (or superuser) may hire a SalesPerson."""
        return request.user.is_superuser or request.user.is_admin_user


# Hide the default Django auth groups config in favour of our role groups
# (we still keep groups usable, but the default model admin for Group is off).
admin.site.unregister(Group)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Read-only visibility into active web (sales-admin) browser sessions.

    Django doesn't register this by default. ``session_data`` is opaque
    (base64-encoded, not the raw ``_auth_user_id`` dict), so this is for
    seeing which sessions exist and when they expire -- not for editing.
    Deleting a row here force-logs-out that session, the same effect as
    ``POST /api/sales-admin/auth/logout``.
    """

    list_display = ("session_key", "expire_date")
    ordering = ("-expire_date",)
    readonly_fields = ("session_key", "session_data", "expire_date")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
