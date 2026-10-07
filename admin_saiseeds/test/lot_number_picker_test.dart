import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/inputs/lot_number_picker_field.dart';
import 'package:admin_saiseeds/features/dispatch_challans/data/models/dispatch_lot_number_model.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const String _productName = 'SAI-33';

const List<DispatchLotNumberModel> _lots = [
  DispatchLotNumberModel(
    lotNumber: 'LOT-001',
    productName: _productName,
    lastUsedAt: '2026-10-01T00:00:00Z',
  ),
  DispatchLotNumberModel(
    lotNumber: 'LOT-002',
    productName: _productName,
    lastUsedAt: '2026-10-03T00:00:00Z',
  ),
  DispatchLotNumberModel(
    lotNumber: 'LOT-003',
    productName: _productName,
    lastUsedAt: '2026-10-02T00:00:00Z',
  ),
  // A different product's lot -- present in the same API response, but must
  // never show up in a picker scoped to _productName.
  DispatchLotNumberModel(
    lotNumber: 'OTHER-LOT',
    productName: 'SAI-3353',
    lastUsedAt: '2026-10-04T00:00:00Z',
  ),
];

class _Harness {
  _Harness(this.picked, this.free);

  final List<DispatchLotNumberModel> picked;
  final List<String> free;
}

Future<_Harness> _pumpPicker(
  WidgetTester tester, {
  List<DispatchLotNumberModel> lots = _lots,
  String productName = _productName,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1200, 900);
  addTearDown(tester.view.reset);

  final _Harness harness = _Harness([], []);
  DispatchLotNumberModel? value;

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: StatefulBuilder(
            builder: (context, setState) => LotNumberPickerField(
              value: value,
              lotNumbers: lots,
              productName: productName,
              productPackagingName: productName,
              onSelected: (lot) {
                harness.picked.add(lot);
                setState(() => value = lot);
              },
              onFreeEntry: (typed) {
                harness.free.add(typed);
                setState(
                  () => value = DispatchLotNumberModel(lotNumber: typed),
                );
              },
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return harness;
}

Future<void> _focusField(WidgetTester tester) async {
  await tester.tap(find.byType(TextField));
  await tester.pumpAndSettle();
}

Future<void> _clickOption(WidgetTester tester, String label) async {
  final TestGesture gesture = await tester.createGesture(
    kind: PointerDeviceKind.mouse,
  );
  await gesture.down(tester.getCenter(find.text(label).last));
  await tester.pump();
  await gesture.up();
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('recent lot numbers are listed when the field is focused', (
    tester,
  ) async {
    await _pumpPicker(tester);
    expect(find.text('LOT-001'), findsNothing);

    await _focusField(tester);

    expect(find.text('LOT-001'), findsOneWidget);
    expect(find.text('LOT-002'), findsOneWidget);
    expect(find.text('LOT-003'), findsOneWidget);
  });

  testWidgets('a lot recorded for a different product is not offered', (
    tester,
  ) async {
    await _pumpPicker(tester);
    await _focusField(tester);

    expect(find.text('OTHER-LOT'), findsNothing);
  });

  testWidgets('typing narrows the recent lot numbers', (tester) async {
    await _pumpPicker(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'LOT-003');
    await tester.pumpAndSettle();

    expect(find.text('LOT-003'), findsWidgets);
    expect(find.text('LOT-001'), findsNothing);
  });

  testWidgets('picking a recent lot reports it as a selection', (tester) async {
    final _Harness harness = await _pumpPicker(tester);
    await _focusField(tester);

    await _clickOption(tester, 'LOT-002');

    expect(harness.picked.single.lotNumber, 'LOT-002');
    expect(harness.free, isEmpty);
  });

  testWidgets('an unknown value offers an add-new row carrying the text', (
    tester,
  ) async {
    final _Harness harness = await _pumpPicker(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'LOT-999');
    await tester.pumpAndSettle();

    expect(harness.picked, isEmpty);
    expect(harness.free, isEmpty);
    expect(find.byIcon(Icons.add_rounded), findsOneWidget);

    await _clickOption(tester, 'LOT-999');

    expect(harness.free, ['LOT-999']);
    expect(harness.picked, isEmpty);
  });

  testWidgets('add-new is not offered when the value already exists', (
    tester,
  ) async {
    await _pumpPicker(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'lot-002');
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.add_rounded), findsNothing);
  });

  testWidgets('enter on a typed new value commits it as add-new', (
    tester,
  ) async {
    final _Harness harness = await _pumpPicker(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'LOT-777');
    await tester.pumpAndSettle();
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();

    expect(harness.free, ['LOT-777']);
  });

  testWidgets('enter on an exact match selects the existing lot', (
    tester,
  ) async {
    final _Harness harness = await _pumpPicker(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'LOT-001');
    await tester.pumpAndSettle();
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();

    expect(harness.picked.single.lotNumber, 'LOT-001');
    expect(harness.free, isEmpty);
  });

  testWidgets('with no recent lots the field still accepts a new value', (
    tester,
  ) async {
    final _Harness harness = await _pumpPicker(tester, lots: const []);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'LOT-001');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.NO_RESULTS_FOUND), findsNothing);
    expect(find.byIcon(Icons.add_rounded), findsOneWidget);

    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();

    expect(harness.free, ['LOT-001']);
  });

  testWidgets('a committed value shows in the field itself', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(1200, 900);
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LotNumberPickerField(
            value: const DispatchLotNumberModel(lotNumber: 'LOT-042'),
            lotNumbers: _lots,
            productName: _productName,
            productPackagingName: _productName,
            onSelected: (_) {},
            onFreeEntry: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final TextField field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text, 'LOT-042');
  });

  testWidgets('the hint reads as pick-or-type', (tester) async {
    await _pumpPicker(tester);

    expect(find.text(AppStrings.FIELD_LOT_NUMBER_RECENT_HINT), findsOneWidget);
  });
}
