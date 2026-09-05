"""Sales-admin website base for a paginated date-range ``GET`` list view."""

from __future__ import annotations

from common.views.paginated_date_range import _PaginatedDateRangeListMixin

from .admin import AdminApiView


class AdminPaginatedDateRangeListView(_PaginatedDateRangeListMixin, AdminApiView):
    """Admin website ``GET`` list view, paginated + date-range filtered.

    Defaults to ``admin_required = True``; a subclass may set
    ``superuser_required = True`` to tighten, or ``admin_required = False``
    to relax to any authenticated user. See
    ``common.views.paginated_date_range`` for the query contract and the
    subclass hooks (``get_queryset``, ``serialize_page``, ``date_field``).
    """

    admin_required = True
