class ClientsEndpoints {
  ClientsEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/get-clients/';
  static const String verify = '$_base/verify-client/';
  static const String update = '$_base/update-client/';

  static String detail(String publicId) => '$_base/client/$publicId';
}
