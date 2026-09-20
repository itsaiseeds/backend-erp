import 'package:dio/dio.dart';
import 'package:admin_saiseeds/features/orders/presentation/bloc/orders_cubit.dart';
import 'package:admin_saiseeds/features/orders/data/orders_repository.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_detail_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

OrderModel _orderWith(int lineCount) {
  return OrderModel(
    publicId: 'ORD-X1Q5NK84WGV2',
    createdAt: DateTime.utc(2026, 9, 14, 18, 2, 5),
    status: OrderStatus.booked,
    client: const OrderRefModel(name: 'sgdg'),
    createdBy: 'Sales Person User',
    clientCreatedBy: 'Sales Person User',
    deliveryAddress: 'eywy, Rajkot, Gujarat, India',
    city: const OrderCityModel(id: 3, name: 'Rajkot'),
    dispatchMode: 'PRIVATE',
    expectedDeliveryDate: DateTime.utc(2026, 9, 15),
    totalAmount: 9800,
    totalPackets: 60,
    itemCount: lineCount,
    packagings: [
      for (int i = 0; i < lineCount; i++)
        OrderPackagingModel(
          publicId: 'PP-$i',
          productPublicId: 'P-$i',
          productName: 'SAI-${100 + i}',
          packetWeight: 1,
          packets: 40,
          totalWeight: 40,
          sellingPrice: 4800,
          negotiatedSellingPrice: 4800,
          quantity: 1,
        ),
    ],
  );
}

Future<void> _openItems(
  WidgetTester tester, {
  required int lineCount,
  Size screen = const Size(1400, 900),
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = screen;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () =>
                OrderDetailDialog.show(
                  context,
                  _orderWith(lineCount),
                  cubit: _cubit(),
                ),
            child: const Text('open'),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();

  await tester.tap(find.text(AppStrings.STEP_NEXT));
  await tester.pumpAndSettle();
}

double _cardHeight(WidgetTester tester) => tester
    .getSize(
      find
          .descendant(
            of: find.byType(AppRecordDialog),
            matching: find.byType(ConstrainedBox),
          )
          .first,
    )
    .height;

OrdersCubit _cubit() =>
    OrdersCubit(repository: OrdersRepository(apiClient: ApiClient(dio: Dio())));

void main() {
  testWidgets('a long order scrolls rather than overflowing', (tester) async {
    await _openItems(tester, lineCount: 30);

    // An unbounded column would throw a RenderFlex overflow here.
    expect(tester.takeException(), isNull);
    expect(find.byType(SingleChildScrollView), findsWidgets);
  });

  testWidgets('a long order does not grow past the screen', (tester) async {
    const Size screen = Size(1400, 900);
    await _openItems(tester, lineCount: 40, screen: screen);

    expect(_cardHeight(tester), lessThanOrEqualTo(screen.height));
  });

  testWidgets('the footer stays visible with many items', (tester) async {
    await _openItems(tester, lineCount: 40);

    // Back and Next sit outside the scroll area, so they never scroll away.
    expect(find.text(AppStrings.STEP_BACK), findsOneWidget);
    expect(find.text(AppStrings.STEP_NEXT), findsOneWidget);
  });

  testWidgets('the header stays visible with many items', (tester) async {
    await _openItems(tester, lineCount: 40);

    expect(find.text(AppStrings.ORDER_DETAILS_TITLE), findsOneWidget);
  });

  testWidgets('later items are reachable by scrolling', (tester) async {
    await _openItems(tester, lineCount: 30, screen: const Size(1400, 700));

    final ScrollableState scrollable = tester.state<ScrollableState>(
      find.descendant(
        of: find.byType(AppRecordDialog),
        matching: find.byType(Scrollable),
      ),
    );

    // Content taller than the viewport is what makes it scrollable at all.
    expect(scrollable.position.maxScrollExtent, greaterThan(0));
    expect(scrollable.position.pixels, 0);

    await tester.drag(
      find.byType(SingleChildScrollView).last,
      const Offset(0, -4000),
    );
    await tester.pumpAndSettle();

    expect(scrollable.position.pixels, scrollable.position.maxScrollExtent);
    expect(find.text('SAI-129'), findsOneWidget);
  });

  testWidgets('a short order does not stretch the dialog', (tester) async {
    await _openItems(tester, lineCount: 2, screen: const Size(1400, 1200));

    expect(_cardHeight(tester), lessThan(1200 - AppSpacing.lg * 2));
  });
}
