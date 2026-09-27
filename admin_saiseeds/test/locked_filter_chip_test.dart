import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_filter_search_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _pumpBar(
  WidgetTester tester, {
  required Map<String, String> filters,
  Set<String> locked = const {},
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AppFilterSearchBar(
          controller: TextEditingController(),
          hintText: AppStrings.TABLE_SEARCH_WITHIN_RESULTS,
          sortByOptions: const ['created_at'],
          filterByOptions: const ['status', 'city_id'],
          initialFilters: filters,
          lockedFilters: locked,
          getHumanReadableFilterName: (value) => value,
          getHumanReadableSortName: (value) => value,
          onSearch: ({search = "", sortBy, sortOrder, filters = const {}}) {},
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

int _removeButtonCount(WidgetTester tester) => find
    .descendant(
      of: find.byType(AppFilterSearchBar),
      matching: find.byIcon(Icons.close_rounded),
    )
    .evaluate()
    .length;

void main() {
  testWidgets('an unlocked chip offers a remove button', (tester) async {
    await _pumpBar(tester, filters: {'city_id': '1'});

    expect(_removeButtonCount(tester), 1);
  });

  testWidgets('a locked chip offers no remove button', (tester) async {
    await _pumpBar(
      tester,
      filters: {'status': 'VERIFIED'},
      locked: {'status'},
    );

    expect(find.text('status'), findsOneWidget);
    expect(_removeButtonCount(tester), 0);
  });

  testWidgets('locking one chip leaves the others removable', (tester) async {
    await _pumpBar(
      tester,
      filters: {'status': 'VERIFIED', 'city_id': '1'},
      locked: {'status'},
    );

    expect(find.text('status'), findsOneWidget);
    expect(find.text('city_id'), findsOneWidget);
    expect(_removeButtonCount(tester), 1);
  });

  testWidgets('a locked chip survives a discarded edit', (tester) async {
    await _pumpBar(
      tester,
      filters: {'status': 'VERIFIED'},
      locked: {'status'},
    );

    await tester.tap(find.text('status'));
    await tester.pumpAndSettle();

    await tester.tap(
      find.byTooltip(AppStrings.TABLE_DISCARD_FILTER),
      warnIfMissed: false,
    );
    await tester.pumpAndSettle();

    expect(find.text('status'), findsOneWidget);
    expect(find.text('VERIFIED'), findsOneWidget);
  });
}
