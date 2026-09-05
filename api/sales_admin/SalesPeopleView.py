"""Sales person management endpoint: ``GET``/``POST`` ``/api/sales-admin/sales-people``.

Only an application Admin may hire a sales person (``admin_required`` on
``AdminApiView``, the session-only web base). A sales person cannot create
another sales person or an admin, and a superuser only creates admins.

Soft-deleted sales people are never returned.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import City
from api.admin import AdminApiView
from authentication.models import SalesPerson, User
from authentication.UserOperations import (
    SalesPersonPayloadSerializer,
    create_verified_user,
    salesperson_payload,
)
from authentication.validators import validate_phone_number


class CreateSalesPersonSerializer(serializers.Serializer):
    """Request validation for creating a new ``SalesPerson`` (city only)."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=10, validators=[validate_phone_number])
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value


class SalesPeopleView(AdminApiView):
    """List (GET) or create (POST) sales people (app admin only)."""

    serializer_class = CreateSalesPersonSerializer
    admin_required = True

    @extend_schema(
        summary="List sales people",
        responses={200: SalesPersonPayloadSerializer(many=True)},
    )
    def get(self, request):
        sales_people = SalesPerson.objects.select_related("user", "city", "created_by").order_by(
            "-id"
        )
        return Response(
            [salesperson_payload(person, include_totp=True) for person in sales_people]
        )

    @extend_schema(
        summary="Create a sales person",
        request=CreateSalesPersonSerializer,
        responses={201: SalesPersonPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateSalesPersonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = create_verified_user(data, actor=request.user)
            salesperson = SalesPerson.objects.create(
                user=user, city=data["city"], created_by=request.user
            )

        return Response(
            salesperson_payload(salesperson, include_totp=True),
            status=status.HTTP_201_CREATED,
        )
