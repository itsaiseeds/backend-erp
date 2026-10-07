"""Base views for the Android app (sales person, godown manager and lab tester).

Android views authenticate via an expiring DRF bearer token
(``ExpiringTokenAuthentication`` -- 24h TTL), which the client persists across
requests, and require an Android role profile (``SalesPerson``, ``GodownManager``,
``LabTester``, or any of them).

Android never touches sessions: no view in this app may import ``login``/
``logout``, read ``request.session``, or use ``SessionAuthentication`` -- that
is exclusively the web (sales-admin) side's concern (see ``api.admin.AdminApiView``).
"""

from __future__ import annotations

from api.authentication import ExpiringTokenAuthentication
from api.views import BaseApiView


class AndroidTokenView(BaseApiView):
    """Fixes the Android credential scheme; declares no role.

    Authenticates via a bearer token (browser sessions don't exist on mobile);
    the token is rejected once it is older than ``TOKEN_TTL_HOURS``. Concrete
    views use one of the role bases below.
    """

    authentication_classes = [ExpiringTokenAuthentication]


class AndroidBaseView(AndroidTokenView):
    """Base for every sales-person Android endpoint.

    - Requires an authenticated user with a ``SalesPerson`` profile
      (``salesperson_required`` on ``BaseApiView``).
    - Set ``superuser_required = True`` to further restrict (rare on mobile).
    """

    salesperson_required = True


class AndroidGodownBaseView(AndroidTokenView):
    """Base for the godown-manager-only Android endpoints (``godown/...``)."""

    godown_manager_required = True


class AndroidLabTesterBaseView(AndroidTokenView):
    """Base for the lab-tester-only Android endpoints (``lab/...``)."""

    lab_tester_required = True


class AndroidSharedView(AndroidTokenView):
    """Base for Android endpoints open to any role (look-ups, reauthenticate, notifications)."""

    android_role_required = True
