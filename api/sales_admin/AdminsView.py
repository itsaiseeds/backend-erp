
"""Admin management endpoint: ``GET``/``POST`` ``/api/sales_admin/admins``.

Only a Django superuser may create an application admin. Creating an admin also
creates a fallback ``SalesPerson`` profile for the same user (same contact
number) so the account can still operate from the salesperson app if needed.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import Admin, SalesPerson

from .serializers import (
    CreateAdminSerializer,
    admin_payload,
    create_address,
    create_verified_user,
)


class AdminsView(AdminApiView):
    """List (GET) or create (POST) application admins.

    Restricted to superusers. ``authentication_classes`` tries the bearer Token
    issued by the auth (OTP verify) flow first, then falls back to the session
    cookie for the web app. Token-first ordering matters: the OTP flow also
    opens a browser session, so a token request that also carries the session
    cookie must be authenticated as the token (and skip the session's CSRF
    check), not rejected.
    """

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    admin_required = False
    superuser_required = True
    serializer_class = CreateAdminSerializer

    def get(self, request):
        admins = (
            Admin.all_objects.select_related(
                "user",
                "created_by",
                "deleted_by",
                "address__city",
                "address__state",
                "address__pincode",
                "address__country",
            )
            .order_by("-id")
        )
        return Response([admin_payload(admin) for admin in admins])

    def post(self, request):
        serializer = CreateAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = create_verified_user(data, actor=request.user)
            admin = Admin.objects.create(
                user=user,
                can_update_stock_count=data["can_update_stock_count"],
                address=create_address(data.get("address"), actor=request.user),
                created_by=request.user,
            )
            # Fallback salesperson so the account can always use the sales app.
            SalesPerson.objects.create(
                user=user, city=data["city"], created_by=request.user
            )

        return Response(admin_payload(admin), status=status.HTTP_201_CREATED)
