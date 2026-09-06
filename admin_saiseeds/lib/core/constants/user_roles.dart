class UserRoles {
  UserRoles._();

  static const String SUPERUSER = 'superuser';
  static const String ADMIN = 'admin';
  static const String SALESPERSON = 'salesperson';
  static const String USER = 'user';

  static const List<String> PORTAL_ACCESS = [SUPERUSER, ADMIN];

  static String _normalise(String? role) => (role ?? '').trim().toLowerCase();

  static bool isSuperuser(String? role) => _normalise(role) == SUPERUSER;

  static bool isAdmin(String? role) => _normalise(role) == ADMIN;

  static bool canAccessPortal(String? role) =>
      PORTAL_ACCESS.contains(_normalise(role));
}
