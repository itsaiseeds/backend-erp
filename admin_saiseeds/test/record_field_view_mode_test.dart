import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/core/widgets/inputs/record_field.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

Future<void> _pumpField(
  WidgetTester tester, {
  required bool isEditable,
  bool isLocked = false,
}) async {
  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Scaffold(
          body: RecordField(
            controller: TextEditingController(text: 'Hitesh Mori'),
            label: 'Name',
            isEditable: isEditable,
            isLocked: isLocked,
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('tapping a view-mode field raises the notice', (tester) async {
    await _pumpField(tester, isEditable: false);

    await tester.tap(find.byType(TextFormField));
    await tester.pumpAndSettle();

    expect(
      tester.takeException(),
      isNull,
      reason: 'the notice is raised without throwing',
    );
    expect(find.byType(RecordField), findsOneWidget);
  });

  testWidgets('a locked field is muted even while the record is editable', (
    tester,
  ) async {
    await _pumpField(tester, isEditable: true, isLocked: true);

    final AppTextField field = tester.widget<AppTextField>(
      find.byType(AppTextField),
    );
    expect(field.readOnly, isTrue);
    expect(field.isMuted, isTrue);
    expect(field.onTap, isNotNull);
  });

  testWidgets('an editable field takes input and raises no notice', (
    tester,
  ) async {
    await _pumpField(tester, isEditable: true);

    final AppTextField field = tester.widget<AppTextField>(
      find.byType(AppTextField),
    );
    expect(field.readOnly, isFalse);
    expect(field.isMuted, isFalse);
    expect(field.onTap, isNull);
  });

  testWidgets('a view-mode field stays selectable so the value can be copied', (
    tester,
  ) async {
    await _pumpField(tester, isEditable: false);

    final AppTextField field = tester.widget<AppTextField>(
      find.byType(AppTextField),
    );
    expect(field.enabled, isTrue);
    expect(field.readOnly, isTrue);
    expect(field.isMuted, isTrue);
  });
}
