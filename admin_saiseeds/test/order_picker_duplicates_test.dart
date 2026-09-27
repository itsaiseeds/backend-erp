import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_product_picker_dialog.dart';
import 'package:admin_saiseeds/features/product_packagings/data/product_packagings_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

ProductPackagingsRepository _repository() =>
    ProductPackagingsRepository(apiClient: ApiClient(dio: Dio()));

Future<void> _pump(
  WidgetTester tester, {
  Set<String> existing = const {},
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1600, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: OrderProductPickerDialog(
          repository: _repository(),
          existingPublicIds: existing,
        ),
      ),
    ),
  );
  await tester.pump();
}

/// The picker fires a real fetch on init; let it fail and settle so no timer
/// outlives the test.
Future<void> _drain(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 1));
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pump(const Duration(seconds: 1));
}

void main() {
  testWidgets('the picker accepts the order\'s existing packagings', (
    tester,
  ) async {
    await _pump(tester, existing: const {'PP-1', 'PP-2'});

    final OrderProductPickerDialog picker = tester
        .widget<OrderProductPickerDialog>(
          find.byType(OrderProductPickerDialog),
        );

    expect(picker.existingPublicIds, {'PP-1', 'PP-2'});

    await _drain(tester);
  });

  testWidgets('the picker defaults to no exclusions', (tester) async {
    await _pump(tester);

    final OrderProductPickerDialog picker = tester
        .widget<OrderProductPickerDialog>(
          find.byType(OrderProductPickerDialog),
        );

    expect(picker.existingPublicIds, isEmpty);

    await _drain(tester);
  });

  testWidgets('the duplicate notice spells out the remedy', (tester) async {
    expect(
      AppStrings.ORDER_PICK_ALREADY_BODY,
      contains('quantity'),
      reason: 'the message should point at the existing line',
    );
    expect(AppStrings.ORDER_PICK_ON_ORDER.isNotEmpty, isTrue);
  });
}
