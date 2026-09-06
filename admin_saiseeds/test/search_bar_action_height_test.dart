import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/theme/app_theme.dart';
import 'package:admin_saiseeds/core/widgets/buttons/add_action_button.dart';
import 'package:admin_saiseeds/core/widgets/buttons/icon_action_button.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_filter_search_bar.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_data_column.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_data_table.dart';

void main() {
  testWidgets('search bar actions size correctly against the bar', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(1600, 1000);
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: AppDataTable<String>(
            items: const <String>[],
            isLoading: false,
            currentPage: 1,
            totalPages: 0,
            totalItems: 0,
            configKey: 'height_probe',
            columns: const [AppDataColumn(id: 'name', label: 'Name')],
            cellBuilder: (context, item, column) => const SizedBox.shrink(),
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                onPressed: () {},
              ),
              AddActionButton(tooltip: 'Add', onPressed: () {}),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final double barHeight = tester
        .getSize(find.byType(AppFilterSearchBar))
        .height;
    double paintedHeight(Finder button) {
      final Finder box = find.descendant(
        of: button,
        matching: find.byWidgetPredicate(
          (w) => w is Container && w.decoration is BoxDecoration,
        ),
      );
      return tester.getSize(box.first).height;
    }

    final double refreshHeight = paintedHeight(find.byType(IconActionButton));
    final double addHeight = paintedHeight(find.byType(AddActionButton));

    final double expected = barHeight - (AppSizes.actionButtonInset * 2);
    expect(refreshHeight, expected);
    expect(addHeight, expected);
  });
}
