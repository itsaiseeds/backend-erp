class AppConfigKeys {
  AppConfigKeys._();

  static const String ENV_FILE_DEV = '.env.dev';
  static const String ENV_FILE_PROD = '.env.prod';

  static const String API_BASE_URL = 'API_BASE_URL';
  static const String SENTRY_DSN = 'SENTRY_DSN';
  static const String SENTRY_ENVIRONMENT = 'SENTRY_ENVIRONMENT';

  static const bool _isRelease = bool.fromEnvironment('dart.vm.product');

  static String get envFile => _isRelease ? ENV_FILE_PROD : ENV_FILE_DEV;
}
