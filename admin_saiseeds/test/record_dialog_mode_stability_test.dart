import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/core/widgets/inputs/record_field.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

const List<String> _labels = [
  'Name',
  'Email (optional)',
  'Phone Number',
  'Role',
];

Widget _body(bool canEdit) {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    mainAxisSize: MainAxisSize.min,
    children: [
      for (final String label in _labels)
        RecordField(
          controller: TextEditingController(text: 'value for $label'),
          label: label,
          isEditable: canEdit,
        ),
    ],
  );
}

Future<void> _pump(
  WidgetTester tester,
  RecordDialogMode mode, {
  bool isSubmitting = false,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Scaffold(
          body: AppRecordDialog(
            icon: Icons.groups_outlined,
            title: 'Sales person details',
            subtitle: 'Identity and contact details on record.',
            mode: mode,
            body: _body(mode == RecordDialogMode.edit),
            aside: const RecordDialogAside(
              title: 'Authenticator',
              subtitle: 'Scan this code in an authenticator app.',
              child: SizedBox(height: 200, width: 200),
            ),
            isSubmitting: isSubmitting,
            onEdit: () {},
            onCancelEdit: () {},
            onSubmit: () {},
          ),
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
  testWidgets('field positions are identical in view and edit mode', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);
    final Map<String, Rect> viewRects = {
      for (final String label in _labels)
        label: tester.getRect(find.text(label)),
    };

    await _pump(tester, RecordDialogMode.edit);

    for (final String label in _labels) {
      expect(
        tester.getRect(find.text(label)),
        viewRects[label],
        reason: '$label moved when entering edit mode',
      );
    }
  });

  testWidgets('the aside stays visible in both modes', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    final Rect viewAside = tester.getRect(find.text('Authenticator'));

    await _pump(tester, RecordDialogMode.edit);

    expect(tester.getRect(find.text('Authenticator')), viewAside);
  });

  testWidgets('view mode disables every field and hides the footer', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
      expect(field.isMuted, isTrue);
      expect(field.enabled, isTrue, reason: 'stays selectable for copying');
    }
    expect(find.text(AppStrings.UPDATE), findsNothing);
  });

  testWidgets('edit mode enables the fields and shows the footer', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isFalse);
      expect(field.isMuted, isFalse);
    }
    expect(find.text(AppStrings.UPDATE), findsOneWidget);
    expect(find.text(AppStrings.CANCEL), findsOneWidget);
  });

  testWidgets('the edit affordance shows only in view mode', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);

    await _pump(tester, RecordDialogMode.edit);
    expect(find.byIcon(Icons.edit_outlined), findsNothing);
  });

  testWidgets('a view-mode field routes taps to the blocked-tap notice', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.onTap, isNotNull);
    }
  });

  testWidgets('an edit-mode field takes taps as ordinary focus', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.onTap, isNull);
    }
  });

  testWidgets('the close button disappears while the update is in flight', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.edit);
    expect(find.byIcon(Icons.close_rounded), findsOneWidget);

    await _pump(tester, RecordDialogMode.edit, isSubmitting: true);
    expect(find.byIcon(Icons.close_rounded), findsNothing);
  });

  testWidgets('an in-flight update cannot be dismissed', (tester) async {
    await _pump(tester, RecordDialogMode.edit, isSubmitting: true);

    final Finder scope = find.descendant(
      of: find.byType(AppRecordDialog),
      matching: find.byWidgetPredicate(
        (widget) => widget is PopScope && widget.canPop == false,
      ),
    );
    expect(scope, findsOneWidget);
  });

  testWidgets('the dialog leaves text selection enabled for copying', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    expect(
      find.descendant(
        of: find.byType(AppRecordDialog),
        matching: find.byType(SelectionContainer),
      ),
      findsNothing,
      reason: 'a disabled SelectionContainer would block copying',
    );
  });
}
