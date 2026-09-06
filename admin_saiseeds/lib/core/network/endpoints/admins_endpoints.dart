class AdminsEndpoints {
  AdminsEndpoints._();

  static const String _base = '/api/sales-admin/admins';

  static const String list = _base;
  static const String create = _base;

  static String detail(String id) => '$_base/$id';
}
