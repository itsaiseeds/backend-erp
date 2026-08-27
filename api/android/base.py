"""Base view for the sales-person Android app.

Android views authenticate via a DRF bearer token (``TokenAuthentication``),
which the client persists across requests, and require a ``SalesPerson``
profile.
"""

from __future__ import annotations

from rest_framework.authentication import TokenAuthentication

from ..permissions import IsSalesPerson
from ..views import BaseApiView


class AndroidBaseView(BaseApiView):
    """Base for every Android app endpoint.

    - Authenticates via a bearer token (browser sessions don't exist on mobile).
    - Requires an authenticated user with a ``SalesPerson`` profile.
    - Set ``superuser_required = True`` to further restrict (rare on mobile).
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsSalesPerson]
