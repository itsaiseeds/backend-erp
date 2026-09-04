"""Admin management endpoint: ``GET``/``POST`` ``/api/sales_admin/admins``.

Only a Django superuser may create an application admin (enforced via the
``IsSuperUser`` permission, mirroring how ``VerifyOTPView`` declares its own
``authentication_classes`` / ``permission_classes``). Creating an admin also
creates a fallback ``SalesPerson`` profile for the same user (same contact
number) so the account can still operate from the salesperson app if needed.

Soft-deleted admins are never returned.
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from aggregator.models import City
from api.authentication import ExpiringTokenAuthentication, SessionAuthentication
from api.permissions import IsSuperUser
from authentication.models import Admin, SalesPerson, User
from authentication.UserOperations import (
    AdminPayloadSerializer,
    admin_payload,
    create_verified_user,
)
from authentication.validators import validate_phone_number

logger = logging.getLogger(__name__)


class CreateAdminSerializer(serializers.Serializer):
    """Request validation for creating a new application ``Admin``.

    ``city`` is required because creating an admin also creates the fallback
    ``SalesPerson`` profile, which needs a city.
    """

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=10, validators=[validate_phone_number])
    can_update_stock_count = serializers.BooleanField(default=False)
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        help_text="City for the fallback salesperson profile created with this admin.",
    )

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value


class AdminsView(APIView):
    """List (GET) or create (POST) application admins (superuser only)."""

    serializer_class = CreateAdminSerializer

    # Refer to api/sales_admin/VerifyOTPView.py for how a view declares its own
    # authentication / permission classes instead of the global defaults.
    authentication_classes: list[type] = [ExpiringTokenAuthentication, SessionAuthentication]
    permission_classes: list[type] = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        summary="List application admins",
        responses={200: AdminPayloadSerializer(many=True)},
    )
    def get(self, request):
        admins = Admin.objects.select_related("user", "created_by").order_by("-id")
        return Response([admin_payload(admin) for admin in admins])

    @extend_schema(
        summary="Create an application admin (and a fallback sales person)",
        request=CreateAdminSerializer,
        responses={201: AdminPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = create_verified_user(data, actor=request.user)
            admin = Admin.objects.create(
                user=user,
                can_update_stock_count=data["can_update_stock_count"],
                created_by=request.user,
            )
            # Fallback salesperson so the account can always use the sales app.
            SalesPerson.objects.create(user=user, city=data["city"], created_by=request.user)

        return Response(
            admin_payload(admin, include_totp=True),
            status=status.HTTP_201_CREATED,
        )
