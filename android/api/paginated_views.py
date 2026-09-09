"""Sales-person Android app base for a paginated date-range ``GET`` list view."""

from __future__ import annotations

from common.views.paginated_date_range import _PaginatedDateRangeListMixin

from .base import AndroidBaseView


class AndroidPaginatedDateRangeListView(_PaginatedDateRangeListMixin, AndroidBaseView):
    """Android app ``GET`` list view, paginated + date-range filtered.

    Inherits ``salesperson_required = True`` from ``AndroidBaseView``. See
    ``common.views.paginated_date_range`` for the query contract and the
    subclass hooks (``get_queryset``, ``serialize_page``, ``date_field``,
    ``enforce_date_range_filters``).

    ``enforce_date_range_filters`` defaults to ``True``: a request with no
    ``start_date_time`` / ``end_date_time`` is a ``400``. Set it to ``False``
    on a subclass to serve the unfiltered list when both bounds are omitted.
    """
