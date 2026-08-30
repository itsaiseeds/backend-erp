"""Salesperson management endpoint: ``GET``/``POST`` ``/api/sales_admin/sales-people``.

An application Admin (or a superuser) may hire a salesperson.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.admin import AdminApiView
from api.permissions import IsAdminOrSuperUser
from authentication.models import SalesPerson

from .serializers import (
    CreateSalesPersonSerializer,
    create_verified_user,
    salesperson_payload,
)


class SalesPeopleView(AdminApiView):
    """List (GET) or create (POST) sales people.

    ``authentication_classes`` tries the bearer Token issued by the auth (OTP
    verify) flow first, then falls back to the session cookie for the web app.
    Token-first ordering matters: the OTP flow also opens a browser session, so
    a token request that also carries the session cookie must be authenticated
    as the token (and skip the session's CSRF check), not rejected.
    """

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = CreateSalesPersonSerializer

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrSuperUser()]

    def get(self, request):
        sales_people = (
            SalesPerson.all_objects.select_related(
                "user", "city", "created_by", "deleted_by"
            )
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
