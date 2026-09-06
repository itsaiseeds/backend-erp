class AuthEndpoints {
  AuthEndpoints._();

  static const String _base = '/api/sales-admin/auth';

  static const String verifyOtp = '$_base/otp/verify';
  static const String logout = '$_base/logout';
}
