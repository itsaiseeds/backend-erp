import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_data_column.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_data_table.dart';

void main() {
  testWidgets('probe: pinned header and body edges line up', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(900, 600);
    addTearDown(tester.view.reset);

    const cols = [
      AppDataColumn(id: 'a', label: 'Order ID', width: 200),
      AppDataColumn(id: 'b', label: 'Client', width: 300),
      AppDataColumn(id: 'c', label: 'Placed', width: 300),
      AppDataColumn(
        id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
        label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
        width: 140,
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppDataTable<int>(
            items: const [1, 2],
            currentPage: 1,
            totalPages: 0,
            totalItems: 2,
            columns: cols,
            configKey: 'probe-align',
            requireColumnSettings: false,
            cellBuilder: (context, item, col) => Text('${col.id}-$item'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final header = tester.getRect(find.text('Actions').first);
    final body = tester.getRect(find.text('Actions-1'));
    debugPrint('header cell : $header');
    debugPrint('body cell   : $body');
    debugPrint('centre delta: ${(header.center.dx - body.center.dx).abs()}');

    // Compare the pinned GROUP edges, not the label centres: the header cell
    // also carries a pin affordance which shifts its text.
    final hdrGroup = tester.getRect(find.ancestor(
      of: find.text('Actions').first,
      matching: find.byType(DecoratedBox),
    ).first);
    final bodyGroup = tester.getRect(find.ancestor(
      of: find.text('Actions-1'),
      matching: find.byType(DecoratedBox),
    ).first);
    debugPrint('header group: $hdrGroup');
    debugPrint('body group  : $bodyGroup');
    debugPrint('left delta  : ${(hdrGroup.left - bodyGroup.left).abs()}');
  });
}
