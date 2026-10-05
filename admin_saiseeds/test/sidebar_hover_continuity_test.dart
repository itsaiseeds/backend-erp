import 'package:admin_saiseeds/core/models/sidebar_workspace_model.dart';
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

// The hover behaviour under test belongs to the rows, so every item sits in
// one workspace and the switcher stays out of the way.
const SidebarGroupModel _group = SidebarGroupModel(
  id: 'ops-all',
  itemIds: ['dashboard', 'clients', 'orders'],
);

const SidebarWorkspaceModel _workspace = SidebarWorkspaceModel(
  id: 'operations',
  label: 'Operations',
  hint: 'Day-to-day work',
  icon: Icons.bolt_outlined,
  groups: [_group],
);

final List<ResolvedSidebarWorkspace> _workspaces = [
  ResolvedSidebarWorkspace(
    workspace: _workspace,
    groups: [ResolvedSidebarGroup(group: _group, items: _items)],
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
          workspaces: _workspaces,
          activeWorkspaceId: 'operations',
          activeItemId: 'dashboard',
          onItemSelected: (_) {},
          onWorkspaceSelected: (_) {},
          profileCard: const SizedBox(height: 60),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

// Hover is signalled by the label colour, not a background fill: the row
// stays flat and only its text and icon brighten.
bool _isHovered(WidgetTester tester, String label) {
  final AnimatedDefaultTextStyle styled = tester
      .widget<AnimatedDefaultTextStyle>(
        find
            .ancestor(
              of: find.text(label),
              matching: find.byType(AnimatedDefaultTextStyle),
            )
            .first,
      );
  return styled.style.color == AppColors.SIDEBAR_TEXT_ACTIVE;
}

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
