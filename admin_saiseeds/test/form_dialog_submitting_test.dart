import 'package:admin_saiseeds/core/widgets/dialogs/app_form_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _pump(WidgetTester tester, {required bool isSubmitting}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AppFormDialog(
          icon: Icons.groups_outlined,
          title: 'Add Sales Person',
          subtitle: 'Register a field sales account on the platform.',
          submitLabel: 'Create',
          isSubmitting: isSubmitting,
          onSubmit: isSubmitting ? null : () {},
          content: const SizedBox(height: 120),
        ),
      ),
    ),
  );

  if (isSubmitting) {
    await tester.pump(const Duration(milliseconds: 100));
    return;
  }
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the close button shows while the form is idle', (tester) async {
    await _pump(tester, isSubmitting: false);

    expect(find.byIcon(Icons.close_rounded), findsOneWidget);
  });

  testWidgets('the close button disappears while creating', (tester) async {
    await _pump(tester, isSubmitting: true);

    expect(find.byIcon(Icons.close_rounded), findsNothing);
  });

  testWidgets('an in-flight create cannot be dismissed', (tester) async {
    await _pump(tester, isSubmitting: true);

    expect(
      find.descendant(
        of: find.byType(AppFormDialog),
        matching: find.byWidgetPredicate(
          (widget) => widget is PopScope && widget.canPop == false,
        ),
      ),
      findsOneWidget,
    );
  });

  testWidgets('an idle form stays dismissable', (tester) async {
    await _pump(tester, isSubmitting: false);

    expect(
      find.descendant(
        of: find.byType(AppFormDialog),
        matching: find.byWidgetPredicate(
          (widget) => widget is PopScope && widget.canPop == true,
        ),
      ),
      findsOneWidget,
    );
  });
}
