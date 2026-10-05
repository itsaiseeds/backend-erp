class GodownManagersEndpoints {
  GodownManagersEndpoints._();

  static const String _base = '/api/sales-admin/godown-managers';

  static const String list = _base;
  static const String create = _base;

  static String detail(String id) => '$_base/$id';
}
