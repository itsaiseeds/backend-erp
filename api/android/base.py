"""Base view for the sales-person Android app.

Android views authenticate via an expiring DRF bearer token
(``ExpiringTokenAuthentication`` — 24h TTL), which the client persists across
requests, and require a ``SalesPerson`` profile.
"""

from __future__ import annotations

from ..authentication import ExpiringTokenAuthentication
from ..permissions import IsSalesPerson
from ..views import BaseApiView


class AndroidBaseView(BaseApiView):
    """Base for every Android app endpoint.

    - Authenticates via a bearer token (browser sessions don't exist on mobile);
      the token is rejected once it is older than ``TOKEN_TTL_HOURS``.
    - Requires an authenticated user with a ``SalesPerson`` profile.
    - Set ``superuser_required = True`` to further restrict (rare on mobile).
    """

    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsSalesPerson]
