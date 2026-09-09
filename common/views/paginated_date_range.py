"""Reusable pieces for a paginated ``GET`` list view: an optional
``start_date_time``..``end_date_time`` window, a catalogue of client-selectable
queryset filters, and a catalogue of client-selectable sort orders.

Whether the date window is mandatory is the subclass's call -- see
:attr:`_PaginatedDateRangeListMixin.enforce_date_range_filters`.

Filtering and sorting are opt-in and share one shape: the subclass declares what
it accepts (:attr:`~_PaginatedDateRangeListMixin.queryset_filters` /
:attr:`~_PaginatedDateRangeListMixin.sort_options`) and every response echoes
the catalogue (``available_filters`` / ``available_sorts``) so the frontend can
discover them without a second endpoint.

The query string uses one (or, for ranges, two) parameter(s) per filter, plus a
single ``sort``::

    ?city_id=12,15&created_after=2026-01-01&sort=-created_at&page=2

* a :class:`QuerysetFilter` is one param, ``?<name>=<v1,v2,...>`` -- the comma
  list is OR-ed, then AND-ed with the other filters. ``multi=False`` makes it a
  single free-text term instead (no comma split) -- for substring search.
* a :class:`RangeFilter` is a ``?<name>_after=`` / ``?<name>_before=`` pair
  (inclusive ``>=`` / ``<=``); send either or both. This is how open-ended
  filters -- dates, numbers -- are expressed, since a comma list can't say
  "between".
* a request that names no filter just gets page one.
* ``sort`` is a comma-separated list of declared sort names, each optionally
  ``-``-prefixed for descending; absent, :attr:`default_sort` is used. A ``pk``
  tie-breaker is always appended so pagination is stable.

``page``, ``page_size``, ``start_date_time``, ``end_date_time`` and ``sort`` are
reserved -- no filter param may reuse those names.

Every ``available_filters`` entry carries a ``kind`` (``select``, ``int``,
``text``, ``date``, ``datetime``, ``date_range``, ``datetime_range``, ...) so
the frontend picks the right widget without guessing; a closed-ended filter
also carries ``options`` (``{value, label}`` choices) so a picker needs no
second call. :func:`list_query_parameters` turns a view's ``queryset_filters`` /
``sort_options`` into the drf-spectacular ``parameters`` list for its schema.

Two concrete client bases wrap the mixin defined here:
``api.paginated_views.AdminPaginatedDateRangeListView`` (sales-admin website)
and ``android.api.paginated_views.AndroidPaginatedDateRangeListView`` (android
app). Subclass one of those -- not the mixin -- in a real view.
"""

from __future__ import annotations

import abc
from collections.abc import Callable, Sequence
from typing import Generic, TypeVar

from django.db.models import Model, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

_ModelT = TypeVar("_ModelT", bound=Model)

# ``options`` on a filter: the eligible ``{value, label}`` choices the client
# should offer -- a static list, or a ``(request) -> list`` callable when the
# eligible set depends on who is asking. ``None`` == open-ended.
FilterOptions = Sequence[dict] | Callable[[Request], Sequence[dict]]


class StandardPageNumberPagination(PageNumberPagination):
    """Project default page number pagination.

    Uses ``?page=`` and ``?page_size=`` (capped at ``max_page_size``). The
    envelope is page-number oriented rather than DRF's URL default::

        {
          "total_count": <rows matching the query, across every page>,
          "total_pages": <number of pages at this page_size, always >= 1>,
          "next_page_number": <int or null on the last page>,
          "previous_page_number": <int or null on the first page>,
          "results": [...],
        }
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 30

    def get_paginated_response(self, data) -> Response:
        page = self.page
        return Response(
            {
                "total_count": page.paginator.count,
                "total_pages": page.paginator.num_pages,
                "next_page_number": (
                    page.next_page_number() if page.has_next() else None
                ),
                "previous_page_number": (
                    page.previous_page_number() if page.has_previous() else None
                ),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema: dict) -> dict:
        return {
            "type": "object",
            "required": [
                "total_count",
                "total_pages",
                "next_page_number",
                "previous_page_number",
                "results",
            ],
            "properties": {
                "total_count": {"type": "integer", "example": 37},
                "total_pages": {"type": "integer", "example": 4},
                "next_page_number": {"type": "integer", "nullable": True, "example": 3},
                "previous_page_number": {
                    "type": "integer",
                    "nullable": True,
                    "example": 1,
                },
                "results": schema,
            },
        }


DATE_RANGE_PARAMS = ("start_date_time", "end_date_time")

# Query params the mixin owns; a filter or sort option may not reuse these names.
RESERVED_QUERY_PARAMS = frozenset(
    {"page", "page_size", "sort", *DATE_RANGE_PARAMS}
)


class DateRangeQuerySerializer(serializers.Serializer):
    """Validates the ``start_date_time`` / ``end_date_time`` pair a paginated
    date-range list view accepts as query params."""

    start_date_time = serializers.DateTimeField()
    end_date_time = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["start_date_time"] > attrs["end_date_time"]:
            raise serializers.ValidationError(
                "start_date_time must be less than or equal to end_date_time."
            )
        return attrs


# -- Value parsers ---------------------------------------------------------

# One raw query-param segment -> a clean, typed value. Must raise
# ``serializers.ValidationError`` when the segment is not acceptable.
ValueParser = Callable[[str], object]


def parse_int(raw: str) -> int:
    """Parser for integer-id filters (the common case)."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise serializers.ValidationError(f"'{raw}' is not a valid integer.") from None


def parse_str(raw: str) -> str:
    """Parser for free-text filters; trims and rejects blanks."""
    value = raw.strip()
    if not value:
        raise serializers.ValidationError("Blank values are not allowed.")
    return value


def parse_date(raw: str):
    """Parser for ISO ``YYYY-MM-DD`` date bounds."""
    return serializers.DateField().to_internal_value(raw.strip())


def parse_datetime(raw: str):
    """Parser for ISO 8601 datetime bounds."""
    return serializers.DateTimeField().to_internal_value(raw.strip())


# Which catalogue ``kind`` a bare parser implies, when the filter declares none.
_PARSER_KIND: dict[ValueParser, str] = {
    parse_int: "int",
    parse_str: "text",
    parse_date: "date",
    parse_datetime: "datetime",
}


# -- Filters -----------------------------------------------------------------

# Upper bound on how many comma-separated values one filter param may carry.
MAX_FILTER_VALUES = 100


class ListFilter(abc.ABC):
    """A whitelisted way for the client to narrow a paginated list view.

    Every filter owns one or more query params, applies itself from the request,
    and describes itself for the ``available_filters`` catalogue. The catalogue
    entry always carries a ``kind`` so the frontend can choose a widget without
    a fixed ``options`` list (``date``/``datetime``/``int``/``text`` inputs,
    ``*_range`` two-bound pickers, ``select`` dropdowns, ...).
    """

    name: str
    kind: str
    description: str

    @abc.abstractmethod
    def param_names(self) -> tuple[str, ...]:
        """The query param(s) this filter reads."""

    @abc.abstractmethod
    def apply_from_request(self, queryset: QuerySet, request: Request) -> QuerySet:
        """Parse this filter's params off ``request`` and narrow ``queryset``.

        Only called when :meth:`applies_to` is true. Raises
        ``serializers.ValidationError`` on a bad value.
        """

    @abc.abstractmethod
    def catalogue_entry(self, request: Request) -> dict:
        """This filter's ``available_filters`` entry."""

    @abc.abstractmethod
    def openapi_parameters(self) -> list[OpenApiParameter]:
        """This filter's drf-spectacular query parameter(s)."""

    def applies_to(self, request: Request) -> bool:
        """Whether the request supplied any of this filter's params."""
        return any(name in request.query_params for name in self.param_names())


class QuerysetFilter(ListFilter):
    """A single-param filter: ``?<name>=<v1,v2,...>`` (comma list OR-ed).

    ``name``
        The query param, and -- unless ``lookup`` is given -- the Django lookup
        too, so ``"status_id__in"`` / ``"city_id__in"`` work out of the box.
    ``lookup``
        The ORM lookup the default ``apply`` uses, when it should differ from the
        public param name (``QuerysetFilter("company_name",
        lookup="company_name__icontains", ...)``).
    ``parse``
        Per-value coercion (default :func:`parse_int`; also :func:`parse_str`).
    ``multi``
        ``True`` (default): ``?<name>=a,b`` is split into a value list, OR-ed by
        the default ``apply`` (which uses an ``__in``-style lookup). ``False``:
        the whole param value is one term (no comma split, no length cap) -- for
        free-text search where a comma is data, and the default ``apply`` passes
        the single value straight to ``lookup``.
    ``apply``
        ``(queryset, values) -> queryset`` for anything a bare
        ``.filter(lookup=values)`` can't express (relation spans, ``.distinct()``,
        ``Q`` objects). ``values`` is always a list (length 1 when ``multi`` is
        ``False``).
    ``options``
        Static ``[{"value", "label"}]`` list, or a ``(request) -> list``
        callable -- the eligible choices, echoed on the catalogue entry so a
        picker needs no second call. Presence flips the default ``kind`` to
        ``"select"``.
    ``kind``
        Catalogue widget hint; defaults from ``options`` / ``parse``.
    """

    def __init__(
        self,
        name: str,
        *,
        lookup: str | None = None,
        parse: ValueParser = parse_int,
        multi: bool = True,
        apply: Callable[[QuerySet, list], QuerySet] | None = None,
        description: str = "",
        options: FilterOptions | None = None,
        kind: str | None = None,
    ) -> None:
        self.name = name
        self.lookup = lookup or name
        self.parse = parse
        self.multi = multi
        self._apply = apply
        self.description = description
        self._options = options
        self.kind = kind or (
            "select" if options is not None else _PARSER_KIND.get(parse, "text")
        )

    def param_names(self) -> tuple[str, ...]:
        return (self.name,)

    def clean_values(self, raw: str | None) -> list:
        """Sanitize this filter's query-param string into a value list.

        ``raw`` is the exact ``?<name>=`` string (``None`` when the param is
        absent). With ``multi`` (default) it is split on commas, blank segments
        dropped, each segment run through :attr:`parse`, duplicates collapsed
        (first-seen order kept). With ``multi`` off the whole string is one term
        through :attr:`parse`.
        """
        if raw is None or not raw.strip():
            raise serializers.ValidationError(
                {self.name: "This filter needs at least one value."}
            )
        if not self.multi:
            return [self.parse(raw.strip())]
        segments = [seg for seg in (part.strip() for part in raw.split(",")) if seg]
        if not segments:
            raise serializers.ValidationError({self.name: "No values supplied."})
        if len(segments) > MAX_FILTER_VALUES:
            raise serializers.ValidationError(
                {self.name: f"Too many values (max {MAX_FILTER_VALUES})."}
            )
        cleaned: list = []
        for segment in segments:
            value = self.parse(segment)
            if value not in cleaned:
                cleaned.append(value)
        return cleaned

    def apply(self, queryset: QuerySet, values: list) -> QuerySet:
        """Narrow ``queryset`` by the sanitized ``values``."""
        if self._apply is not None:
            return self._apply(queryset, values)
        return queryset.filter(**{self.lookup: values if self.multi else values[0]})

    def apply_from_request(self, queryset: QuerySet, request: Request) -> QuerySet:
        return self.apply(queryset, self.clean_values(request.query_params[self.name]))

    def resolve_options(self, request: Request) -> list[dict]:
        options = self._options
        if callable(options):
            options = options(request)
        return list(options or [])

    def catalogue_entry(self, request: Request) -> dict:
        entry: dict[str, object] = {
            "filter": self.name,
            "kind": self.kind,
            "description": self.description,
        }
        if self._options is not None:
            entry["options"] = self.resolve_options(request)
        return entry

    def openapi_parameters(self) -> list[OpenApiParameter]:
        hint = self.description or f"Filter by {self.name}."
        shape = (
            "Comma-separated (any match); AND-ed with the other filters."
            if self.multi
            else "Single value; AND-ed with the other filters."
        )
        return [OpenApiParameter(self.name, OpenApiTypes.STR, description=f"{hint} {shape}")]


class RangeFilter(ListFilter):
    """A two-bound filter: ``?<name>_after=`` / ``?<name>_before=`` (inclusive).

    This is how open-ended filters are expressed -- a comma list can name a set
    but can't say "between", so anything ordered (dates, numbers) gets a
    lower/upper pair instead. Send either bound or both.

    ``name``
        Base name; the params are ``<name>_after`` / ``<name>_before`` and the
        catalogue entry is keyed by ``name``.
    ``field``
        ORM field the bounds compare against (``__gte`` / ``__lte``); defaults
        to ``name``. ``__`` lookups across relations are fine.
    ``parse``
        Bound coercion (default :func:`parse_datetime`; also :func:`parse_date`,
        :func:`parse_int`).
    ``kind``
        Catalogue widget hint; defaults to ``"<parser-kind>_range"``.
    """

    def __init__(
        self,
        name: str,
        *,
        field: str | None = None,
        parse: ValueParser = parse_datetime,
        description: str = "",
        kind: str | None = None,
        suffixes: tuple[str, str] = ("after", "before"),
    ) -> None:
        self.name = name
        self.field = field or name
        self.parse = parse
        self.description = description
        self.kind = kind or f"{_PARSER_KIND.get(parse, 'text')}_range"
        self.lower_param = f"{name}_{suffixes[0]}"
        self.upper_param = f"{name}_{suffixes[1]}"

    def param_names(self) -> tuple[str, ...]:
        return (self.lower_param, self.upper_param)

    def apply_from_request(self, queryset: QuerySet, request: Request) -> QuerySet:
        bounds: dict[str, object] = {}
        raw_lower = request.query_params.get(self.lower_param, "").strip()
        raw_upper = request.query_params.get(self.upper_param, "").strip()
        if raw_lower:
            bounds[f"{self.field}__gte"] = self.parse(raw_lower)
        if raw_upper:
            bounds[f"{self.field}__lte"] = self.parse(raw_upper)
        if not bounds:
            raise serializers.ValidationError(
                {self.name: f"Provide {self.lower_param} and/or {self.upper_param}."}
            )
        lower = bounds.get(f"{self.field}__gte")
        upper = bounds.get(f"{self.field}__lte")
        if lower is not None and upper is not None and lower > upper:  # type: ignore[operator]
            raise serializers.ValidationError(
                {self.name: f"{self.lower_param} must be <= {self.upper_param}."}
            )
        return queryset.filter(**bounds)

    def catalogue_entry(self, request: Request) -> dict:
        return {
            "filter": self.name,
            "kind": self.kind,
            "params": list(self.param_names()),
            "description": self.description,
        }

    def openapi_parameters(self) -> list[OpenApiParameter]:
        api_type = {
            "date_range": OpenApiTypes.DATE,
            "datetime_range": OpenApiTypes.DATETIME,
        }.get(self.kind, OpenApiTypes.NUMBER)
        hint = self.description or f"Bound on {self.field}."
        return [
            OpenApiParameter(
                self.lower_param, api_type, description=f"{hint} Inclusive lower bound."
            ),
            OpenApiParameter(
                self.upper_param, api_type, description=f"{hint} Inclusive upper bound."
            ),
        ]


# -- Sort options ------------------------------------------------------

class SortOption:
    """One named, whitelisted sort the client may ask for via ``?sort=``.

    ``name``
        The token the client sends (optionally ``-``-prefixed for descending).
    ``fields``
        The ORM ``order_by`` field(s) the token maps to, ascending. Defaults to
        ``(name,)``. Descending flips every field. Give several for a composite
        sort (``("company_name", "-created_at")`` -> name A->Z, newest first
        within a name).
    ``description``
        Human hint surfaced to the client in the catalogue.
    """

    def __init__(
        self,
        name: str,
        *,
        fields: Sequence[str] | None = None,
        description: str = "",
    ) -> None:
        self.name = name
        self.fields = tuple(fields) if fields else (name,)
        self.description = description

    def order_by(self, *, descending: bool) -> list[str]:
        """The ORM ordering fragments for this option in the asked direction."""
        if not descending:
            return list(self.fields)
        return [f[1:] if f.startswith("-") else f"-{f}" for f in self.fields]

    def catalogue_entry(self) -> dict:
        """The ``available_sorts`` entry handed to the client."""
        return {"sort": self.name, "description": self.description}


# -- OpenAPI --------------------------------------------------------------


class FilterCatalogueEntrySerializer(serializers.Serializer):
    """Schema for one ``available_filters`` entry."""

    filter = serializers.CharField()
    kind = serializers.CharField(
        help_text="Widget hint: select, int, text, date, datetime, date_range, datetime_range, ..."
    )
    description = serializers.CharField()
    params = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="The query params this filter reads (range filters have two).",
    )
    options = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Eligible {value, label} choices, when the filter is closed-ended.",
    )


class SortCatalogueEntrySerializer(serializers.Serializer):
    """Schema for one ``available_sorts`` entry."""

    sort = serializers.CharField()
    description = serializers.CharField()


def list_query_parameters(
    *,
    queryset_filters: Sequence[ListFilter] = (),
    sort_options: Sequence[SortOption] = (),
    date_window: str = "required",
) -> list[OpenApiParameter]:
    """Build the drf-spectacular ``parameters`` list for a paginated list view.

    Pass a view's own ``queryset_filters`` / ``sort_options`` so the documented
    query string stays in lockstep with what the view actually accepts.
    ``date_window`` is ``"required"`` (default), ``"optional"`` or ``"none"``.
    """
    params = [
        OpenApiParameter("page", OpenApiTypes.INT, description="1-based page number."),
        OpenApiParameter(
            "page_size", OpenApiTypes.INT, description="Rows per page (default 10, max 30)."
        ),
    ]
    if date_window != "none":
        required = date_window == "required"
        for name in DATE_RANGE_PARAMS:
            params.append(
                OpenApiParameter(
                    name,
                    OpenApiTypes.DATETIME,
                    required=required,
                    description=f"ISO 8601. {name.replace('_', ' ').capitalize()} of the window.",
                )
            )
    for spec in queryset_filters:
        params.extend(spec.openapi_parameters())
    if sort_options:
        names = ", ".join(option.name for option in sort_options)
        params.append(
            OpenApiParameter(
                "sort",
                OpenApiTypes.STR,
                description=(
                    f"Comma-separated sort keys ({names}); prefix a key with '-' "
                    "for descending. Defaults to the view's natural order."
                ),
            )
        )
    return params


class _PaginatedDateRangeListMixin(Generic[_ModelT]):
    """Provides ``GET`` for a paginated list view with an optional date window,
    optional client-selectable filters and optional client-selectable sorting.

    A subclass must implement :meth:`get_queryset` and :meth:`serialize_page`,
    and may set:

    * :attr:`date_field` -- the timestamp column the window filters on, possibly
      spanning a relation (``"order__created_at"``). Defaults to ``created_at``.
    * :attr:`enforce_date_range_filters` (default ``True``) -- whether a request
      with neither ``start_date_time`` nor ``end_date_time`` is a ``400``
      (``True``) or is served unfiltered (``False``). A partial pair is always
      a ``400``.
    * :attr:`queryset_filters` -- the :class:`ListFilter` tuple the view accepts
      (:class:`QuerysetFilter` single-param, :class:`RangeFilter` two-bound).
      The ones whose param(s) are present are AND-ed on. Every response carries
      ``available_filters``.
    * :attr:`sort_options` -- the :class:`SortOption` tuple the view accepts via
      ``?sort=<csv>``. Every response carries ``available_sorts``.
    * :attr:`default_sort` -- ORM ordering (a field string or a sequence of
      them) used when ``?sort`` is absent. A ``pk`` tie-breaker is always added.

    Not for direct use -- compose it through one of the concrete client bases.
    """

    date_field: str = "created_at"
    enforce_date_range_filters: bool = True
    queryset_filters: tuple[ListFilter, ...] = ()
    sort_options: tuple[SortOption, ...] = ()
    default_sort: str | Sequence[str] = ()
    pagination_class = StandardPageNumberPagination

    def get_queryset(self, request: Request) -> QuerySet[_ModelT]:
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_queryset(self, request)."
        )

    def serialize_page(self, page_items: list[_ModelT], request: Request) -> object:
        raise NotImplementedError(
            f"{type(self).__name__} must implement "
            "serialize_page(self, page_items, request)."
        )

    # -- catalogues ---------------------------------------------------------

    def _filters(self) -> tuple[ListFilter, ...]:
        """The declared filters, validated (raises on a config bug)."""
        seen: set[str] = set()
        for spec in self.queryset_filters:
            for param in spec.param_names():
                if param in RESERVED_QUERY_PARAMS:
                    raise ValueError(f"Filter param '{param}' is a reserved query param.")
                if param in seen:
                    raise ValueError(f"Duplicate filter param '{param}'.")
                seen.add(param)
        return tuple(self.queryset_filters)

    def _sort_catalogue(self) -> dict[str, SortOption]:
        """The declared sort options, keyed by name (raises on a config bug)."""
        catalogue: dict[str, SortOption] = {}
        for option in self.sort_options:
            if option.name in RESERVED_QUERY_PARAMS:
                raise ValueError(f"Sort name '{option.name}' is a reserved query param.")
            if option.name in catalogue:
                raise ValueError(f"Duplicate sort option '{option.name}'.")
            catalogue[option.name] = option
        return catalogue

    # -- request parsing --------------------------------------------------

    def _date_range_filter(self, request: Request) -> dict[str, object]:
        """ORM kwargs for the requested window, or ``{}`` for no filtering.

        Returns ``{}`` only when the window is optional
        (``enforce_date_range_filters`` is ``False``) and the request supplied
        neither bound. Any other case goes through
        :class:`DateRangeQuerySerializer`, so a missing or partial pair raises
        the usual ``400``.
        """
        supplied = any(name in request.query_params for name in DATE_RANGE_PARAMS)
        if not supplied and not self.enforce_date_range_filters:
            return {}

        params = DateRangeQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        return {
            f"{self.date_field}__gte": params.validated_data["start_date_time"],
            f"{self.date_field}__lte": params.validated_data["end_date_time"],
        }

    def _apply_filters(
        self,
        queryset: QuerySet,
        request: Request,
        filters: tuple[ListFilter, ...],
    ) -> QuerySet:
        """AND every declared filter whose param(s) are present onto ``queryset``.

        Raises ``serializers.ValidationError`` for an unparseable / empty value.
        Params that are not declared filters are ignored.
        """
        for spec in filters:
            if spec.applies_to(request):
                queryset = spec.apply_from_request(queryset, request)
        return queryset

    def _ordering(
        self, request: Request, catalogue: dict[str, SortOption]
    ) -> list[str]:
        """The ORM ``order_by`` args for this request (always ends with ``pk``).

        Raises ``serializers.ValidationError`` for an unknown sort name.
        """
        raw = request.query_params.get("sort")
        order: list[str] = []
        if raw and raw.strip():
            seen: set[str] = set()
            for token in (part.strip() for part in raw.split(",")):
                if not token:
                    continue
                descending = token.startswith("-")
                key = token[1:] if descending else token
                option = catalogue.get(key)
                if option is None:
                    available = ", ".join(catalogue) or "none"
                    raise serializers.ValidationError(
                        {"sort": f"Unknown sort '{key}'. Available: {available}."}
                    )
                if key in seen:
                    continue
                seen.add(key)
                order.extend(option.order_by(descending=descending))
        if not order:
            default = self.default_sort
            order = [default] if isinstance(default, str) else list(default)
        order.append("pk")
        return order

    # -- response --------------------------------------------------------

    def get(self, request: Request, *args, **kwargs) -> Response:
        filters = self._filters()
        sort_catalogue = self._sort_catalogue()

        queryset = self.get_queryset(request).filter(**self._date_range_filter(request))
        queryset = self._apply_filters(queryset, request, filters)
        queryset = queryset.order_by(*self._ordering(request, sort_catalogue))

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        response = paginator.get_paginated_response(self.serialize_page(page, request))
        if filters:
            response.data["available_filters"] = [
                spec.catalogue_entry(request) for spec in filters
            ]
        if sort_catalogue:
            response.data["available_sorts"] = [
                option.catalogue_entry() for option in sort_catalogue.values()
            ]
        return response
