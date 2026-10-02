"""Godown manager management endpoint: ``GET``/``POST`` ``/api/sales-admin/godown-managers``.

Only an application Admin may hire a godown manager (``admin_required`` on
``AdminApiView``, the session-only web base), mirroring ``SalesPeopleView``
minus the city: a godown manager carries no location.

Soft-deleted godown managers are never returned.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import GodownManager, User
from authentication.UserOperations import (
    GodownManagerPayloadSerializer,
    create_verified_user,
    godown_manager_payload,
)
from authentication.validators import validate_phone_number


class CreateGodownManagerSerializer(serializers.Serializer):
    """Request validation for creating a new ``GodownManager``."""

    name = serializers.CharField(
        max_length=255,
        error_messages={"blank": "Name is required.", "required": "Name is required."},
    )
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10,
        validators=[validate_phone_number],
        error_messages={
            "blank": "Phone number is required.",
            "required": "Phone number is required.",
        },
    )

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value


class GodownManagersView(AdminApiView):
    """List (GET) or create (POST) godown managers (app admin only)."""

    serializer_class = CreateGodownManagerSerializer
    admin_required = True

    @extend_schema(
        summary="List godown managers",
        responses={200: GodownManagerPayloadSerializer(many=True)},
    )
    def get(self, request):
        managers = GodownManager.objects.select_related("user", "created_by").order_by("-id")
        return Response(
            [godown_manager_payload(manager, include_totp=True) for manager in managers]
        )

    @extend_schema(
        summary="Create a godown manager",
        request=CreateGodownManagerSerializer,
        responses={201: GodownManagerPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateGodownManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = create_verified_user(data, actor=request.user)
            manager = GodownManager.objects.create(user=user, created_by=request.user)

        return Response(
            godown_manager_payload(manager, include_totp=True),
            status=status.HTTP_201_CREATED,
        )
