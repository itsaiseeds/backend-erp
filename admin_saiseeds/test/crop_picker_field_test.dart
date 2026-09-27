import 'package:admin_saiseeds/core/models/crop_model.dart';
import 'package:admin_saiseeds/core/widgets/inputs/crop_picker_field.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const List<CropModel> _crops = [
  CropModel(id: 1, name: 'Bajra'),
  CropModel(id: 2, name: 'Cotton'),
  CropModel(id: 3, name: 'Wheat'),
];

class _Captured {
  CropModel? selected;
  String? createRequested;
}

Future<_Captured> _pumpPicker(
  WidgetTester tester, {
  List<CropModel> crops = _crops,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1200, 900);
  addTearDown(tester.view.reset);

  final _Captured captured = _Captured();
  CropModel? value;

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: StatefulBuilder(
            builder: (context, setState) => CropPickerField(
              value: value,
              crops: crops,
              onSelected: (crop) {
                captured.selected = crop;
                setState(() => value = crop);
              },
              onCreateRequested: (name) => captured.createRequested = name,
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return captured;
}

Future<void> _clickOption(WidgetTester tester, Finder target) async {
  final TestGesture gesture = await tester.createGesture(
    kind: PointerDeviceKind.mouse,
  );
  await gesture.down(tester.getCenter(target));
  await tester.pump();
  await gesture.up();
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('typing filters the existing crops in place', (tester) async {
    await _pumpPicker(tester);

    await tester.tap(find.byType(TextField));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'cot');
    await tester.pumpAndSettle();

    expect(find.text('Cotton'), findsOneWidget);
    expect(find.text('Bajra'), findsNothing);
  });

  testWidgets('an unmatched term offers to create that crop', (tester) async {
    final _Captured captured = await _pumpPicker(tester);

    await tester.tap(find.byType(TextField));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Maize');
    await tester.pumpAndSettle();

    final Finder createRow = find.textContaining('Create crop');
    expect(createRow, findsOneWidget);

    await _clickOption(tester, createRow);

    expect(captured.createRequested, 'Maize');
    expect(captured.selected, isNull);
  });

  testWidgets('an exact match offers no create option', (tester) async {
    await _pumpPicker(tester);

    await tester.tap(find.byType(TextField));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Wheat');
    await tester.pumpAndSettle();

    // The field itself holds the typed text, so the option is the second.
    expect(find.text('Wheat'), findsNWidgets(2));
    expect(find.textContaining('Create crop'), findsNothing);
  });

  testWidgets('picking an existing crop reports it, not a create', (
    tester,
  ) async {
    final _Captured captured = await _pumpPicker(tester);

    await tester.tap(find.byType(TextField));
    await tester.pumpAndSettle();

    await _clickOption(tester, find.text('Bajra').last);

    expect(captured.selected?.name, 'Bajra');
    expect(captured.createRequested, isNull);
  });

  testWidgets('with no crops yet the field still opens to create one', (
    tester,
  ) async {
    final _Captured captured = await _pumpPicker(tester, crops: const []);

    await tester.tap(find.byType(TextField));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Groundnut');
    await tester.pumpAndSettle();

    await _clickOption(tester, find.textContaining('Create crop'));

    expect(captured.createRequested, 'Groundnut');
  });
}
