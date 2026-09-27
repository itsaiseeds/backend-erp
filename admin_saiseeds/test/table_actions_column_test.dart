import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/orders_table.dart';
import 'package:admin_saiseeds/features/products/data/models/product_model.dart';
import 'package:admin_saiseeds/features/products/presentation/widgets/products_table.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const ProductModel _product = ProductModel(
  publicId: 'P-1',
  name: 'SAI-33',
  sellingPrice: '120',
);

final OrderModel _order = OrderModel(
  publicId: 'ORD-1',
  createdAt: null,
  status: OrderStatus.booked,
  client: const OrderRefModel(name: 'sgdg'),
  dispatchMode: 'PRIVATE',
  totalAmount: 9800,
);

void _noFetch({
  required int page,
  required int limit,
  String? search,
  String? sortBy,
  String? sortOrder,
  Map<String, String>? filters,
}) {}

Future<void> _pump(WidgetTester tester, Widget table) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(2400, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(MaterialApp(home: Scaffold(body: table)));
  await tester.pumpAndSettle();
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('a products row offers delete only, no view or edit', (
    tester,
  ) async {
    bool viewed = false;

    await _pump(
      tester,
      ProductsTable(
        products: const [_product],
        isLoading: false,
        currentPage: 1,
        totalPages: 1,
        totalItems: 1,
        onFetchData: _noFetch,
        onView: (_) => viewed = true,
        onDelete: (_) {},
      ),
    );

    // Edit now lives in the detail dialog header.
    expect(find.byIcon(Icons.edit_outlined), findsNothing);
    expect(find.byIcon(Icons.visibility_outlined), findsNothing);
    expect(find.byIcon(Icons.delete_outline_rounded), findsOneWidget);

    // The row itself still opens the detail view.
    await tester.tap(find.text('SAI-33'));
    await tester.pumpAndSettle();
    expect(viewed, isTrue);
  });

  testWidgets('the orders table drops the empty actions column', (
    tester,
  ) async {
    bool viewed = false;

    await _pump(
      tester,
      OrdersTable(
        orders: [_order],
        isLoading: false,
        isMutating: false,
        currentPage: 1,
        totalPages: 1,
        totalItems: 1,
        onFetchData: _noFetch,
        onView: (_) => viewed = true,
      ),
    );

    expect(find.byIcon(Icons.visibility_outlined), findsNothing);
    expect(find.text(AppStrings.TABLE_ACTIONS_COLUMN_LABEL), findsNothing);

    // The lifecycle column stays; it is not the generic actions column.
    expect(find.text(AppStrings.COLUMN_ORDER_ACTIONS), findsOneWidget);

    await tester.tap(find.text('sgdg'));
    await tester.pumpAndSettle();
    expect(viewed, isTrue);
  });
}
