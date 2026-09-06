class SalesPeopleEndpoints {
  SalesPeopleEndpoints._();

  static const String _base = '/api/sales-admin/sales-people';

  static const String list = _base;
  static const String create = _base;

  static String detail(String id) => '$_base/$id';
}
