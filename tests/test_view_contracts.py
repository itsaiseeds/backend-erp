"""The single owner of the API's authentication and permission contract.

Every API endpoint inherits *all* of its credential and role gating from one of
two bases -- :class:`api.admin.AdminApiView` (session cookie, sales-admin web)
or :class:`android.api.base.AndroidBaseView` (bearer token, Android app) --
which in turn delegate to :class:`api.views.BaseApiView`'s flags. A concrete
view never re-implements that logic; it only *declares* flags.

So the gating is proven exactly once, here, in three layers:

1. :class:`BaseApiViewFlagTest` -- the flags map to the right permission
   classes (pure unit test, no database, no HTTP).
2. :class:`ViewContractRegistryTest` -- every routed view declares the
   contract it is supposed to declare, checked against an explicit table.
   A new view, or a changed flag, fails here until the table is updated.
3. :class:`SessionAuthContractTest` / :class:`TokenAuthContractTest` -- one
   real HTTP round trip per credential scheme and role flag, proving the
   declared flags actually produce 401/403/200 through the live stack.

Layers 2 and 3 together replace the per-endpoint ``test_anonymous_..._rejected``
/ ``test_non_admin_..._rejected`` tests that used to be copy-pasted into every
endpoint module: the registry catches a mis-wired view (including views nobody
wrote a test for), and the contract tests prove the wiring has teeth. **Do not
re-add per-endpoint authentication tests** -- see ``docs/testing.md``.

tests/test_view_contracts.py
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.urls import get_resolver
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from aggregator.models import City, Country, State
from android.api.base import AndroidBaseView
from api.admin import AdminApiView
from api.authentication import ExpiringTokenAuthentication, SessionAuthentication
from api.permissions import IsAdminUser, IsSalesPerson, IsSuperUser
from api.views import BaseApiView
from authentication.models import Admin, SalesPerson
from tests.android.common import AndroidApiTestCase
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

# Contract shorthand used by the registry table below:
#   "<scheme>:<role>" where scheme is the credential the base class fixes
#   (session = web/sales-admin, token = Android) and role is the strictest
#   flag the view sets (auth = authenticated only, no role requirement).
SESSION_AUTH = "session:auth"
SESSION_ADMIN = "session:admin"
SESSION_SUPERUSER = "session:superuser"
TOKEN_AUTH = "token:auth"
TOKEN_SALESPERSON = "token:salesperson"

_SCHEME_BASES = {"session": AdminApiView, "token": AndroidBaseView}
_SCHEME_AUTHENTICATORS = {
    "session": SessionAuthentication,
    "token": ExpiringTokenAuthentication,
}
_ROLE_FLAGS = {
    "auth": {"admin_required": False, "superuser_required": False, "salesperson_required": False},
    "admin": {"admin_required": True, "superuser_required": False, "salesperson_required": False},
    "superuser": {
        "admin_required": False,
        "superuser_required": True,
        "salesperson_required": False,
    },
    "salesperson": {
        "admin_required": False,
        "superuser_required": False,
        "salesperson_required": True,
    },
}

# Every routed endpoint that goes through BaseApiView, and the contract it must
# declare. Adding a view without adding it here is a test failure -- that is the
# point: this table is the review surface for "who may call what".
EXPECTED_CONTRACTS = {
    # -- Android app (token-only) --------------------------------------------
    # Logout deliberately does NOT require a SalesPerson profile: a token whose
    # profile was removed must still be revocable.
    "android/api/v1/auth/logout": ("LogoutView", TOKEN_AUTH),
    "android/api/v1/auth/reauthenticate": ("ReauthenticateView", TOKEN_SALESPERSON),
    "android/api/v1/client/<public_id>": ("GetClientView", TOKEN_SALESPERSON),
    "android/api/v1/create-client": ("CreateClientView", TOKEN_SALESPERSON),
    "android/api/v1/get-clients": ("GetClientsView", TOKEN_SALESPERSON),
    "android/api/v1/update-client": ("UpdateClientView", TOKEN_SALESPERSON),
    "android/api/v1/utilities/cities": ("CitiesView", TOKEN_SALESPERSON),
    "android/api/v1/utilities/countries": ("CountriesView", TOKEN_SALESPERSON),
    "android/api/v1/utilities/states": ("StatesView", TOKEN_SALESPERSON),
    # -- Sales-admin website (session-only) ----------------------------------
    "api/sales-admin/admins": ("AdminsView", SESSION_SUPERUSER),
    "api/sales-admin/admins/<int:id>": ("UpdateAdminView", SESSION_SUPERUSER),
    "api/sales-admin/auth/logout": ("LogoutView", SESSION_AUTH),
    "api/sales-admin/check-todays-inventory": ("CheckTodaysInventoryView", SESSION_ADMIN),
    "api/sales-admin/client/<str:public_id>": ("GetClientView", SESSION_ADMIN),
    "api/sales-admin/crops": ("CropsView", SESSION_ADMIN),
    "api/sales-admin/crops/<int:id>": ("UpdateCropView", SESSION_ADMIN),
    "api/sales-admin/get-clients/": ("GetClientsView", SESSION_ADMIN),
    "api/sales-admin/get-stock/<str:public_id>": ("StockView", SESSION_ADMIN),
    "api/sales-admin/loose-stock": ("LooseStockView", SESSION_ADMIN),
    "api/sales-admin/product-packagings": ("ProductPackagingsView", SESSION_ADMIN),
    "api/sales-admin/product-packagings/<str:public_id>": (
        "UpdateProductPackagingView",
        SESSION_ADMIN,
    ),
    "api/sales-admin/products": ("ProductsView", SESSION_ADMIN),
    "api/sales-admin/products/<str:public_id>": ("UpdateProductView", SESSION_ADMIN),
    "api/sales-admin/sales-people": ("SalesPeopleView", SESSION_ADMIN),
    "api/sales-admin/sales-people/<int:id>": ("UpdateSalesPersonView", SESSION_ADMIN),
    "api/sales-admin/update-client/": ("UpdateClientView", SESSION_ADMIN),
    "api/sales-admin/update-loose-stock": ("UpdateLooseStockView", SESSION_ADMIN),
    "api/sales-admin/update-todays-inventory": ("UpdateTodaysInventoryView", SESSION_ADMIN),
    "api/sales-admin/verify-client/": ("VerifyClientView", SESSION_ADMIN),
    "api/test-sentry/": ("TestSentryView", SESSION_SUPERUSER),
    "api/utilities/cities": ("CitiesView", SESSION_ADMIN),
    "api/utilities/countries": ("CountriesView", SESSION_ADMIN),
    "api/utilities/reauthenticate": ("ReauthenticateView", SESSION_AUTH),
    "api/utilities/states": ("StatesView", SESSION_ADMIN),
}

# The only project endpoints that may be reached without credentials: both mint
# them. Anything else bypassing BaseApiView is a security regression.
PRE_AUTH_VIEWS = {
    "android/api/v1/auth/login": "android.api.v1.LoginView.LoginView",
    "api/sales-admin/auth/otp/verify": "api.sales_admin.VerifyOTPView.VerifyOTPView",
}


def _routed_api_views() -> dict[str, type[APIView]]:
    """Map every routed URL pattern to the :class:`APIView` subclass serving it."""
    views: dict[str, type[APIView]] = {}

    def walk(resolver, prefix: str = "") -> None:
        for pattern in resolver.url_patterns:
            path = prefix + str(pattern.pattern)
            if hasattr(pattern, "url_patterns"):
                walk(pattern, path)
                continue
            view_class = getattr(pattern.callback, "view_class", None)
            if view_class is not None and issubclass(view_class, APIView):
                views[path] = view_class

    walk(get_resolver())
    return views


class BaseApiViewFlagTest(SimpleTestCase):
    """The flags on ``BaseApiView`` map to the right DRF permission classes.

    tests/test_view_contracts.py::BaseApiViewFlagTest
    """

    def test_each_flag_combination_yields_the_expected_permissions(self):
        """tests/test_view_contracts.py::BaseApiViewFlagTest::test_each_flag_combination_yields_the_expected_permissions"""
        cases = [
            ({}, [IsAuthenticated]),
            ({"auth_required": False}, []),
            ({"admin_required": True}, [IsAuthenticated, IsAdminUser]),
            ({"superuser_required": True}, [IsAuthenticated, IsSuperUser]),
            ({"salesperson_required": True}, [IsAuthenticated, IsSalesPerson]),
            (
                {"admin_required": True, "superuser_required": True},
                [IsAuthenticated, IsAdminUser, IsSuperUser],
            ),
        ]
        for flags, expected in cases:
            with self.subTest(flags=flags):
                view = type("_View", (BaseApiView,), dict(flags))()
                self.assertEqual([type(p) for p in view.get_permissions()], expected)

    def test_the_two_concrete_bases_fix_one_credential_scheme_each(self):
        """``AdminApiView`` is session-only and ``AndroidBaseView`` token-only.

        tests/test_view_contracts.py::BaseApiViewFlagTest::test_the_two_concrete_bases_fix_one_credential_scheme_each
        """
        self.assertEqual(AdminApiView.authentication_classes, [SessionAuthentication])
        self.assertEqual(AndroidBaseView.authentication_classes, [ExpiringTokenAuthentication])
        # The Android base additionally pins the SalesPerson requirement, so an
        # Android view only opts *out* of it deliberately (e.g. logout).
        self.assertTrue(AndroidBaseView.salesperson_required)
        self.assertFalse(AdminApiView.salesperson_required)


class ViewContractRegistryTest(SimpleTestCase):
    """Every routed view declares exactly the contract it is supposed to.

    tests/test_view_contracts.py::ViewContractRegistryTest
    """

    def test_the_routed_view_set_matches_the_expected_table(self):
        """No endpoint is added, removed or re-pathed without updating the table.

        tests/test_view_contracts.py::ViewContractRegistryTest::test_the_routed_view_set_matches_the_expected_table
        """
        routed = {
            path
            for path, view in _routed_api_views().items()
            if issubclass(view, BaseApiView)
        }
        self.assertEqual(routed, set(EXPECTED_CONTRACTS))

    def test_every_routed_view_declares_the_expected_contract(self):
        """tests/test_view_contracts.py::ViewContractRegistryTest::test_every_routed_view_declares_the_expected_contract"""
        routed = _routed_api_views()
        for path, (view_name, contract) in EXPECTED_CONTRACTS.items():
            with self.subTest(path=path):
                view = routed[path]
                scheme, role = contract.split(":")
                self.assertEqual(view.__name__, view_name)
                self.assertTrue(
                    issubclass(view, _SCHEME_BASES[scheme]),
                    f"{view.__name__} must inherit {_SCHEME_BASES[scheme].__name__}",
                )
                self.assertEqual(
                    view.authentication_classes, [_SCHEME_AUTHENTICATORS[scheme]]
                )
                self.assertTrue(view.auth_required)
                for flag, expected in _ROLE_FLAGS[role].items():
                    self.assertEqual(getattr(view, flag), expected, flag)

    def test_no_view_hand_rolls_permission_classes(self):
        """``get_permissions`` is overridden, so ``permission_classes`` is dead code.

        A view setting it would look gated while being wide open, so catch it here
        rather than hoping an endpoint test notices.

        tests/test_view_contracts.py::ViewContractRegistryTest::test_no_view_hand_rolls_permission_classes
        """
        for path, view in _routed_api_views().items():
            if not issubclass(view, BaseApiView):
                continue
            with self.subTest(path=path):
                self.assertIs(
                    view.permission_classes,
                    APIView.permission_classes,
                    f"{view.__name__} sets permission_classes; express the rule as a flag",
                )

    def test_only_the_login_endpoints_bypass_the_base_view(self):
        """tests/test_view_contracts.py::ViewContractRegistryTest::test_only_the_login_endpoints_bypass_the_base_view"""
        bypassing = {
            path: f"{view.__module__}.{view.__name__}"
            for path, view in _routed_api_views().items()
            if not issubclass(view, BaseApiView)
            # Third-party endpoints (the drf-spectacular schema/docs views) are
            # gated by SPECTACULAR_SETTINGS, not by our flags.
            and view.__module__.split(".")[0] in {"api", "android"}
        }
        self.assertEqual(bypassing, PRE_AUTH_VIEWS)


class SessionAuthContractTest(WebApiTestCase):
    """The session (sales-admin) contract, proven over real HTTP once per role.

    Representative endpoints stand in for every view sharing their flags --
    which the registry test above pins exhaustively.

    tests/test_view_contracts.py::SessionAuthContractTest
    """

    AUTH_ONLY_URL = "/api/utilities/reauthenticate"
    ADMIN_URL = "/api/utilities/countries"
    SUPERUSER_URL = "/api/sales-admin/admins"

    @classmethod
    def setUpTestData(cls):
        """One user per role: superuser, app admin, salesperson and plain."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
        state = State.objects.create(
            name="Maharashtra", code="MH", country=country, created_by=cls.superuser
        )
        cls.city = City.objects.create(name="Pune", state=state, created_by=cls.superuser)

        cls.admin = User.objects.create_user(
            phone_number="7777777777",
            name="app admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.admin, can_update_stock_count=True, created_by=cls.superuser
        )
        cls.plain = User.objects.create_user(
            phone_number="6666666666",
            name="plain user",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="5555555555",
                name="salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=cls.city,
            created_by=cls.superuser,
        )

    def test_anonymous_callers_get_401_on_every_role_level(self):
        """tests/test_view_contracts.py::SessionAuthContractTest::test_anonymous_callers_get_401_on_every_role_level"""
        for url in (self.AUTH_ONLY_URL, self.ADMIN_URL, self.SUPERUSER_URL):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)

    def test_auth_only_endpoints_accept_any_logged_in_user(self):
        """``auth_required`` alone imposes no role at all.

        tests/test_view_contracts.py::SessionAuthContractTest::test_auth_only_endpoints_accept_any_logged_in_user
        """
        for user in (self.plain, self.salesperson.user, self.admin, self.superuser):
            with self.subTest(user=user.name):
                self.login_as(user)
                self.assertEqual(self.client.get(self.AUTH_ONLY_URL).status_code, 200)

    def test_admin_required_endpoints_need_an_admin_profile(self):
        """A bare superuser has no ``Admin`` profile and is refused, by design.

        tests/test_view_contracts.py::SessionAuthContractTest::test_admin_required_endpoints_need_an_admin_profile
        """
        for user in (self.plain, self.salesperson.user, self.superuser):
            with self.subTest(user=user.name):
                self.login_as(user)
                self.assertEqual(self.client.get(self.ADMIN_URL).status_code, 403)
        self.login_as(self.admin)
        self.assertEqual(self.client.get(self.ADMIN_URL).status_code, 200)

    def test_superuser_required_endpoints_need_a_django_superuser(self):
        """An app ``Admin`` is not enough where ``superuser_required`` is set.

        tests/test_view_contracts.py::SessionAuthContractTest::test_superuser_required_endpoints_need_a_django_superuser
        """
        for user in (self.plain, self.salesperson.user, self.admin):
            with self.subTest(user=user.name):
                self.login_as(user)
                self.assertEqual(self.client.get(self.SUPERUSER_URL).status_code, 403)
        self.login_as(self.superuser)
        self.assertEqual(self.client.get(self.SUPERUSER_URL).status_code, 200)

    def test_a_bearer_token_never_authenticates_the_web_side(self):
        """tests/test_view_contracts.py::SessionAuthContractTest::test_a_bearer_token_never_authenticates_the_web_side"""
        token = Token.objects.create(user=self.superuser)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        for url in (self.AUTH_ONLY_URL, self.ADMIN_URL, self.SUPERUSER_URL):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)


class TokenAuthContractTest(AndroidApiTestCase):
    """The bearer-token (Android) contract, proven over real HTTP once.

    tests/test_view_contracts.py::TokenAuthContractTest
    """

    SALESPERSON_URL = "/android/api/v1/utilities/countries"
    AUTH_ONLY_URL = "/android/api/v1/auth/logout"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
        state = State.objects.create(
            name="Maharashtra", code="MH", country=country, created_by=cls.superuser
        )
        city = City.objects.create(name="Pune", state=state, created_by=cls.superuser)
        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="7777777777",
                name="salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=city,
            created_by=cls.superuser,
        )

    def test_anonymous_callers_get_401(self):
        """tests/test_view_contracts.py::TokenAuthContractTest::test_anonymous_callers_get_401"""
        self.assertEqual(self.client.get(self.SALESPERSON_URL).status_code, 401)
        self.assertEqual(self.client.post(self.AUTH_ONLY_URL).status_code, 401)

    def test_a_token_without_a_salesperson_profile_is_forbidden(self):
        """The superuser has no ``SalesPerson`` profile, so mobile refuses it (403)...

        ...but logout, which drops ``salesperson_required``, still accepts it so
        the token can always be revoked.

        tests/test_view_contracts.py::TokenAuthContractTest::test_a_token_without_a_salesperson_profile_is_forbidden
        """
        self.login_as(self.superuser)
        self.assertEqual(self.client.get(self.SALESPERSON_URL).status_code, 403)
        self.assertEqual(self.client.post(self.AUTH_ONLY_URL).status_code, 204)

    def test_a_salesperson_token_is_accepted(self):
        """tests/test_view_contracts.py::TokenAuthContractTest::test_a_salesperson_token_is_accepted"""
        self.login_as(self.salesperson.user)
        self.assertEqual(self.client.get(self.SALESPERSON_URL).status_code, 200)

    def test_a_browser_session_never_authenticates_the_android_side(self):
        """tests/test_view_contracts.py::TokenAuthContractTest::test_a_browser_session_never_authenticates_the_android_side"""
        self.client.force_login(self.salesperson.user)
        self.assertEqual(self.client.get(self.SALESPERSON_URL).status_code, 401)
        self.assertEqual(self.client.post(self.AUTH_ONLY_URL).status_code, 401)

    def test_an_expired_token_is_rejected_and_deleted(self):
        """The 24h TTL is enforced end to end, not just in the auth class.

        ``tests/test_expiring_token.py`` unit-tests the TTL arithmetic; this
        proves the class is actually wired into the Android stack.

        tests/test_view_contracts.py::TokenAuthContractTest::test_an_expired_token_is_rejected_and_deleted
        """
        token = self.login_as(self.salesperson.user)
        Token.objects.filter(key=token.key).update(created=timezone.now() - timedelta(hours=48))

        self.assertEqual(self.client.get(self.SALESPERSON_URL).status_code, 401)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
