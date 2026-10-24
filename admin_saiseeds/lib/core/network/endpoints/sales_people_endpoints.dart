class SalesPeopleEndpoints {
  SalesPeopleEndpoints._();

  static const String _base = '/api/sales-admin/sales-people';

  static const String list = _base;
  static const String create = _base;

  static String detail(String id) => '$_base/$id';

  static const String allIncludingRemoved =
      '/api/sales-admin/all-sales-person/';

  static String byLiveSalesPerson(int id) =>
      '/api/sales-admin/client/by-sales-person/$id';

  static const String transferClients =
      '/api/sales-admin/client/transfer-client/';
}
