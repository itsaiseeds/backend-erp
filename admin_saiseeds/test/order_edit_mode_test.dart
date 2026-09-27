import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/widgets/inputs/single_date_field.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/product_packagings/data/product_packagings_repository.dart';
import 'package:admin_saiseeds/features/orders/data/orders_repository.dart';
import 'package:admin_saiseeds/features/orders/presentation/bloc/orders_cubit.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_detail_dialog.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_product_picker_dialog.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

OrderModel _orderWith(OrderStatus status) => OrderModel(
  publicId: 'ORD-X1Q5NK84WGV2',
  createdAt: DateTime.utc(2026, 9, 14, 18, 2, 5),
  status: status,
  client: const OrderRefModel(name: 'Saiseeds'),
  createdBy: 'Sales Person User',
  clientCreatedBy: 'Sales Person User',
  deliveryAddress: 'Line 1, Ahmedabad, Gujarat, India',
  city: const OrderCityModel(id: 3, name: 'Ahmedabad'),
  dispatchMode: 'PRIVATE',
  expectedDeliveryDate: DateTime.utc(2026, 9, 20),
  totalAmount: 9800,
  totalPackets: 60,
  itemCount: 2,
  packagings: const [
    OrderPackagingModel(
      publicId: 'PP-1',
      productName: 'SAI-3353',
      packetWeight: 1,
      packets: 40,
      totalWeight: 40,
      sellingPrice: 4800,
      negotiatedSellingPrice: 4800,
      quantity: 1,
    ),
    OrderPackagingModel(
      publicId: 'PP-2',
      productName: 'SAI-3353',
      packetWeight: 1,
      packets: 20,
      totalWeight: 20,
      sellingPrice: 5000,
      negotiatedSellingPrice: 5000,
      quantity: 1,
    ),
  ],
);

OrdersCubit _cubit() =>
    OrdersCubit(repository: OrdersRepository(apiClient: ApiClient(dio: Dio())));

Future<void> _pump(
  WidgetTester tester, {
  RecordDialogMode mode = RecordDialogMode.view,
  OrderStatus status = OrderStatus.booked,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1600, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () => OrderDetailDialog.show(
                  context,
                  _orderWith(status),
                  cubit: _cubit(),
                  initialMode: mode,
                  packagingsRepository: ProductPackagingsRepository(
                    apiClient: ApiClient(dio: Dio()),
                  ),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
}

Future<void> _goToItems(WidgetTester tester) async {
  await tester.tap(find.text(AppStrings.STEP_NEXT));
  await tester.pumpAndSettle();
}

Future<void> _goToDelivery(WidgetTester tester) async {
  await _goToItems(tester);
  await tester.tap(find.text(AppStrings.STEP_NEXT));
  await tester.pumpAndSettle();
}

Finder _card() => find
    .descendant(of: find.byType(Dialog), matching: find.byType(Container))
    .first;

void main() {
  testWidgets('an editable order offers the pencil', (tester) async {
    await _pump(tester);

    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
  });

  testWidgets('a dispatched order offers no pencil', (tester) async {
    await _pump(tester, status: OrderStatus.dispatched);

    expect(find.byIcon(Icons.edit_outlined), findsNothing);
  });

  testWidgets('delivery uses the in-house calendar, not the Material one', (
    tester,
  ) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToDelivery(tester);

    expect(find.byType(SingleDateField), findsOneWidget);
  });

  testWidgets('view mode shows no date field on delivery', (tester) async {
    await _pump(tester);
    await _goToDelivery(tester);

    expect(find.byType(SingleDateField), findsNothing);
  });

  testWidgets('edit mode offers add and remove on the items step', (
    tester,
  ) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    expect(find.text(AppStrings.ORDER_ADD_ITEM), findsOneWidget);
    expect(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM), findsNWidgets(2));
  });

  testWidgets('view mode offers neither add nor remove', (tester) async {
    await _pump(tester);
    await _goToItems(tester);

    expect(find.text(AppStrings.ORDER_ADD_ITEM), findsNothing);
    expect(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM), findsNothing);
  });

  testWidgets('add item opens the product picker', (tester) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    expect(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM), findsNWidgets(2));

    await tester.tap(find.text(AppStrings.ORDER_ADD_ITEM));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byType(OrderProductPickerDialog), findsOneWidget);
    expect(find.text(AppStrings.ORDER_PICK_PRODUCTS_TITLE), findsOneWidget);
    expect(find.text(AppStrings.ORDER_PICK_CONFIRM), findsOneWidget);
  });

  testWidgets('removing an item drops its row', (tester) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    await tester.tap(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM).first);
    await tester.pumpAndSettle();

    expect(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM), findsNothing);
  });

  testWidgets('the sole remaining row offers no remove', (tester) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    await tester.tap(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM).first);
    await tester.pumpAndSettle();

    expect(
      find.byTooltip(AppStrings.ORDER_REMOVE_ITEM),
      findsNothing,
      reason: 'an order keeps at least one line',
    );
  });

  testWidgets('edit mode keeps the compact row with a stepper', (
    tester,
  ) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    expect(find.byIcon(Icons.add_rounded), findsWidgets);
    expect(find.byIcon(Icons.remove_rounded), findsWidgets);
    expect(find.text(AppStrings.ORDER_QUANTITY_LABEL), findsNothing);
  });

  testWidgets('the stepper raises the quantity', (tester) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    final Finder stepperCount = find.descendant(
      of: find.ancestor(
        of: find.byIcon(Icons.add_rounded).first,
        matching: find.byType(Row),
      ).first,
      matching: find.byType(Text),
    );

    expect(tester.widget<Text>(stepperCount.first).data, '1');

    await tester.tap(find.byIcon(Icons.add_rounded).first);
    await tester.pumpAndSettle();

    expect(tester.widget<Text>(stepperCount.first).data, '2');
  });

  testWidgets('the order summary shows only on the closing step', (
    tester,
  ) async {
    await _pump(tester);
    expect(find.text('Saiseeds'), findsNothing);

    await _goToItems(tester);
    expect(find.text('Saiseeds'), findsNothing);

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text('Saiseeds'), findsOneWidget);
    expect(find.text(AppStrings.ORDER_TOTAL_AMOUNT_LABEL), findsOneWidget);
  });

  testWidgets('the summary closes the delivery step', (tester) async {
    await _pump(tester);
    await _goToDelivery(tester);

    final Rect address = tester.getRect(
      find.text(AppStrings.ORDER_DELIVERY_ADDRESS_LABEL),
    );
    final Rect summary = tester.getRect(find.text('Saiseeds'));

    expect(
      summary.top,
      greaterThan(address.top),
      reason: 'the summary sits below the delivery fields',
    );
  });

  testWidgets('the summary totals follow the draft, not the server', (
    tester,
  ) async {
    await _pump(tester, mode: RecordDialogMode.edit);

    // Server totals: 9,800 across 60 packets in 2 items.
    await _goToItems(tester);
    await tester.tap(find.byIcon(Icons.add_rounded).first);
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('9,800'),
      findsNothing,
      reason: 'the stale server total must not survive an edit',
    );
    expect(find.textContaining('14,600'), findsOneWidget);
    expect(find.text('100'), findsOneWidget);
  });

  testWidgets('removing a line lowers the summary item count', (tester) async {
    await _pump(tester, mode: RecordDialogMode.edit);
    await _goToItems(tester);

    await tester.tap(find.byTooltip(AppStrings.ORDER_REMOVE_ITEM).first);
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();

    expect(find.text('1'), findsWidgets);
    expect(find.textContaining('9,800'), findsNothing);
  });

  testWidgets('view mode keeps the server totals', (tester) async {
    await _pump(tester);
    await _goToDelivery(tester);

    expect(find.textContaining('9,800'), findsOneWidget);
    expect(find.text('60'), findsOneWidget);
  });

  testWidgets('the order dialog is roomier than the shared default', (
    tester,
  ) async {
    await _pump(tester);

    final Size card = tester.getSize(_card());

    expect(
      card.width,
      greaterThanOrEqualTo(
        AppSizes.recordDialogTwoColumnWidth + AppSizes.recordDialogRoomyBump,
      ),
    );
  });
}
