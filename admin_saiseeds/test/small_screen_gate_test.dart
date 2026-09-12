import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/widgets/layout/small_screen_notice.dart';

Future<void> _pumpAt(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    const MaterialApp(
      home: SmallScreenGate(child: Scaffold(body: Text('portal'))),
    ),
  );
  await tester.pump();
}

void main() {
  testWidgets('phone width shows the notice', (tester) async {
    await _pumpAt(tester, const Size(420, 900));

    expect(find.byType(SmallScreenNotice), findsOneWidget);
    expect(find.text('portal'), findsNothing);
  });

  testWidgets('just below the tablet breakpoint shows the notice',
      (tester) async {
    await _pumpAt(tester, const Size(767, 1024));

    expect(find.byType(SmallScreenNotice), findsOneWidget);
  });

  testWidgets('tablet width shows the portal', (tester) async {
    await _pumpAt(tester, const Size(768, 1024));

    expect(find.text('portal'), findsOneWidget);
    expect(find.byType(SmallScreenNotice), findsNothing);
  });

  testWidgets('desktop width shows the portal', (tester) async {
    await _pumpAt(tester, const Size(1440, 900));

    expect(find.text('portal'), findsOneWidget);
    expect(find.byType(SmallScreenNotice), findsNothing);
  });
}
