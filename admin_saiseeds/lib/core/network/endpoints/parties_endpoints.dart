class PartiesEndpoints {
  PartiesEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/parties';
  static const String create = '$_base/parties';

  static String detail(int id) => '$_base/parties/$id';
}
