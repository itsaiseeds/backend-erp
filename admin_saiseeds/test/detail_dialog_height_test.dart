import 'package:admin_saiseeds/core/theme/app_spacing.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_detail_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const double _inset = AppSpacing.lg * 2;

Future<void> _pumpDialog(
  WidgetTester tester, {
  required Size screen,
  int rows = 40,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = screen;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) => TextButton(
            onPressed: () => showDialog<void>(
              context: context,
              builder: (_) => AppDetailDialog(
                icon: Icons.person_outline,
                title: 'Sales person details',
                subtitle: 'Identity and contact details on record.',
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (int i = 0; i < rows; i++)
                      SizedBox(height: 40, child: Text('Row $i')),
                  ],
                ),
              ),
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

double _dialogHeight(WidgetTester tester) => tester
    .getSize(
      find
          .descendant(
            of: find.byType(AppDetailDialog),
            matching: find.byType(ConstrainedBox),
          )
          .first,
    )
    .height;

void main() {
  testWidgets('a tall screen gets a taller dialog than the old 720 cap', (
    tester,
  ) async {
    await _pumpDialog(tester, screen: const Size(1600, 1080));

    // The old fixed ceiling left the QR and its actions below the fold.
    expect(_dialogHeight(tester), greaterThan(720));
  });

  testWidgets('the dialog uses the viewport height, less its inset', (
    tester,
  ) async {
    const Size screen = Size(1600, 900);
    await _pumpDialog(tester, screen: screen);

    expect(_dialogHeight(tester), closeTo(screen.height - _inset, 1.0));
  });

  testWidgets('it never grows past the maximum on a very tall screen', (
    tester,
  ) async {
    await _pumpDialog(tester, screen: const Size(1600, 1600));

    expect(_dialogHeight(tester), AppSizes.dialogMaxHeight);
  });

  testWidgets('a short screen still fits without overflowing', (tester) async {
    const Size screen = Size(1280, 600);
    await _pumpDialog(tester, screen: screen);

    expect(_dialogHeight(tester), lessThanOrEqualTo(screen.height));
    expect(tester.takeException(), isNull);
  });

  testWidgets('short content does not stretch the dialog', (tester) async {
    await _pumpDialog(tester, screen: const Size(1600, 1080), rows: 2);

    expect(_dialogHeight(tester), lessThan(720));
  });
}
