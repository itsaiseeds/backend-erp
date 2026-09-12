import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/models/sidebar_item_model.dart';
import 'package:admin_saiseeds/core/widgets/layout/app_sidebar.dart';

void main() {
  testWidgets('active item paints exactly one fill layer', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 260,
            child: SidebarItem(
              item: const SidebarItemModel(
                id: 'clients',
                label: 'Clients',
                icon: Icons.storefront_outlined,
              ),
              isActive: true,
              isCollapsed: false,
              onTap: () {},
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final containers = tester
        .widgetList<AnimatedContainer>(find.byType(AnimatedContainer))
        .toList();

    for (final c in containers) {
      final d = c.decoration as BoxDecoration?;
      debugPrint('AnimatedContainer color: ${d?.color}');
    }

    final inkWells = find.byType(InkWell).evaluate().length;
    final materials = find.byType(Material).evaluate().length;
    debugPrint('InkWell count: $inkWells');
    debugPrint('Material count: $materials');
  });
}
