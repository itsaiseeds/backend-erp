import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/core/models/created_by_model.dart';
import 'package:admin_saiseeds/features/admins/data/models/admin_model.dart';
import 'package:admin_saiseeds/features/admins/presentation/widgets/admin_record_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

const AdminModel _admin = AdminModel(
  id: '1',
  name: 'Sales Admin User',
  email: 'admin@example.com',
  phoneNumber: '9265319363',
  role: 'admin',
  canUpdateStockCount: true,
  createdBy: CreatedByModel(id: 1, name: 'Superuser'),
  createdAt: '2026-09-14T22:52:00+05:30',
  provisioningUri: 'otpauth://totp/Saiseeds:9265319363?secret=JBSWY3DPEHPK3PXP',
);

const List<String> _labels = [
  'Name',
  'Email (optional)',
  'Phone Number',
  'Role',
  'Stock Access',
  'Created By',
  'Created At',
];

Future<void> _pump(WidgetTester tester, RecordDialogMode mode) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Scaffold(
          body: AdminRecordDialog(admin: _admin, initialMode: mode),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('every admin field is present in both modes', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    for (final String label in _labels) {
      expect(find.text(label), findsOneWidget, reason: '$label missing in view');
    }

    await _pump(tester, RecordDialogMode.edit);
    for (final String label in _labels) {
      expect(find.text(label), findsOneWidget, reason: '$label missing in edit');
    }
  });

  testWidgets('admin field positions do not shift between modes', (
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

  testWidgets('the authenticator column renders in both modes', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    final Rect viewAside = tester.getRect(
      find.text(AppStrings.DETAIL_SECTION_AUTHENTICATOR),
    );

    await _pump(tester, RecordDialogMode.edit);

    expect(
      tester.getRect(find.text(AppStrings.DETAIL_SECTION_AUTHENTICATOR)),
      viewAside,
    );
  });

  testWidgets('view mode is read-only and offers the edit affordance', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
      expect(field.isMuted, isTrue);
    }
    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    expect(find.text(AppStrings.UPDATE), findsNothing);
  });

  testWidgets('edit mode opens only the writable admin fields', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    final Map<String, bool> mutedByLabel = {
      for (final AppTextField field in tester.widgetList<AppTextField>(
        find.byType(AppTextField),
      ))
        field.label!: field.isMuted,
    };

    expect(mutedByLabel['Name'], isFalse);
    expect(mutedByLabel['Email (optional)'], isFalse);
    expect(mutedByLabel['Phone Number'], isFalse);

    expect(mutedByLabel['Role'], isTrue);
    expect(mutedByLabel['Stock Access'], isTrue);
    expect(mutedByLabel['Created By'], isTrue);
    expect(mutedByLabel['Created At'], isTrue);
  });

  testWidgets('entering edit mode from the header keeps the layout still', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);
    final Map<String, Rect> before = {
      for (final String label in _labels)
        label: tester.getRect(find.text(label)),
    };

    await tester.tap(find.byIcon(Icons.edit_outlined));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.UPDATE), findsOneWidget);
    expect(find.text(AppStrings.CANCEL), findsOneWidget);
    for (final String label in _labels) {
      expect(tester.getRect(find.text(label)), before[label], reason: label);
    }
  });

  testWidgets('cancelling returns to a read-only view', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.CANCEL));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.UPDATE), findsNothing);
    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
    }
  });
}
