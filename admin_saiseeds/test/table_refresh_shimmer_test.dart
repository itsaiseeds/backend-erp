import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/theme/app_theme.dart';
import 'package:admin_saiseeds/core/widgets/loaders/shimmer_rows.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_data_column.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_data_table.dart';

Widget _table({required bool isLoading, required List<String> items}) {
  return MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(
      body: AppDataTable<String>(
        items: items,
        isLoading: isLoading,
        currentPage: 1,
        totalPages: 0,
        totalItems: items.length,
        configKey: 'shimmer_probe',
        columns: const [AppDataColumn(id: 'name', label: 'Name')],
        cellBuilder: (context, item, column) => Text(item),
      ),
    ),
  );
}

void main() {
  testWidgets('shimmer shows while refreshing with rows already loaded', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(1400, 900);
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      _table(isLoading: false, items: const ['Alpha', 'Beta']),
    );
    await tester.pumpAndSettle();

    expect(find.text('Alpha'), findsOneWidget);
    expect(find.byType(ShimmerRows), findsNothing);

    await tester.pumpWidget(
      _table(isLoading: true, items: const ['Alpha', 'Beta']),
    );
    await tester.pump();

    expect(find.byType(ShimmerRows), findsOneWidget);
  });
}
