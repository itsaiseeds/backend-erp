import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/dialogs/app_record_dialog.dart';
import 'package:admin_saiseeds/core/widgets/inputs/app_text_field.dart';
import 'package:admin_saiseeds/features/product_packagings/data/models/product_packaging_model.dart';
import 'package:admin_saiseeds/features/product_packagings/presentation/widgets/product_packaging_record_dialog.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:toastification/toastification.dart';

const ProductPackagingModel _packaging = ProductPackagingModel(
  publicId: 'PP-0001',
  product: PackagingProductRef(publicId: 'P-0001', name: 'SAI-33'),
  packetWeight: '1',
  packets: 20,
  totalWeight: '20',
  sellingPrice: '2400',
);

const List<String> _labels = [
  AppStrings.FIELD_PACKET_WEIGHT,
  AppStrings.FIELD_PACKETS,
  AppStrings.FIELD_BAG_SELLING_PRICE,
  AppStrings.COLUMN_TOTAL_WEIGHT,
];

Future<void> _pump(WidgetTester tester, RecordDialogMode mode) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1440, 900);
  addTearDown(tester.view.reset);

  // Opened as a real route: a bare Scaffold child ignores Dialog.alignment,
  // which is what keeps the card anchored when the footer appears.
  await tester.pumpWidget(
    ToastificationWrapper(
      child: MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  barrierDismissible: false,
                  builder: (_) => ProductPackagingRecordDialog(
                    packaging: _packaging,
                    initialMode: mode,
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

void main() {
  testWidgets('view and edit share one title', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    expect(find.text(AppStrings.PRODUCT_PACKAGING_DETAIL_TITLE), findsOneWidget);

    await _pump(tester, RecordDialogMode.edit);
    expect(find.text(AppStrings.PRODUCT_PACKAGING_DETAIL_TITLE), findsOneWidget);
  });

  testWidgets('every field is present in both modes', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    for (final String label in _labels) {
      expect(find.text(label), findsOneWidget, reason: '$label missing in view');
    }

    await _pump(tester, RecordDialogMode.edit);
    for (final String label in _labels) {
      expect(find.text(label), findsOneWidget, reason: '$label missing in edit');
    }
  });

  testWidgets('field positions do not shift between modes', (tester) async {
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

  testWidgets('edit mode opens the writable fields only', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    final Map<String, bool> mutedByLabel = {
      for (final AppTextField field in tester.widgetList<AppTextField>(
        find.byType(AppTextField),
      ))
        if (field.label != null && field.label!.isNotEmpty)
          field.label!: field.isMuted,
    };

    expect(mutedByLabel[AppStrings.FIELD_PACKET_WEIGHT], isFalse);
    expect(mutedByLabel[AppStrings.FIELD_PACKETS], isFalse);
    expect(mutedByLabel[AppStrings.FIELD_BAG_SELLING_PRICE], isFalse);

    expect(
      mutedByLabel[AppStrings.COLUMN_TOTAL_WEIGHT],
      isTrue,
      reason: 'total weight is derived, never typed',
    );

    expect(find.text(AppStrings.UPDATE), findsOneWidget);
    expect(find.text(AppStrings.CANCEL), findsOneWidget);
    expect(find.byIcon(Icons.edit_outlined), findsNothing);
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

    for (final String label in _labels) {
      expect(tester.getRect(find.text(label)), before[label], reason: label);
    }
  });

  testWidgets('the selected product sits in its own third column', (
    tester,
  ) async {
    await _pump(tester, RecordDialogMode.view);

    expect(
      find.text(AppStrings.SELECTED_PRODUCT_SUMMARY_TITLE),
      findsOneWidget,
    );

    final Rect summary = tester.getRect(
      find.text(AppStrings.SELECTED_PRODUCT_SUMMARY_TITLE),
    );
    final Rect packets = tester.getRect(find.text(AppStrings.FIELD_PACKETS));

    expect(
      summary.left,
      greaterThan(packets.right),
      reason: 'the summary belongs to the right of the field columns',
    );
  });

  testWidgets('the summary column survives the mode switch', (tester) async {
    await _pump(tester, RecordDialogMode.view);
    final Rect before = tester.getRect(
      find.text(AppStrings.SELECTED_PRODUCT_SUMMARY_TITLE),
    );

    await tester.tap(find.byIcon(Icons.edit_outlined));
    await tester.pumpAndSettle();

    expect(
      tester.getRect(find.text(AppStrings.SELECTED_PRODUCT_SUMMARY_TITLE)),
      before,
    );
  });

  testWidgets('total weight recomputes when packets change', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    final Finder totalWeight = find.ancestor(
      of: find.text(AppStrings.COLUMN_TOTAL_WEIGHT),
      matching: find.byType(Column),
    );
    expect(totalWeight, findsWidgets);

    // Seeded: 1 kg x 20 packets = 20.
    expect(find.text('20'), findsWidgets);

    await tester.enterText(
      find.widgetWithText(TextFormField, '20').first,
      '30',
    );
    await tester.pumpAndSettle();

    // 1 kg x 30 packets = 30; the fetched 20 must not survive.
    final Iterable<TextFormField> fields = tester
        .widgetList<TextFormField>(find.byType(TextFormField));
    final List<String> values = [
      for (final field in fields) field.controller?.text ?? '',
    ];
    expect(values, contains('30'));
  });

  testWidgets('cancelling returns to a read-only view', (tester) async {
    await _pump(tester, RecordDialogMode.edit);

    await tester.tap(find.text(AppStrings.CANCEL));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    for (final AppTextField field in tester.widgetList<AppTextField>(
      find.byType(AppTextField),
    )) {
      expect(field.readOnly, isTrue);
    }
  });
}
