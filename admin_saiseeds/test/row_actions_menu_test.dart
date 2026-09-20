import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/buttons/row_actions_menu.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _pump(
  WidgetTester tester, {
  required List<RowAction> actions,
  bool enabled = true,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1200, 800);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Center(
          child: RowActionsMenu(actions: actions, enabled: enabled),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the row collapses to a single labelled button', (tester) async {
    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          onSelected: () {},
        ),
      ],
    );

    expect(find.text(AppStrings.TABLE_ROW_ACTIONS), findsOneWidget);
    expect(find.text(AppStrings.ORDER_VERIFY), findsNothing);
  });

  testWidgets('tapping it reveals every action by name', (tester) async {
    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          onSelected: () {},
        ),
        RowAction(
          label: AppStrings.ORDER_HOLD,
          icon: Icons.pause_circle_outline,
          onSelected: () {},
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.ORDER_VERIFY), findsOneWidget);
    expect(find.text(AppStrings.ORDER_HOLD), findsOneWidget);
  });

  testWidgets('choosing an action runs it and closes the menu', (tester) async {
    int taps = 0;

    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          onSelected: () => taps++,
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.ORDER_VERIFY));
    await tester.pumpAndSettle();

    expect(taps, 1);
    expect(find.text(AppStrings.ORDER_VERIFY), findsNothing);
  });

  testWidgets('a blocked action stays listed but inert', (tester) async {
    int taps = 0;

    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          blockedHint: AppStrings.ORDER_VERIFY_BLOCKED,
          onSelected: null,
        ),
        RowAction(
          label: AppStrings.ORDER_HOLD,
          icon: Icons.pause_circle_outline,
          onSelected: () => taps++,
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.ORDER_VERIFY), findsOneWidget);

    await tester.tap(find.text(AppStrings.ORDER_VERIFY));
    await tester.pumpAndSettle();

    expect(taps, 0, reason: 'a blocked action must not fire');
    expect(
      find.text(AppStrings.ORDER_HOLD),
      findsOneWidget,
      reason: 'the menu stays open after a blocked tap',
    );
  });

  testWidgets('a busy row cannot open the menu', (tester) async {
    await _pump(
      tester,
      enabled: false,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          onSelected: () {},
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.ORDER_VERIFY), findsNothing);
  });

  testWidgets('a blocked action explains itself inline', (tester) async {
    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          blockedHint: AppStrings.ORDER_VERIFY_BLOCKED,
          onSelected: null,
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.ORDER_VERIFY_BLOCKED), findsOneWidget);
  });

  testWidgets('an available action carries no blocked hint', (tester) async {
    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          blockedHint: AppStrings.ORDER_VERIFY_BLOCKED,
          onSelected: () {},
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.ORDER_VERIFY_BLOCKED), findsNothing);
  });

  testWidgets('tapping outside dismisses the menu', (tester) async {
    await _pump(
      tester,
      actions: [
        RowAction(
          label: AppStrings.ORDER_VERIFY,
          icon: Icons.verified_outlined,
          onSelected: () {},
        ),
      ],
    );

    await tester.tap(find.text(AppStrings.TABLE_ROW_ACTIONS));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.ORDER_VERIFY), findsOneWidget);

    await tester.tapAt(const Offset(20, 20));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.ORDER_VERIFY), findsNothing);
  });
}
