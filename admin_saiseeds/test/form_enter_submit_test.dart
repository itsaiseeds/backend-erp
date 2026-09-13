import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_form_dialog.dart';

Future<int> _pressEnter(
  WidgetTester tester, {
  bool isSubmitting = false,
  bool hasHandler = true,
  bool focusField = false,
}) async {
  int calls = 0;
  final controller = TextEditingController();

  await tester.pumpWidget(
    MaterialApp(
      home: AppFormDialog(
        icon: Icons.person_outline,
        title: 'Form',
        subtitle: 'sub',
        submitLabel: 'Next',
        isSubmitting: isSubmitting,
        onSubmit: hasHandler ? () => calls++ : null,
        content: TextField(controller: controller),
      ),
    ),
  );
  await tester.pump();

  if (focusField) {
    await tester.tap(find.byType(TextField));
    await tester.pump();
  }

  await tester.sendKeyEvent(LogicalKeyboardKey.enter);
  await tester.pump();

  return calls;
}

void main() {
  testWidgets('Enter triggers submit', (tester) async {
    expect(await _pressEnter(tester), 1);
  });

  testWidgets('Enter works while a text field has focus', (tester) async {
    expect(await _pressEnter(tester, focusField: true), 1);
  });

  testWidgets('Enter is ignored while submitting', (tester) async {
    expect(await _pressEnter(tester, isSubmitting: true), 0);
  });

  testWidgets('Enter is safe when no handler is set', (tester) async {
    expect(await _pressEnter(tester, hasHandler: false), 0);
  });
}
