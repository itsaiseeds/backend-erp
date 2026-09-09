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
    subclass hooks (``get_queryset``, ``serialize_page``, ``date_field``,
    ``enforce_date_range_filters``).

    ``enforce_date_range_filters`` defaults to ``True``: a request with no
    ``start_date_time`` / ``end_date_time`` is a ``400``. Set it to ``False``
    on a subclass to serve the unfiltered list when both bounds are omitted.
    """

    admin_required = True
