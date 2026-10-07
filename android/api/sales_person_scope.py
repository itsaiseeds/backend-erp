"""Booking on behalf of a sales person: the admin-only ``created_by`` scope.

An admin who also has app access may act for a sales person. The endpoints that
support it take an optional user id (``created_by`` in a body, ``sales_person_id``
in a query string) and resolve it here, so the rules live in one place:

* no id -> the caller, exactly as before;
* an id from a caller who is not an admin -> 403;
* an id that is not an active user with a live ``SalesPerson`` profile -> 400.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from authentication.models import SalesPerson

User = get_user_model()


def live_sales_person_users():
    """Active users holding a live ``SalesPerson`` profile, ordered by name."""
    live_user_ids = SalesPerson.objects.values("user_id")
    return User.objects.filter(is_active=True, id__in=live_user_ids).order_by("name", "id")


def resolve_sales_person(request: Request, user_id: int | None, field: str = "created_by"):
    """The sales person ``request`` acts for: the caller, or ``user_id`` for an admin."""
    if user_id is None:
        return request.user
    if not request.user.is_admin_user:
        raise PermissionDenied("Only an admin can act on behalf of a sales person.")
    target = live_sales_person_users().filter(id=user_id).first()
    if target is None:
        raise serializers.ValidationError({field: "Not an active sales person."})
    return target


def sales_person_from_query(request: Request):
    """Resolve the optional ``?sales_person_id=`` query param (see module doc)."""
    raw = request.query_params.get("sales_person_id")
    if raw is None or raw == "":
        return request.user
    try:
        user_id = int(raw)
    except ValueError:
        raise serializers.ValidationError({"sales_person_id": "Must be an integer."}) from None
    return resolve_sales_person(request, user_id, field="sales_person_id")
