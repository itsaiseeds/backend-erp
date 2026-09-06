import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/routing/app_router.dart';
import 'package:admin_saiseeds/core/routing/route_constants.dart';
import 'package:admin_saiseeds/core/services/session_guard.dart';
import 'package:admin_saiseeds/features/profile/presentation/profile_screen.dart';
import 'package:admin_saiseeds/main.dart';

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000');
  });

  tearDown(() => SessionGuard.prober = null);

  testWidgets('profile renders without overflow across widths', (tester) async {
    SharedPreferences.setMockInitialValues({
      'user_name': 'admin',
      'user_role': 'superuser',
      'user_phone_number': '9999999999',
      'can_create_admin': true,
      'can_create_sales_person': true,
    });
    SessionGuard.prober = (_) async => const ApiProbeResult(
      statusCode: 200,
      data: {
        'user': {
          'id': 1,
          'name': 'admin',
          'phone_number': '9999999999',
          'role': 'superuser',
        },
        'can_create_admin': true,
        'can_create_sales_person': true,
      },
    );

    for (final double width in <double>[
      1920,
      1600,
      1440,
      1280,
      1024,
      900,
      768,
    ]) {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = Size(width, 1000);
      addTearDown(tester.view.reset);

      await SessionGuard.refresh();
      AppRouter.router.go('${Routes.DASHBOARD}?tab=profile');
      await tester.pumpWidget(const AdminSaiseedsApp());
      await tester.pumpAndSettle();

      expect(
        find.byType(ProfileScreen),
        findsOneWidget,
        reason: 'profile did not render at $width',
      );
      expect(
        tester.takeException(),
        isNull,
        reason: 'overflow or exception at width $width',
      );
    }
  });
}
