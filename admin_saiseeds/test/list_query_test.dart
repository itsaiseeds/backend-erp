import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/utils/list_query.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_filter_search_bar.dart';
import 'package:admin_saiseeds/features/admins/data/models/admin_model.dart';

const List<AdminModel> _admins = [
  AdminModel(
    id: '1',
    name: 'Zara Patel',
    email: 'zara@example.com',
    phoneNumber: '9000000001',
    role: 'admin',
    createdAt: '2026-01-03T00:00:00Z',
  ),
  AdminModel(
    id: '2',
    name: 'Amit Shah',
    email: 'amit@example.com',
    phoneNumber: '9000000002',
    role: 'superuser',
    createdAt: '2026-01-01T00:00:00Z',
  ),
  AdminModel(
    id: '3',
    name: 'Meera Joshi',
    email: 'meera@example.com',
    phoneNumber: '9111111111',
    role: 'admin',
    createdAt: '2026-01-02T00:00:00Z',
  ),
];

List<String> _searchable(AdminModel admin) => [
  admin.name,
  admin.email,
  admin.phoneNumber,
  admin.role,
];

String? _fieldValue(AdminModel admin, String field) {
  switch (field) {
    case AppStrings.FILTER_BY_NAME:
      return admin.name;
    case AppStrings.FILTER_BY_ROLE:
      return admin.role;
    default:
      return null;
  }
}

Comparable<Object>? _sortValue(AdminModel admin, String field) {
  switch (field) {
    case AppStrings.SORT_BY_NAME:
      return admin.name.toLowerCase();
    case AppStrings.SORT_BY_CREATED_AT:
      return admin.createdAt;
    default:
      return null;
  }
}

void main() {
  group('ListQuery.search', () {
    test('returns every row when the query is empty or null', () {
      expect(
        ListQuery.search(
          source: _admins,
          query: null,
          searchableValues: _searchable,
        ).length,
        3,
      );
      expect(
        ListQuery.search(
          source: _admins,
          query: '   ',
          searchableValues: _searchable,
        ).length,
        3,
      );
    });

    test('matches case-insensitively across every searchable field', () {
      final List<AdminModel> byName = ListQuery.search(
        source: _admins,
        query: 'zAra',
        searchableValues: _searchable,
      );
      expect(byName.single.id, '1');

      final List<AdminModel> byEmail = ListQuery.search(
        source: _admins,
        query: 'amit@',
        searchableValues: _searchable,
      );
      expect(byEmail.single.id, '2');

      final List<AdminModel> byPhone = ListQuery.search(
        source: _admins,
        query: '91111',
        searchableValues: _searchable,
      );
      expect(byPhone.single.id, '3');
    });

    test('returns an empty list when nothing matches', () {
      expect(
        ListQuery.search(
          source: _admins,
          query: 'nonexistent',
          searchableValues: _searchable,
        ),
        isEmpty,
      );
    });
  });

  group('ListQuery.filter', () {
    test('applies a single field filter', () {
      final List<AdminModel> filtered = ListQuery.filter(
        source: _admins,
        filters: const {AppStrings.FILTER_BY_ROLE: 'superuser'},
        fieldValue: _fieldValue,
      );
      expect(filtered.single.id, '2');
    });

    test('applies multiple filters conjunctively', () {
      final List<AdminModel> filtered = ListQuery.filter(
        source: _admins,
        filters: const {
          AppStrings.FILTER_BY_ROLE: 'admin',
          AppStrings.FILTER_BY_NAME: 'meera',
        },
        fieldValue: _fieldValue,
      );
      expect(filtered.single.id, '3');
    });

    test('passes everything through when filters are empty', () {
      expect(
        ListQuery.filter(
          source: _admins,
          filters: const {},
          fieldValue: _fieldValue,
        ).length,
        3,
      );
    });
  });

  group('ListQuery.sort', () {
    test('sorts ascending by name', () {
      final List<AdminModel> sorted = ListQuery.sort(
        source: _admins,
        sortBy: AppStrings.SORT_BY_NAME,
        sortOrder: AppFilterSearchBar.SORT_ASCENDING,
        sortValue: _sortValue,
      );
      expect(sorted.map((admin) => admin.name), [
        'Amit Shah',
        'Meera Joshi',
        'Zara Patel',
      ]);
    });

    test('sorts descending by created_at', () {
      final List<AdminModel> sorted = ListQuery.sort(
        source: _admins,
        sortBy: AppStrings.SORT_BY_CREATED_AT,
        sortOrder: AppFilterSearchBar.SORT_DESCENDING,
        sortValue: _sortValue,
      );
      expect(sorted.map((admin) => admin.id), ['1', '3', '2']);
    });

    test('leaves order untouched when no sort field is given', () {
      final List<AdminModel> sorted = ListQuery.sort(
        source: _admins,
        sortBy: null,
        sortOrder: AppFilterSearchBar.SORT_ASCENDING,
        sortValue: _sortValue,
      );
      expect(sorted.map((admin) => admin.id), ['1', '2', '3']);
    });
  });

  group('ListQuery.withoutPagination', () {
    test('returns every item and reports no pages', () {
      final ListQueryResult<AdminModel> result =
          ListQuery.withoutPagination(source: _admins);

      expect(result.items.length, _admins.length);
      expect(result.totalItems, _admins.length);
      expect(result.totalPages, 0);
      expect(result.page, 1);
    });

    test('an empty source still reports no pages', () {
      final ListQueryResult<AdminModel> result =
          ListQuery.withoutPagination<AdminModel>(source: const []);

      expect(result.items, isEmpty);
      expect(result.totalItems, 0);
      expect(result.totalPages, 0);
    });
  });

  group('ListQuery.paginate', () {
    test('splits the list into pages and reports totals', () {
      final ListQueryResult<AdminModel> firstPage = ListQuery.paginate(
        source: _admins,
        page: 1,
        limit: 2,
      );
      expect(firstPage.items.length, 2);
      expect(firstPage.totalItems, 3);
      expect(firstPage.totalPages, 2);
      expect(firstPage.page, 1);

      final ListQueryResult<AdminModel> secondPage = ListQuery.paginate(
        source: _admins,
        page: 2,
        limit: 2,
      );
      expect(secondPage.items.single.id, '3');
    });

    test('clamps an out-of-range page to the last page', () {
      final ListQueryResult<AdminModel> result = ListQuery.paginate(
        source: _admins,
        page: 99,
        limit: 2,
      );
      expect(result.page, 2);
      expect(result.items.single.id, '3');
    });

    test('returns everything when limit is not yet known', () {
      final ListQueryResult<AdminModel> result = ListQuery.paginate(
        source: _admins,
        page: 1,
        limit: 0,
      );
      expect(result.items.length, 3);
      expect(result.totalPages, 1);
    });

    test('handles an empty source', () {
      final ListQueryResult<AdminModel> result = ListQuery.paginate(
        source: const <AdminModel>[],
        page: 1,
        limit: 10,
      );
      expect(result.items, isEmpty);
      expect(result.totalItems, 0);
      expect(result.totalPages, 0);
    });
  });

  test('search then sort then paginate composes as the cubit uses it', () {
    final List<AdminModel> searched = ListQuery.search(
      source: _admins,
      query: 'example.com',
      searchableValues: _searchable,
    );
    final List<AdminModel> sorted = ListQuery.sort(
      source: searched,
      sortBy: AppStrings.SORT_BY_NAME,
      sortOrder: AppFilterSearchBar.SORT_ASCENDING,
      sortValue: _sortValue,
    );
    final ListQueryResult<AdminModel> paged = ListQuery.paginate(
      source: sorted,
      page: 1,
      limit: 2,
    );

    expect(paged.totalItems, 3);
    expect(paged.totalPages, 2);
    expect(paged.items.map((admin) => admin.name), [
      'Amit Shah',
      'Meera Joshi',
    ]);
  });
}
