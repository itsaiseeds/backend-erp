class WasteManagementEndpoints {
  WasteManagementEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/raw-material-wastes';
  static const String create = '$_base/raw-material-wastes';

  static String detail(String publicId) =>
      '$_base/raw-material-waste/$publicId';
}
