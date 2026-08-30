"""Salesperson management endpoint: ``GET``/``POST`` ``/api/sales_admin/sales-people``.

An application Admin (or a superuser) may hire a salesperson.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from aggregator.models import City
from api.authentication import ExpiringTokenAuthentication, SessionAuthentication
from api.permissions import IsAdminOrSuperUser
from authentication.models import SalesPerson
from authentication.UserOperations import create_verified_user, salesperson_payload
from authentication.validators import validate_phone_number

User = get_user_model()


class CreateSalesPersonSerializer(serializers.Serializer):
    """Validation for a new ``SalesPerson`` (city only, no address)."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, validators=[validate_phone_number]
    )
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "A user with this contact number already exists."
            )
        return value


class SalesPeopleView(APIView):
    """List (GET) or create (POST) sales people."""

    serializer_class = CreateSalesPersonSerializer
    authentication_classes: list[type] = [ExpiringTokenAuthentication, SessionAuthentication]
    permission_classes: list[type] = [IsAuthenticated, IsAdminOrSuperUser]

    def get(self, request):
        sales_people = (
            SalesPerson.objects.select_related("user", "created_by", "city")
            .order_by("-id")
        )
        return Response([salesperson_payload(person) for person in sales_people])

    def post(self, request):
        serializer = CreateSalesPersonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = create_verified_user(data, actor=request.user)
            salesperson = SalesPerson.objects.create(
                user=user, city=data["city"], created_by=request.user
            )

        return Response(salesperson_payload(salesperson), status=status.HTTP_201_CREATED)
