import 'package:admin_saiseeds/core/models/sidebar_item_model.dart';
import 'package:admin_saiseeds/core/theme/app_colors.dart';
import 'package:admin_saiseeds/core/widgets/layout/app_sidebar.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const List<SidebarItemModel> _items = [
  SidebarItemModel(
    id: 'dashboard',
    label: 'Dashboard',
    icon: Icons.space_dashboard_outlined,
  ),
  SidebarItemModel(
    id: 'clients',
    label: 'Clients',
    icon: Icons.storefront_outlined,
  ),
  SidebarItemModel(
    id: 'orders',
    label: 'Order Management',
    icon: Icons.receipt_long_outlined,
  ),
];

Future<void> _pumpSidebar(WidgetTester tester) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1400, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: AppSidebar(
          items: _items,
          activeItemId: 'dashboard',
          onItemSelected: (_) {},
          profileCard: const SizedBox(height: 60),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Color? _fillOf(WidgetTester tester, String label) {
  final AnimatedContainer container = tester.widget<AnimatedContainer>(
    find
        .ancestor(
          of: find.text(label),
          matching: find.byType(AnimatedContainer),
        )
        .last,
  );
  return (container.decoration as BoxDecoration?)?.color;
}

bool _isHovered(WidgetTester tester, String label) =>
    _fillOf(tester, label) == AppColors.SIDEBAR_ITEM_HOVER;

void main() {
  testWidgets('hovering an item tints it', (tester) async {
    await _pumpSidebar(tester);

    final TestGesture gesture = await tester.createGesture(
      kind: PointerDeviceKind.mouse,
    );
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);

    await gesture.moveTo(tester.getCenter(find.text('Clients')));
    await tester.pumpAndSettle();

    expect(_isHovered(tester, 'Clients'), isTrue);
  });

  testWidgets('the gap between two items is not dead space', (tester) async {
    await _pumpSidebar(tester);

    final TestGesture gesture = await tester.createGesture(
      kind: PointerDeviceKind.mouse,
    );
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);

    final Rect clients = tester.getRect(
      find
          .ancestor(
            of: find.text('Clients'),
            matching: find.byType(AnimatedContainer),
          )
          .last,
    );
    final Rect orders = tester.getRect(
      find
          .ancestor(
            of: find.text('Order Management'),
            matching: find.byType(AnimatedContainer),
          )
          .last,
    );

    // A pointer travelling down the list must always be over some item;
    // any unclaimed strip between them reads as a hover flicker.
    expect(orders.top, lessThanOrEqualTo(clients.bottom + 1.0));
  });

  testWidgets('sliding from one item to the next keeps one of them lit', (
    tester,
  ) async {
    await _pumpSidebar(tester);

    final TestGesture gesture = await tester.createGesture(
      kind: PointerDeviceKind.mouse,
    );
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);

    final Offset start = tester.getCenter(find.text('Clients'));
    final Offset end = tester.getCenter(find.text('Order Management'));

    await gesture.moveTo(start);
    await tester.pumpAndSettle();

    final int steps = (end.dy - start.dy).round().abs();
    for (int i = 1; i <= steps; i++) {
      await gesture.moveTo(Offset(start.dx, start.dy + i));
      await tester.pump();

      final bool anyLit =
          _isHovered(tester, 'Clients') ||
          _isHovered(tester, 'Order Management');
      expect(
        anyLit,
        isTrue,
        reason: 'hover dropped out ${i}px into the travel',
      );
    }
  });
}
