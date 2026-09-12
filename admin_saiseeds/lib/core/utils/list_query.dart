import '../widgets/inputs/app_filter_search_bar.dart';

class ListQueryResult<T> {
  final List<T> items;
  final int totalItems;
  final int totalPages;
  final int page;

  const ListQueryResult({
    required this.items,
    required this.totalItems,
    required this.totalPages,
    required this.page,
  });
}

class ListQuery {
  ListQuery._();

  static List<T> search<T>({
    required List<T> source,
    required String? query,
    required List<String> Function(T item) searchableValues,
  }) {
    final String needle = (query ?? '').trim().toLowerCase();
    if (needle.isEmpty) return List<T>.from(source);

    return source
        .where(
          (item) => searchableValues(
            item,
          ).any((value) => value.toLowerCase().contains(needle)),
        )
        .toList();
  }

  static List<T> filter<T>({
    required List<T> source,
    required Map<String, String>? filters,
    required String? Function(T item, String field) fieldValue,
  }) {
    if (filters == null || filters.isEmpty) return List<T>.from(source);

    return source.where((item) {
      for (final MapEntry<String, String> entry in filters.entries) {
        final String expected = entry.value.trim().toLowerCase();
        if (expected.isEmpty) continue;
        final String actual = (fieldValue(item, entry.key) ?? '').toLowerCase();
        if (!actual.contains(expected)) return false;
      }
      return true;
    }).toList();
  }

  static List<T> sort<T>({
    required List<T> source,
    required String? sortBy,
    required String? sortOrder,
    required Comparable<Object>? Function(T item, String field) sortValue,
  }) {
    final List<T> sorted = List<T>.from(source);
    if (sortBy == null || sortBy.isEmpty) return sorted;

    final bool isDescending = sortOrder == AppFilterSearchBar.SORT_DESCENDING;

    sorted.sort((a, b) {
      final Comparable<Object>? left = sortValue(a, sortBy);
      final Comparable<Object>? right = sortValue(b, sortBy);
      if (left == null && right == null) return 0;
      if (left == null) return 1;
      if (right == null) return -1;
      final int comparison = left.compareTo(right);
      return isDescending ? -comparison : comparison;
    });

    return sorted;
  }

  static ListQueryResult<T> withoutPagination<T>({required List<T> source}) {
    return ListQueryResult<T>(
      items: List<T>.from(source),
      totalItems: source.length,
      totalPages: 0,
      page: 1,
    );
  }

  static ListQueryResult<T> paginate<T>({
    required List<T> source,
    required int page,
    required int limit,
  }) {
    final int totalItems = source.length;

    if (limit <= 0) {
      return ListQueryResult<T>(
        items: List<T>.from(source),
        totalItems: totalItems,
        totalPages: totalItems > 0 ? 1 : 0,
        page: 1,
      );
    }

    final int totalPages = totalItems == 0
        ? 0
        : ((totalItems + limit - 1) ~/ limit);
    final int safePage = totalPages == 0
        ? 1
        : page.clamp(1, totalPages).toInt();
    final int start = (safePage - 1) * limit;
    final int end = (start + limit) > totalItems ? totalItems : start + limit;

    return ListQueryResult<T>(
      items: start >= totalItems ? <T>[] : source.sublist(start, end),
      totalItems: totalItems,
      totalPages: totalPages,
      page: safePage,
    );
  }
}
