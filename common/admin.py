"""Reusable Django admin helpers for the project's base models.

``AuditFieldsAdminMixin`` renders the timestamp/soft-delete columns that our
abstract bases add (``created_at``, ``updated_at``, ``is_deleted``,
``deleted_at``, ``deleted_by``) grouped in an "Audit" section on every change
form. ``created_at``/``updated_at`` stay read-only (they're ``auto_now_add``/
``auto_now``, so typing into them would do nothing anyway); ``is_deleted``,
``deleted_at`` and ``deleted_by`` are editable, so a Django admin user can
correct or override the soft-delete state directly -- Django's own
``change_<model>`` permission is what gates who may do that, the same as any
other field. It also hides ``created_by`` from every create/edit form: any
model with a ``CreatedByModel`` column has it set automatically to
``request.user`` on creation and never shows it in the UI.
``SoftDeleteModelAdmin`` builds on ``AuditFieldsAdminMixin`` and makes the
admin's **delete action** go through ``SoftDeletedModel.delete(deleted_by=
request.user)`` instead of hard-deleting (or exploding with
``PermissionDenied``); editing the audit fields directly on the change form is
a separate, unchecked path -- see above.
"""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

AUDIT_FIELDS = ("created_at", "updated_at", "is_deleted", "deleted_at", "deleted_by")
# The subset of AUDIT_FIELDS that stays read-only. is_deleted/deleted_at/
# deleted_by are deliberately left out -- editable in the Django admin only,
# per AuditFieldsAdminMixin's module docstring.
READONLY_AUDIT_FIELDS = ("created_at", "updated_at")


class AuditFieldsAdminMixin:
    """Append the base-model audit fields to the change form, and auto-fill
    ``created_by`` (when the model has one) with the acting user.

    ``created_by`` is hidden from the add (creation) form, but shown as a
    read-only field on the change (view/edit) form. ``is_deleted``/
    ``deleted_at``/``deleted_by`` are grouped alongside the read-only
    ``created_at``/``updated_at`` in the same "Audit" section, but are
    themselves editable -- see the module docstring.
    """

    audit_fields = AUDIT_FIELDS
    readonly_audit_fields = READONLY_AUDIT_FIELDS

    def get_model_audit_fields(self):
        """Return the audit fields that actually exist on this model."""
        model_fields = {f.name for f in self.model._meta.get_fields()}
        return tuple(name for name in self.audit_fields if name in model_fields)

    def get_model_readonly_audit_fields(self):
        """Return the audit fields that stay read-only on this model."""
        model_fields = {f.name for f in self.model._meta.get_fields()}
        return tuple(name for name in self.readonly_audit_fields if name in model_fields)

    def get_model_created_by_field(self):
        """Return ``("created_by",)`` when the model tracks its creator."""
        if hasattr(self.model, "created_by"):
            return ("created_by",)
        return ()

    def get_fieldsets(self, request, obj=None):
        fieldsets = self._strip_created_by(super().get_fieldsets(request, obj))
        created_by = self.get_model_created_by_field()
        audit = self.get_model_audit_fields()
        if created_by and obj is not None:
            audit = (*created_by, *audit)
        if audit:
            fieldsets = (*fieldsets, ("Audit", {"fields": audit}))
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        return (
            *self.readonly_fields,
            *self.get_model_created_by_field(),
            *self.get_model_readonly_audit_fields(),
        )

    def save_model(self, request, obj, form, change):
        """Record the acting user as ``created_by`` on new records."""
        if not change and hasattr(obj, "created_by_id") and obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def _strip_created_by(self, fieldsets):
        """Drop ``created_by`` from the fieldsets, whatever the admin declared."""
        cleaned = []
        for name, options in fieldsets:
            fields = tuple(field for field in options.get("fields", ()) if field != "created_by")
            if fields:
                cleaned.append((name, {**options, "fields": fields}))
        return tuple(cleaned)


class SoftDeleteModelAdmin(AuditFieldsAdminMixin, admin.ModelAdmin):
    """ModelAdmin for ``SoftDeletedModel`` models.

    Deletions pass the current user as ``deleted_by`` (the soft-delete
    implementation requires it) and surface ``PermissionDenied`` -- or a
    ``ValidationError`` from a model that refuses deletion in its current state
    -- as an admin message instead of a 500. ``created_at``/``updated_at`` are
    read-only; ``is_deleted``/``deleted_at``/``deleted_by`` are editable
    directly on the change form (see ``AuditFieldsAdminMixin``).
    """

    def get_deleted_objects(self, objs, request):
        # Soft deletion never cascades to related rows nor touches the rows
        # they reference, so the standard "protected / needs-permission"
        # analysis is irrelevant (and would wrongly block the delete flow via
        # PROTECT-ed relations). Returning empty keeps the default
        # ``delete_selected`` action and the object delete view usable.
        return [], {}, set(), {}

    def delete_model(self, request, obj):
        try:
            obj.delete(deleted_by=request.user)
        except PermissionDenied as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        except ValidationError as exc:
            self.message_user(request, " ".join(exc.messages), level=messages.ERROR)

    def delete_queryset(self, request, queryset):
        skipped = 0
        for obj in queryset:
            try:
                obj.delete(deleted_by=request.user)
            except (PermissionDenied, ValidationError):
                skipped += 1
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} item(s) that cannot be deleted.",
                level=messages.ERROR,
            )
