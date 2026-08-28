// Basic smoke test for the Saiseeds TOTP login screen.
//
// It only verifies the login UI renders; the live sign-in flow hits the real
// backend and is covered by integration tests on the server side.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:admin_web/main.dart';

void main() {
  testWidgets('Login screen renders', (WidgetTester tester) async {
    await tester.pumpWidget(const SaiSeedsApp());

    expect(find.text('Saiseeds Admin'), findsOneWidget);
    expect(find.text('Phone number'), findsOneWidget);
    expect(find.text('6-digit code'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);
  });
}
