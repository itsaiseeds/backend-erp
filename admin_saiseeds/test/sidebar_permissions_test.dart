import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/constants/tab_ids.dart';
import 'package:admin_saiseeds/core/constants/user_roles.dart';
import 'package:admin_saiseeds/features/dashboard/data/sidebar_items.dart';

void main() {
  List<String> idsFor(String? role) =>
      SidebarItems.visibleItems(role: role).map((item) => item.id).toList();

  test('a superuser sees every tab', () {
    expect(idsFor(UserRoles.SUPERUSER), [
      TabIds.DASHBOARD,
      TabIds.ADMINS,
      TabIds.SALES_PEOPLE,
      TabIds.PRODUCTS,
      TabIds.PRODUCT_PACKAGINGS,
    ]);
  });

  test('an admin sees every tab except admins', () {
    final ids = idsFor(UserRoles.ADMIN);

    expect(ids.contains(TabIds.ADMINS), isFalse);
    expect(ids, [
      TabIds.DASHBOARD,
      TabIds.SALES_PEOPLE,
      TabIds.PRODUCTS,
      TabIds.PRODUCT_PACKAGINGS,
    ]);
  });

  test('a salesperson sees no tabs at all', () {
    expect(idsFor(UserRoles.SALESPERSON), isEmpty);
  });

  test('a plain user and an unknown role see no tabs', () {
    expect(idsFor(UserRoles.USER), isEmpty);
    expect(idsFor(null), isEmpty);
    expect(idsFor(''), isEmpty);
  });

  test('an admin cannot reach the admins tab by URL', () {
    expect(
      SidebarItems.isAccessible(TabIds.ADMINS, role: UserRoles.ADMIN),
      isFalse,
    );
    expect(
      SidebarItems.isAccessible(TabIds.ADMINS, role: UserRoles.SUPERUSER),
      isTrue,
    );
  });

  test('a salesperson cannot reach any tab by URL', () {
    for (final String id in <String>[
      TabIds.DASHBOARD,
      TabIds.ADMINS,
      TabIds.SALES_PEOPLE,
      TabIds.PRODUCTS,
      TabIds.PRODUCT_PACKAGINGS,
      TabIds.PROFILE,
    ]) {
      expect(
        SidebarItems.isAccessible(id, role: UserRoles.SALESPERSON),
        isFalse,
        reason: '$id should be blocked for a salesperson',
      );
    }
  });

  test('dashboard and profile stay reachable for permitted roles', () {
    for (final String role in <String>[UserRoles.SUPERUSER, UserRoles.ADMIN]) {
      expect(SidebarItems.isAccessible(TabIds.DASHBOARD, role: role), isTrue);
      expect(SidebarItems.isAccessible(TabIds.PROFILE, role: role), isTrue);
    }
  });

  test('role matching tolerates case and whitespace', () {
    expect(idsFor('  SuperUser ').contains(TabIds.ADMINS), isTrue);
    expect(idsFor(' ADMIN').contains(TabIds.ADMINS), isFalse);
    expect(idsFor(' ADMIN').contains(TabIds.PRODUCTS), isTrue);
  });

  test('product packagings is visible to superuser and admin alike', () {
    expect(idsFor(UserRoles.SUPERUSER).contains(TabIds.PRODUCT_PACKAGINGS),
        isTrue);
    expect(idsFor(UserRoles.ADMIN).contains(TabIds.PRODUCT_PACKAGINGS), isTrue);
  });

  test('product packagings is reachable by URL for permitted roles only', () {
    for (final String role in <String>[UserRoles.SUPERUSER, UserRoles.ADMIN]) {
      expect(
        SidebarItems.isAccessible(TabIds.PRODUCT_PACKAGINGS, role: role),
        isTrue,
        reason: 'product packagings should be reachable for $role',
      );
    }
    for (final String? role in <String?>[
      UserRoles.SALESPERSON,
      UserRoles.USER,
      null,
      '',
    ]) {
      expect(
        SidebarItems.isAccessible(TabIds.PRODUCT_PACKAGINGS, role: role),
        isFalse,
        reason: 'product packagings should be blocked for $role',
      );
    }
  });

  test('the product packagings tab id is a known tab', () {
    expect(SidebarItems.isKnown(TabIds.PRODUCT_PACKAGINGS), isTrue);
  });
}
