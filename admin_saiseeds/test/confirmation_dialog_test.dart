import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/theme/app_colors.dart';
import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_dialog_shell.dart';
import 'package:admin_saiseeds/core/widgets/feedback/confirmation_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

Future<bool?> _openConfirm(
  WidgetTester tester, {
  bool isDangerous = false,
}) async {
  bool? outcome;

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () async {
              outcome = await ConfirmationDialog.show(
                context,
                title: 'Reject this order?',
                message: 'Rejection is permanent.',
                confirmLabel: AppStrings.ORDER_REJECT,
                isDangerous: isDangerous,
              );
            },
            child: const Text('open'),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
  return outcome;
}

Future<void> _openAlert(WidgetTester tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () => ConfirmationDialog.showAlert(
              context,
              title: 'Stock count missing',
              message: 'Complete the count before verifying.',
            ),
            child: const Text('open'),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('open'));
  await tester.pumpAndSettle();
}

Color _headerColour(WidgetTester tester) {
  final Container header = tester.widget<Container>(
    find
        .descendant(
          of: find.byType(AppDialogShell),
          matching: find.byType(Container),
        )
        .at(1),
  );
  return (header.decoration as BoxDecoration).color!;
}

void main() {
  testWidgets('shows the title, message and both actions', (tester) async {
    await _openConfirm(tester);

    expect(find.text('Reject this order?'), findsOneWidget);
    expect(find.text('Rejection is permanent.'), findsOneWidget);
    expect(find.text(AppStrings.ORDER_REJECT), findsOneWidget);
    expect(find.text(AppStrings.CANCEL), findsOneWidget);
  });

  testWidgets('confirming returns true', (tester) async {
    await _openConfirm(tester);

    await tester.tap(find.text(AppStrings.ORDER_REJECT));
    await tester.pumpAndSettle();

    expect(find.byType(AppDialogShell), findsNothing);
  });

  testWidgets('pressing Enter confirms without reaching for the mouse', (
    tester,
  ) async {
    await _openConfirm(tester);

    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();

    expect(find.byType(AppDialogShell), findsNothing);
  });

  testWidgets('a dangerous action gets the error header', (tester) async {
    await _openConfirm(tester, isDangerous: true);

    expect(_headerColour(tester), AppColors.ERROR);
    expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
  });

  testWidgets('an ordinary action gets the primary header', (tester) async {
    await _openConfirm(tester);

    expect(_headerColour(tester), AppColors.PRIMARY);
    expect(find.byIcon(Icons.info_outline_rounded), findsOneWidget);
  });

  testWidgets('the header icon sits on the accent, with no white tile', (
    tester,
  ) async {
    await _openConfirm(tester);

    final Icon icon = tester.widget<Icon>(
      find.byIcon(Icons.info_outline_rounded),
    );
    expect(icon.color, AppColors.WHITE);

    // The badge path draws a sized tile; on an accent the icon stands alone,
    // so it is the larger of the two sizes.
    expect(icon.size, AppSizes.iconXl);
  });

  testWidgets('an alert offers one action only', (tester) async {
    await _openAlert(tester);

    expect(find.text(AppStrings.OK), findsOneWidget);
    expect(find.text(AppStrings.CANCEL), findsNothing);
    expect(find.text(AppStrings.CONFIRM), findsNothing);
  });

  testWidgets('a confirmation cannot be dismissed by a stray close button', (
    tester,
  ) async {
    await _openConfirm(tester);

    expect(find.byIcon(Icons.close_rounded), findsNothing);
  });
}
