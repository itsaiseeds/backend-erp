import 'package:dio/dio.dart';
import 'package:admin_saiseeds/features/orders/presentation/bloc/orders_cubit.dart';
import 'package:admin_saiseeds/features/orders/data/orders_repository.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/buttons/primary_button.dart';
import 'package:admin_saiseeds/core/widgets/buttons/secondary_button.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/theme/app_colors.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_form_dialog.dart';
import 'package:admin_saiseeds/core/widgets/feedback/form_step_indicator.dart';
import 'package:admin_saiseeds/core/widgets/feedback/section_title.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_detail_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

final OrderModel _order = OrderModel(
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
  itemCount: 2,
  packagings: const [
    OrderPackagingModel(
      publicId: 'PP-1',
      productName: 'SAI-33',
      packetWeight: 1,
      packets: 40,
      totalWeight: 40,
      sellingPrice: 4800,
      negotiatedSellingPrice: 4800,
      quantity: 1,
    ),
  ],
);

Future<void> _pumpDialog(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1400, 1200);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () => OrderDetailDialog.show(context, _order, cubit: _cubit()),
            child: const Text('open'),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
}

Future<void> _tapNext(WidgetTester tester) async {
  await tester.tap(find.text(AppStrings.STEP_NEXT));
  await tester.pumpAndSettle();
}

double _cardWidth(WidgetTester tester) => tester
    .getSize(
      find
          .descendant(
            of: find.byType(AppRecordDialog),
            matching: find.byType(ConstrainedBox),
          )
          .first,
    )
    .width;

OrdersCubit _cubit() =>
    OrdersCubit(repository: OrdersRepository(apiClient: ApiClient(dio: Dio())));

void main() {
  testWidgets('the header is a full-bleed accent bar', (tester) async {
    await _pumpDialog(tester);

    final Container header = tester.widget<Container>(
      find
          .descendant(
            of: find.byType(AppDialogHeader),
            matching: find.byType(Container),
          )
          .first,
    );
    expect(header.color, AppColors.PRIMARY);

    final Text title = tester.widget<Text>(
      find.text(AppStrings.ORDER_DETAILS_TITLE),
    );
    expect(title.style?.color, AppColors.WHITE);
  });

  testWidgets('the subtitle names the step, as the reference does', (
    tester,
  ) async {
    await _pumpDialog(tester);
    expect(find.textContaining('Step 1'), findsOneWidget);

    await _tapNext(tester);
    expect(find.textContaining('Step 2'), findsOneWidget);
    expect(find.textContaining('Step 1'), findsNothing);
  });

  testWidgets('each step is headed by an icon and a rule', (tester) async {
    await _pumpDialog(tester);

    expect(find.byType(SectionTitle), findsOneWidget);
    expect(
      find.descendant(
        of: find.byType(SectionTitle),
        matching: find.byType(Divider),
      ),
      findsOneWidget,
    );
  });

  testWidgets('there is no step indicator, only the buttons', (tester) async {
    await _pumpDialog(tester);

    // The Back/Next pair is the navigation; a numbered rail duplicates it.
    expect(find.byType(FormStepIndicator), findsNothing);
    expect(find.text(AppStrings.STEP_NEXT), findsOneWidget);
  });

  testWidgets('the current step is named above its content', (tester) async {
    await _pumpDialog(tester);
    expect(find.text(AppStrings.ORDER_STEP_SUMMARY), findsOneWidget);

    await _tapNext(tester);
    // "Items" is also a metric label, so the summary title going away is the
    // unambiguous signal that the heading tracks the step.
    expect(find.text(AppStrings.ORDER_STEP_SUMMARY), findsNothing);
    expect(find.text(AppStrings.ORDER_STEP_ITEMS), findsWidgets);
  });

  testWidgets('the first step offers Next and no Back', (tester) async {
    await _pumpDialog(tester);

    expect(find.text(AppStrings.STEP_NEXT), findsOneWidget);
    expect(find.text(AppStrings.STEP_BACK), findsNothing);
  });

  testWidgets('Next advances through the steps', (tester) async {
    await _pumpDialog(tester);

    await _tapNext(tester);
    expect(find.text('SAI-33'), findsOneWidget);

    await _tapNext(tester);
    expect(find.text('eywy, Rajkot, Gujarat, India'), findsOneWidget);
  });

  testWidgets('a middle step offers both Back and Next', (tester) async {
    await _pumpDialog(tester);
    await _tapNext(tester);

    expect(find.text(AppStrings.STEP_BACK), findsOneWidget);
    expect(find.text(AppStrings.STEP_NEXT), findsOneWidget);
  });

  testWidgets('Back returns to the previous step', (tester) async {
    await _pumpDialog(tester);
    await _tapNext(tester);

    await tester.tap(find.text(AppStrings.STEP_BACK));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.STEP_BACK), findsNothing);
    expect(find.text(AppStrings.ORDER_PLACED_BY_LABEL), findsOneWidget);
  });

  testWidgets('the last step offers save rather than advancing', (
    tester,
  ) async {
    await _pumpDialog(tester);
    await _tapNext(tester);
    await _tapNext(tester);

    expect(find.text(AppStrings.STEP_NEXT), findsNothing);
    expect(find.text(AppStrings.SAVE), findsOneWidget);
  });

  testWidgets('view mode cannot save from the last step', (tester) async {
    await _pumpDialog(tester);
    await _tapNext(tester);
    await _tapNext(tester);

    final PrimaryButton save = tester.widget<PrimaryButton>(
      find.byType(PrimaryButton),
    );
    expect(save.onPressed, isNull);
  });

  testWidgets('Next takes half the footer beside Cancel', (tester) async {
    await _pumpDialog(tester);

    final double buttonWidth = tester.getSize(find.byType(PrimaryButton)).width;

    // Half the card, give or take the gutter between the two buttons.
    expect(buttonWidth, greaterThan(_cardWidth(tester) * 0.4));
    expect(buttonWidth, lessThan(_cardWidth(tester) * 0.6));
  });

  testWidgets('Back and Next share the row evenly', (tester) async {
    await _pumpDialog(tester);
    await _tapNext(tester);

    final double back = tester.getSize(find.byType(SecondaryButton)).width;
    final double next = tester.getSize(find.byType(PrimaryButton)).width;

    expect(back, closeTo(next, 1.0));
    expect(back + next, greaterThan(_cardWidth(tester) * 0.7));
  });
}
