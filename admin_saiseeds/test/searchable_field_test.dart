import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/widgets/inputs/searchable_field.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const List<String> _cities = [
  'Ahmedabad, Gujarat',
  'Rajkot, Gujarat',
  'Surat, Gujarat',
  'Pune, Maharashtra',
];

Future<List<String>> _pumpField(
  WidgetTester tester, {
  String? initial,
  List<String> items = _cities,
}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1200, 900);
  addTearDown(tester.view.reset);

  final List<String> picked = [];
  String? value = initial;

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: StatefulBuilder(
            builder: (context, setState) => SearchableField<String>(
              label: 'City',
              hintText: 'Select a city',
              value: value,
              items: items,
              itemToString: (item) => item,
              isSame: (a, b) => a == b,
              onSelected: (item) {
                picked.add(item);
                setState(() => value = item);
              },
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return picked;
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
  testWidgets('the selected value shows in the field itself', (tester) async {
    await _pumpField(tester, initial: 'Rajkot, Gujarat');

    final TextField field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text, 'Rajkot, Gujarat');
  });

  testWidgets('focusing the field opens the list', (tester) async {
    await _pumpField(tester);

    expect(find.text('Surat, Gujarat'), findsNothing);

    await _focusField(tester);

    expect(find.text('Surat, Gujarat'), findsOneWidget);
  });

  testWidgets('typing in the field filters in place', (tester) async {
    await _pumpField(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'raj');
    await tester.pumpAndSettle();

    expect(find.text('Rajkot, Gujarat'), findsOneWidget);
    expect(find.text('Surat, Gujarat'), findsNothing);
    expect(find.text('Pune, Maharashtra'), findsNothing);
  });

  testWidgets('there is no second search box inside the menu', (tester) async {
    await _pumpField(tester);
    await _focusField(tester);

    // The field is the search box; a nested one is the old popup behaviour.
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text(AppStrings.SEARCH), findsNothing);
  });

  testWidgets('matching is case-insensitive', (tester) async {
    await _pumpField(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'GUJARAT');
    await tester.pumpAndSettle();

    expect(find.text('Ahmedabad, Gujarat'), findsOneWidget);
    expect(find.text('Pune, Maharashtra'), findsNothing);
  });

  testWidgets('a term matching nothing says so', (tester) async {
    await _pumpField(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'zzzz');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.NO_RESULTS_FOUND), findsOneWidget);
  });

  testWidgets('clicking an option selects it and fills the field', (
    tester,
  ) async {
    final List<String> picked = await _pumpField(tester);
    await _focusField(tester);

    await _clickOption(tester, 'Surat, Gujarat');

    expect(picked, ['Surat, Gujarat']);
    final TextField field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text, 'Surat, Gujarat');
  });

  testWidgets('arrow down then Enter picks the first match', (tester) async {
    final List<String> picked = await _pumpField(tester);
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'pune');
    await tester.pumpAndSettle();

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
    await tester.pumpAndSettle();
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();

    expect(picked, ['Pune, Maharashtra']);
  });

  testWidgets('typing without picking restores the selected value', (
    tester,
  ) async {
    await _pumpField(tester, initial: 'Rajkot, Gujarat');
    await _focusField(tester);

    await tester.enterText(find.byType(TextField), 'half typed');
    await tester.pumpAndSettle();

    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();

    final TextField field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text, 'Rajkot, Gujarat');
  });

  testWidgets('an empty source disables the field', (tester) async {
    await _pumpField(tester, items: const []);

    final TextField field = tester.widget<TextField>(find.byType(TextField));
    expect(field.enabled, isFalse);
  });
}
