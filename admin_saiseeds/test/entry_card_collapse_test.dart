import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/clients/presentation/widgets/client_form_steps.dart';

void main() {
  testWidgets('collapsed card hides its body and shows the summary',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: EntryCard(
            key: ValueKey('collapsed'),
            title: 'Addresses 1',
            summary: 'Shop, Line 1, Ahmedabad',
            initiallyExpanded: false,
            child: Text('body field'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Shop, Line 1, Ahmedabad'), findsOneWidget);

    final double collapsedHeight =
        tester.getSize(find.byType(EntryCard)).height;

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: EntryCard(
            key: ValueKey('expanded'),
            title: 'Addresses 1',
            summary: 'Shop, Line 1, Ahmedabad',
            child: Text('body field'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final double expandedHeight = tester.getSize(find.byType(EntryCard)).height;

    expect(
      collapsedHeight,
      lessThan(expandedHeight),
      reason: 'collapsed card must be shorter than the expanded one',
    );
  });

  testWidgets('tapping the header expands the card', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: EntryCard(
            title: 'Addresses 1',
            summary: 'Shop, Line 1',
            initiallyExpanded: false,
            child: Text('body field'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Addresses 1'));
    await tester.pumpAndSettle();

    expect(tester.getSize(find.text('body field')).height, greaterThan(0));
    expect(find.text('Shop, Line 1'), findsNothing,
        reason: 'summary is replaced by the body when expanded');
  });

  testWidgets('expanded card shows its body immediately', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: EntryCard(
            title: 'Addresses 1',
            child: Text('body field'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.getSize(find.text('body field')).height, greaterThan(0));
  });
}
