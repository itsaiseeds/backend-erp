class ProductPackagingsEndpoints {
  ProductPackagingsEndpoints._();

  static const String _base = '/api/sales-admin/product-packagings';

  static const String list = _base;
  static const String create = _base;

  static String detail(String publicId) => '$_base/$publicId';
}
