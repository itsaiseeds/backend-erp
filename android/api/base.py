"""Base view for the sales-person Android app.

Android views authenticate via an expiring DRF bearer token
(``ExpiringTokenAuthentication`` -- 24h TTL), which the client persists across
requests, and require a ``SalesPerson`` profile.

Android never touches sessions: no view in this app may import ``login``/
``logout``, read ``request.session``, or use ``SessionAuthentication`` -- that
is exclusively the web (sales-admin) side's concern (see ``api.admin.AdminApiView``).
"""

from __future__ import annotations

from api.authentication import ExpiringTokenAuthentication
from api.views import BaseApiView


class AndroidBaseView(BaseApiView):
    """Base for every Android app endpoint.

    - Authenticates via a bearer token (browser sessions don't exist on mobile);
      the token is rejected once it is older than ``TOKEN_TTL_HOURS``.
    - Requires an authenticated user with a ``SalesPerson`` profile
      (``salesperson_required`` on ``BaseApiView``).
    - Set ``superuser_required = True`` to further restrict (rare on mobile).
    """

    authentication_classes = [ExpiringTokenAuthentication]
    salesperson_required = True
