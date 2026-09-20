import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/orders_table.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

final OrderModel _order = OrderModel(
  publicId: 'ORD-X1Q5NK84WGV2',
  createdAt: DateTime.utc(2026, 9, 14, 18, 2, 5),
  status: OrderStatus.booked,
  client: const OrderRefModel(publicId: 'C-BREB4DIUEQ6Y', name: 'sgdg'),
  clientCreatedBy: 'Sales Person User',
  createdBy: 'Sales Person User',
  deliveryAddress: 'eywy, Rajkot, Gujarat, India',
  city: const OrderCityModel(id: 3, name: 'Rajkot'),
  dispatchMode: 'PRIVATE',
  expectedDeliveryDate: DateTime.utc(2026, 9, 15),
  totalAmount: 9800,
  totalPackets: 60,
  itemCount: 2,
);

Future<void> _pumpTable(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(2400, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: OrdersTable(
          orders: [_order],
          isLoading: false,
          isMutating: false,
          currentPage: 1,
          totalPages: 1,
          totalItems: 1,
          onFetchData:
              ({
                required int page,
                required int limit,
                String? search,
                String? sortBy,
                String? sortOrder,
                Map<String, String>? filters,
              }) {},
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('the orders table shows the specified fields', () {
    testWidgets('the order id is the first column and is shown', (
      tester,
    ) async {
      await _pumpTable(tester);

      expect(find.text('ORD-X1Q5NK84WGV2'), findsOneWidget);
      expect(find.text(AppStrings.COLUMN_ORDER_ID), findsOneWidget);
    });

    testWidgets('client and address are on the row', (tester) async {
      await _pumpTable(tester);

      expect(find.text('sgdg'), findsOneWidget);
      expect(find.text('eywy, Rajkot, Gujarat, India'), findsOneWidget);
    });

    testWidgets('dispatch and expected delivery stay in the detail view', (
      tester,
    ) async {
      await _pumpTable(tester);

      expect(find.text(AppStrings.ORDER_DISPATCH_PRIVATE), findsNothing);
      expect(find.text('15 Sep 2026'), findsNothing);
    });

    testWidgets('both people columns are on the row', (tester) async {
      await _pumpTable(tester);

      expect(find.text(AppStrings.COLUMN_ORDER_SALES_PERSON), findsOneWidget);
      expect(find.text(AppStrings.COLUMN_ORDER_VERIFIED_BY), findsOneWidget);
      expect(
        find.text(AppStrings.COLUMN_ORDER_CLIENT_ONBOARDED_BY),
        findsOneWidget,
      );
    });

    testWidgets('dates are rendered in IST', (tester) async {
      await _pumpTable(tester);

      // 18:02 UTC on the 14th is 11:32 PM IST the same evening.
      expect(find.textContaining('11:32 PM'), findsOneWidget);
      expect(find.textContaining('IST'), findsOneWidget);
    });

    testWidgets('the client public id is never shown', (tester) async {
      await _pumpTable(tester);

      expect(find.text('C-BREB4DIUEQ6Y'), findsNothing);
    });

    testWidgets('per-line detail stays out of the table', (tester) async {
      await _pumpTable(tester);

      // Packets and product names belong to the detail dialog.
      expect(find.text('60'), findsNothing);
      expect(find.text('SAI-33'), findsNothing);
    });
  });

  group('table presentation', () {
    testWidgets('cell values are centred, not left aligned', (tester) async {
      await _pumpTable(tester);

      // A left-aligned cell would sit against the column edge; centring is
      // what the Center ancestor provides.
      expect(
        find.ancestor(
          of: find.text('ORD-X1Q5NK84WGV2'),
          matching: find.byType(Center),
        ),
        findsWidgets,
      );
      final Iterable<Align> leftAligned = tester
          .widgetList<Align>(
            find.ancestor(of: find.text('sgdg'), matching: find.byType(Align)),
          )
          .where((align) => align.alignment == Alignment.centerLeft);
      expect(leftAligned, isEmpty);
    });

    testWidgets('the order id is the leading column', (tester) async {
      await _pumpTable(tester);

      final double idX = tester.getTopLeft(find.text('ORD-X1Q5NK84WGV2')).dx;
      final double clientX = tester.getTopLeft(find.text('sgdg')).dx;

      expect(idX, lessThan(clientX));
    });
  });
}
