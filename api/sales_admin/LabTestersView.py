"""Lab tester management endpoint: ``GET``/``POST`` ``/api/sales-admin/lab-testers``.

Only an application Admin may hire a lab tester (``admin_required`` on
``AdminApiView``, the session-only web base), mirroring ``GodownManagersView``:
a lab tester carries no location.

Soft-deleted lab testers are never returned.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import LabTester, User
from authentication.UserOperations import (
    LabTesterPayloadSerializer,
    can_see_totp,
    create_verified_user,
    lab_tester_payload,
)
from authentication.validators import validate_phone_number


class CreateLabTesterSerializer(serializers.Serializer):
    """Request validation for creating a new ``LabTester``."""

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


class LabTestersView(AdminApiView):
    """List (GET) or create (POST) lab testers (app admin only)."""

    serializer_class = CreateLabTesterSerializer
    admin_required = True

    @extend_schema(
        summary="List lab testers",
        responses={200: LabTesterPayloadSerializer(many=True)},
    )
    def get(self, request):
        testers = LabTester.objects.select_related("user", "created_by").order_by("-id")
        return Response(
            [
                lab_tester_payload(
                    tester, include_totp=can_see_totp(request.user, tester.user)
                )
                for tester in testers
            ]
        )

    @extend_schema(
        summary="Create a lab tester",
        request=CreateLabTesterSerializer,
        responses={201: LabTesterPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateLabTesterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = create_verified_user(data, actor=request.user)
            tester = LabTester.objects.create(user=user, created_by=request.user)

        return Response(
            lab_tester_payload(tester, include_totp=True),
            status=status.HTTP_201_CREATED,
        )
