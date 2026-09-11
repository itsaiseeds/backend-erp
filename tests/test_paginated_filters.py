"""Unit tests for the filter / sort sanitization and request handling behind
the paginated list views (``common.views.paginated_date_range``).

Mostly pure -- no database -- so they run on ``SimpleTestCase``; the mixin
request tests drive it with a fake queryset. The end-to-end behaviour against a
real endpoint (a real DB, the ``?<filter>=`` / ``?sort=`` wiring, pagination) is
in ``tests/android/test_clients.py::AndroidClientApiTest``.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from common.views.paginated_date_range import (
    DATE_RANGE_PARAMS,
    MAX_FILTER_VALUES,
    QuerysetFilter,
    RangeFilter,
    SortOption,
    _PaginatedDateRangeListMixin,
    list_query_parameters,
    parse_date,
    parse_int,
    parse_str,
)


class _FakeQuerySet:
    """Records the last ``.filter()`` call so the default apply can be asserted."""

    def __init__(self):
        self.filtered_with: dict | None = None

    def filter(self, **kwargs):
        self.filtered_with = kwargs
        return self


class QuerysetFilterCleanValuesTest(SimpleTestCase):
    """tests/test_paginated_filters.py::QuerysetFilterCleanValuesTest"""

    def setUp(self):
        self.spec = QuerysetFilter("city_id__in")

    def test_splits_and_coerces_a_csv_of_ints(self):
        self.assertEqual(self.spec.clean_values("1,2,3"), [1, 2, 3])

    def test_trims_whitespace_and_drops_blank_segments(self):
        self.assertEqual(self.spec.clean_values(" 1 , , 2 ,"), [1, 2])

    def test_collapses_duplicates_keeping_first_seen_order(self):
        self.assertEqual(self.spec.clean_values("2,1,2,1"), [2, 1])

    def test_missing_param_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            self.spec.clean_values(None)

    def test_blank_param_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            self.spec.clean_values("   ")

    def test_only_separators_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            self.spec.clean_values(",, ,")

    def test_a_non_integer_segment_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            self.spec.clean_values("1,abc")

    def test_too_many_values_are_rejected(self):
        raw = ",".join(str(n) for n in range(MAX_FILTER_VALUES + 1))
        with self.assertRaises(serializers.ValidationError):
            self.spec.clean_values(raw)

    def test_exactly_the_limit_is_allowed(self):
        raw = ",".join(str(n) for n in range(MAX_FILTER_VALUES))
        self.assertEqual(len(self.spec.clean_values(raw)), MAX_FILTER_VALUES)

    def test_a_string_parser_can_be_supplied(self):
        spec = QuerysetFilter("status_code__in", parse=parse_str)
        self.assertEqual(spec.clean_values(" booked , shipped "), ["booked", "shipped"])

    def test_multi_false_keeps_the_whole_value_as_one_term(self):
        spec = QuerysetFilter("company_name", parse=parse_str, multi=False)

        self.assertEqual(spec.clean_values(" Acme, Inc "), ["Acme, Inc"])

    def test_multi_false_still_rejects_a_blank_value(self):
        spec = QuerysetFilter("company_name", parse=parse_str, multi=False)

        with self.assertRaises(serializers.ValidationError):
            spec.clean_values("   ")


class QuerysetFilterApplyTest(SimpleTestCase):
    """tests/test_paginated_filters.py::QuerysetFilterApplyTest"""

    def test_default_apply_uses_the_name_as_a_django_lookup(self):
        queryset = _FakeQuerySet()

        QuerysetFilter("status_id__in").apply(queryset, [1, 2])

        self.assertEqual(queryset.filtered_with, {"status_id__in": [1, 2]})

    def test_lookup_overrides_the_param_name_for_the_default_apply(self):
        queryset = _FakeQuerySet()

        QuerysetFilter(
            "company_name", lookup="company_name__icontains", parse=parse_str, multi=False
        ).apply(queryset, ["acme"])

        self.assertEqual(queryset.filtered_with, {"company_name__icontains": "acme"})

    def test_a_custom_apply_callable_takes_over(self):
        spec = QuerysetFilter("city_id", apply=lambda qs, values: (qs, values))

        self.assertEqual(spec.apply("QS", [7]), ("QS", [7]))

    def test_catalogue_entry_carries_name_label_kind_and_description(self):
        spec = QuerysetFilter("city_id", description="primary address city")

        self.assertEqual(
            spec.catalogue_entry(request=None),
            {
                "filter": "city_id",
                # Defaulted from the name: trailing "_id" dropped, title-cased.
                "label": "City",
                "kind": "int",
                "description": "primary address city",
            },
        )

    def test_an_explicit_label_overrides_the_derived_one(self):
        spec = QuerysetFilter("city_id", label="Delivery City")

        self.assertEqual(spec.catalogue_entry(request=None)["label"], "Delivery City")

    def test_kind_defaults_from_the_parser_and_is_overridable(self):
        self.assertEqual(QuerysetFilter("q", parse=parse_str).kind, "text")
        self.assertEqual(QuerysetFilter("q", kind="search").kind, "search")

    def test_options_flip_the_kind_to_select_and_accept_a_static_list(self):
        spec = QuerysetFilter(
            "city_id",
            description="city",
            options=[{"value": 1, "label": "Surat"}],
        )

        self.assertEqual(
            spec.catalogue_entry(request="req"),
            {
                "filter": "city_id",
                "label": "City",
                "kind": "select",
                "description": "city",
                "options": [{"value": 1, "label": "Surat"}],
            },
        )

    def test_options_may_also_be_a_request_aware_callable(self):
        spec = QuerysetFilter(
            "city_id", options=lambda request: [{"value": request, "label": "x"}]
        )

        self.assertEqual(
            spec.catalogue_entry(request=7)["options"], [{"value": 7, "label": "x"}]
        )


class ValueParserTest(SimpleTestCase):
    """tests/test_paginated_filters.py::ValueParserTest"""

    def test_parse_int_accepts_digits(self):
        self.assertEqual(parse_int("42"), 42)

    def test_parse_int_rejects_words(self):
        with self.assertRaises(serializers.ValidationError):
            parse_int("nope")

    def test_parse_str_trims(self):
        self.assertEqual(parse_str("  hi  "), "hi")

    def test_parse_str_rejects_blank(self):
        with self.assertRaises(serializers.ValidationError):
            parse_str("   ")

    def test_parse_date_accepts_iso(self):
        self.assertEqual(str(parse_date(" 2026-09-10 ")), "2026-09-10")

    def test_parse_date_rejects_garbage(self):
        with self.assertRaises(serializers.ValidationError):
            parse_date("not-a-date")


class _FilterQuerySet:
    """Records ``.filter()`` kwargs so a range filter's ORM output is checkable."""

    def __init__(self):
        self.filtered_with: dict = {}

    def filter(self, **kwargs):
        self.filtered_with.update(kwargs)
        return self


class RangeFilterTest(SimpleTestCase):
    """tests/test_paginated_filters.py::RangeFilterTest"""

    factory = APIRequestFactory()

    def setUp(self):
        self.spec = RangeFilter("created", field="created_at", parse=parse_date)

    def _request(self, **params):
        return Request(self.factory.get("/", params))

    def test_it_owns_an_after_and_a_before_param(self):
        self.assertEqual(self.spec.param_names(), ("created_after", "created_before"))

    def test_only_the_after_bound_yields_a_gte(self):
        qs = _FilterQuerySet()

        self.spec.apply_from_request(qs, self._request(created_after="2026-01-01"))

        self.assertEqual(list(qs.filtered_with), ["created_at__gte"])

    def test_both_bounds_yield_a_closed_interval(self):
        qs = _FilterQuerySet()

        self.spec.apply_from_request(
            qs, self._request(created_after="2026-01-01", created_before="2026-02-01")
        )

        self.assertEqual(
            sorted(qs.filtered_with), ["created_at__gte", "created_at__lte"]
        )

    def test_neither_bound_present_is_a_400(self):
        with self.assertRaises(serializers.ValidationError):
            self.spec.apply_from_request(_FilterQuerySet(), self._request(created_after=""))

    def test_inverted_bounds_are_a_400(self):
        with self.assertRaises(serializers.ValidationError):
            self.spec.apply_from_request(
                _FilterQuerySet(),
                self._request(created_after="2026-02-01", created_before="2026-01-01"),
            )

    def test_catalogue_entry_names_the_two_params_and_a_range_kind(self):
        self.assertEqual(
            self.spec.catalogue_entry(request=None),
            {
                "filter": "created",
                "label": "Created",
                "kind": "date_range",
                "params": ["created_after", "created_before"],
                "description": "",
            },
        )

    def test_applies_to_is_true_when_either_bound_is_present(self):
        self.assertTrue(self.spec.applies_to(self._request(created_before="2026-01-01")))
        self.assertFalse(self.spec.applies_to(self._request(page="2")))


class SortOptionTest(SimpleTestCase):
    """tests/test_paginated_filters.py::SortOptionTest"""

    def test_name_is_the_default_field_ascending(self):
        self.assertEqual(SortOption("company_name").order_by(descending=False), ["company_name"])

    def test_descending_flips_every_field(self):
        option = SortOption("recent", fields=("created_at", "-id"))

        self.assertEqual(option.order_by(descending=True), ["-created_at", "id"])

    def test_catalogue_entry_exposes_name_label_and_description(self):
        self.assertEqual(
            SortOption("created_at", description="added").catalogue_entry(),
            {"sort": "created_at", "label": "Created At", "description": "added"},
        )

    def test_an_explicit_label_overrides_the_derived_one(self):
        option = SortOption("created_at", label="Date added", description="added")

        self.assertEqual(option.catalogue_entry()["label"], "Date added")


class ListQueryParametersTest(SimpleTestCase):
    """tests/test_paginated_filters.py::ListQueryParametersTest"""

    def _names(self, **kwargs):
        return [p.name for p in list_query_parameters(**kwargs)]

    def test_bare_view_documents_page_and_the_required_window(self):
        params = list_query_parameters()

        self.assertEqual([p.name for p in params], ["page", "page_size", *DATE_RANGE_PARAMS])
        window = {p.name: p for p in params if p.name in DATE_RANGE_PARAMS}
        self.assertTrue(all(p.required for p in window.values()))

    def test_optional_window_marks_the_bounds_not_required(self):
        params = {p.name: p for p in list_query_parameters(date_window="optional")}

        self.assertFalse(params["start_date_time"].required)

    def test_none_window_drops_the_bounds(self):
        self.assertEqual(self._names(date_window="none"), ["page", "page_size"])

    def test_filters_and_sort_are_documented(self):
        names = self._names(
            queryset_filters=(QuerysetFilter("city_id"), QuerysetFilter("status__in")),
            sort_options=(SortOption("created_at"), SortOption("company_name")),
            date_window="none",
        )

        self.assertEqual(names, ["page", "page_size", "city_id", "status__in", "sort"])

    def test_a_range_filter_contributes_its_two_bound_params(self):
        names = self._names(
            queryset_filters=(RangeFilter("created", parse=parse_date),),
            date_window="none",
        )

        self.assertEqual(
            names, ["page", "page_size", "created_after", "created_before"]
        )


class _ListQuerySet(list):
    """A list that also answers the queryset calls the mixin makes (all no-ops),
    so the mixin can run without a database. Django's paginator treats it as a
    plain sequence. ``last_order_by`` records the ordering the mixin asked for."""

    def __init__(self, *args):
        super().__init__(*args)
        self.last_order_by: tuple = ()
        self.filter_calls: list[dict] = []

    def filter(self, **kwargs):
        if kwargs:
            self.filter_calls.append(kwargs)
        return self

    def order_by(self, *fields):
        self.last_order_by = fields
        return self


class MixinRequestHandlingTest(SimpleTestCase):
    """End-to-end behaviour of ``_PaginatedDateRangeListMixin.get`` without a DB.

    tests/test_paginated_filters.py::MixinRequestHandlingTest
    """

    factory = APIRequestFactory()

    @staticmethod
    def _view(*, queryset_filters=(), sort_options=(), default_sort=(), enforce=True):
        holder: dict = {}

        class _View(_PaginatedDateRangeListMixin, APIView):
            authentication_classes: list = []
            permission_classes: list = []

            def get_queryset(self, request):
                holder["queryset"] = _ListQuerySet(range(25))
                return holder["queryset"]

            def serialize_page(self, page_items, request):
                return list(page_items)

        _View.queryset_filters = queryset_filters
        _View.sort_options = sort_options
        _View.default_sort = default_sort
        _View.enforce_date_range_filters = enforce
        view = _View.as_view()
        return lambda request: (view(request), holder.get("queryset"))

    def test_no_filters_defined_and_window_enforced_rejects_a_bare_request(self):
        response, _ = self._view()(self.factory.get("/"))

        self.assertEqual(response.status_code, 400)

    def test_no_catalogues_defined_paginates_everything_without_extra_keys(self):
        response, _ = self._view(enforce=False)(self.factory.get("/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 25)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertNotIn("available_filters", response.data)
        self.assertNotIn("available_sorts", response.data)

    def test_no_filter_selected_returns_the_first_page_and_the_catalogue(self):
        view = self._view(
            queryset_filters=(QuerysetFilter("n__in", description="a number"),),
            enforce=False,
        )

        response, _ = view(self.factory.get("/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 25)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertEqual(
            response.data["available_filters"],
            [
                {
                    "filter": "n__in",
                    "label": "N In",
                    "kind": "int",
                    "description": "a number",
                }
            ],
        )

    def test_each_declared_filter_is_its_own_param_and_they_and_together(self):
        applied: list = []
        spec_a = QuerysetFilter("a__in", apply=lambda qs, v: applied.append(("a", v)) or qs)
        spec_b = QuerysetFilter("b__in", apply=lambda qs, v: applied.append(("b", v)) or qs)
        view = self._view(queryset_filters=(spec_a, spec_b), enforce=False)

        response, _ = view(self.factory.get("/", {"a__in": "1,2", "b__in": "9"}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(applied, [("a", [1, 2]), ("b", [9])])

    def test_an_unrecognised_query_param_is_ignored(self):
        view = self._view(queryset_filters=(QuerysetFilter("n__in"),), enforce=False)

        response, _ = view(self.factory.get("/", {"bogus": "1"}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 25)

    def test_a_range_filter_applies_gte_lte_and_echoes_a_range_kind(self):
        view = self._view(
            queryset_filters=(
                RangeFilter("created", field="created_at", parse=parse_date),
            ),
            enforce=False,
        )

        response, queryset = view(
            self.factory.get(
                "/", {"created_after": "2026-01-01", "created_before": "2026-03-01"}
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(k for call in queryset.filter_calls for k in call),
            ["created_at__gte", "created_at__lte"],
        )
        self.assertEqual(
            response.data["available_filters"][0]["kind"], "date_range"
        )

    def test_a_range_filter_with_no_bound_present_serves_the_full_page(self):
        view = self._view(
            queryset_filters=(RangeFilter("created", parse=parse_date),), enforce=False
        )

        response, _ = view(self.factory.get("/"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_count"], 25)

    def test_an_empty_filter_value_is_a_400(self):
        view = self._view(queryset_filters=(QuerysetFilter("n__in"),), enforce=False)

        response, _ = view(self.factory.get("/", {"n__in": ""}))

        self.assertEqual(response.status_code, 400)

    def test_a_non_integer_filter_value_is_a_400(self):
        view = self._view(queryset_filters=(QuerysetFilter("n__in"),), enforce=False)

        response, _ = view(self.factory.get("/", {"n__in": "1,nope"}))

        self.assertEqual(response.status_code, 400)

    def test_sort_maps_to_order_by_with_a_pk_tie_breaker(self):
        view = self._view(
            sort_options=(SortOption("name", fields=("company_name",)),), enforce=False
        )

        _, queryset = view(self.factory.get("/", {"sort": "-name"}))

        self.assertEqual(queryset.last_order_by, ("-company_name", "pk"))

    def test_default_sort_applies_when_sort_is_absent(self):
        view = self._view(
            sort_options=(SortOption("created_at"),),
            default_sort="-created_at",
            enforce=False,
        )

        _, queryset = view(self.factory.get("/"))

        self.assertEqual(queryset.last_order_by, ("-created_at", "pk"))

    def test_an_unknown_sort_is_a_400(self):
        view = self._view(sort_options=(SortOption("created_at"),), enforce=False)

        response, _ = view(self.factory.get("/", {"sort": "bogus"}))

        self.assertEqual(response.status_code, 400)

    def test_available_sorts_is_echoed(self):
        view = self._view(
            sort_options=(SortOption("created_at", description="added"),), enforce=False
        )

        response, _ = view(self.factory.get("/"))

        self.assertEqual(
            response.data["available_sorts"],
            [{"sort": "created_at", "label": "Created At", "description": "added"}],
        )

    def test_a_filter_or_sort_named_like_a_reserved_param_is_a_config_error(self):
        view = self._view(queryset_filters=(QuerysetFilter("page"),), enforce=False)

        with self.assertRaises(ValueError):
            view(self.factory.get("/"))

    def test_a_partial_date_window_is_a_400_even_when_optional(self):
        view = self._view(enforce=False)

        response, _ = view(self.factory.get("/", {"start_date_time": "2026-01-01T00:00Z"}))

        self.assertEqual(response.status_code, 400)
