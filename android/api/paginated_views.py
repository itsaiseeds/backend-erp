"""Sales-person Android app base for a paginated date-range ``GET`` list view."""

from __future__ import annotations

from common.views.paginated_date_range import _PaginatedDateRangeListMixin

from .base import AndroidBaseView


class AndroidPaginatedDateRangeListView(_PaginatedDateRangeListMixin, AndroidBaseView):
    """Android app ``GET`` list view, paginated + date-range filtered.

    Inherits ``salesperson_required = True`` from ``AndroidBaseView``. See
    ``common.views.paginated_date_range`` for the query contract and the
    subclass hooks (``get_queryset``, ``serialize_page``, ``date_field``).
    """
