import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/routing/app_router.dart';
import 'package:admin_saiseeds/core/routing/route_constants.dart';
import 'package:admin_saiseeds/core/utils/app_scroll_behavior.dart';
import 'package:admin_saiseeds/main.dart';

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000');
  });

  test('mouse is excluded from scroll drag devices', () {
    const behavior = AppScrollBehavior();
    expect(behavior.dragDevices.contains(PointerDeviceKind.mouse), isFalse);
    expect(behavior.dragDevices.contains(PointerDeviceKind.touch), isTrue);
    expect(behavior.dragDevices.contains(PointerDeviceKind.stylus), isTrue);
    expect(behavior.dragDevices.contains(PointerDeviceKind.trackpad), isTrue);
  });

  testWidgets('app applies AppScrollBehavior globally', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 1000));
    AppRouter.router.go(Routes.LOGIN);

    await tester.pumpWidget(const AdminSaiseedsApp());
    await tester.pumpAndSettle();

    final MaterialApp app = tester.widget(find.byType(MaterialApp));
    expect(app.scrollBehavior, isA<AppScrollBehavior>());
  });

  testWidgets('routes render inside a SelectionArea', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 1000));
    AppRouter.router.go(Routes.LOGIN);

    await tester.pumpWidget(const AdminSaiseedsApp());
    await tester.pumpAndSettle();

    expect(find.byType(SelectionArea), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
