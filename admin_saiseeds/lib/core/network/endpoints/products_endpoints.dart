class ProductsEndpoints {
  ProductsEndpoints._();

  static const String _base = '/api/sales-admin/products';

  static const String list = _base;
  static const String UsableList = "$_base?is_usable=all";
  static const String create = _base;

  static String detail(String publicId) => '$_base/$publicId';
}
