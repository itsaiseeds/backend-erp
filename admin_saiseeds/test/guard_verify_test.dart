import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/routing/app_router.dart';
import 'package:admin_saiseeds/core/routing/route_constants.dart';
import 'package:admin_saiseeds/core/services/session_guard.dart';
import 'package:admin_saiseeds/features/auth/presentation/login_screen.dart';
import 'package:admin_saiseeds/features/dashboard/presentation/dashboard_screen.dart';
import 'package:admin_saiseeds/main.dart';

void _sizeTo(WidgetTester tester, double width, double height) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, height);
  addTearDown(tester.view.reset);
}

Future<void> _boot(WidgetTester tester) async {
  await SessionGuard.refresh();
  AppRouter.router.go(Routes.DASHBOARD);
  await tester.pumpWidget(const AdminSaiseedsApp());
  await tester.pumpAndSettle();
}

void _respondWith(int statusCode, {dynamic data}) {
  SessionGuard.prober = (_) async =>
      ApiProbeResult(statusCode: statusCode, data: data);
}

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000');
  });

  tearDown(() => SessionGuard.prober = null);

  testWidgets('no session blocks dashboard and lands on login', (tester) async {
    SharedPreferences.setMockInitialValues({});
    _respondWith(401);
    _sizeTo(tester, 1600, 1000);

    await _boot(tester);

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(find.byType(DashboardScreen), findsNothing);
  });

  testWidgets('invalid session also blocks dashboard', (tester) async {
    SharedPreferences.setMockInitialValues({
      'user_name': '',
      'user_role': '',
      'user_phone_number': '',
    });
    _respondWith(401);
    _sizeTo(tester, 1600, 1000);

    await _boot(tester);

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(find.byType(DashboardScreen), findsNothing);
  });

  testWidgets('valid session renders the dashboard shell', (tester) async {
    SharedPreferences.setMockInitialValues({
      'user_name': 'Harsh Mori',
      'user_role': 'admin',
      'user_phone_number': '9876543210',
    });
    _respondWith(200);
    _sizeTo(tester, 1600, 1000);

    await _boot(tester);

    expect(find.byType(DashboardScreen), findsOneWidget);
    expect(find.byType(LoginScreen), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('dashboard has no overflow across widths', (tester) async {
    SharedPreferences.setMockInitialValues({
      'user_name': 'Harsh Mori',
      'user_role': 'admin',
      'user_phone_number': '9876543210',
    });
    _respondWith(200);

    for (final double width in <double>[1600, 1280, 1024, 900, 768, 600]) {
      _sizeTo(tester, width, 1000);
      await _boot(tester);
      expect(
        tester.takeException(),
        isNull,
        reason: 'overflow or exception at width $width',
      );
    }
  });
}
