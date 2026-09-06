import 'package:flutter/foundation.dart';

class ObservabilityConfig {
  ObservabilityConfig._();

  static const String sentryDsn = String.fromEnvironment('SENTRY_DSN');

  static const double _releaseTracesSampleRate = 0.01;
  static const double _debugTracesSampleRate = 0.0;

  static const String _releaseEnvironment = 'production';
  static const String _debugEnvironment = 'development';

  static const String _appName = 'admin_saiseeds';
  static const String _appVersion = '1.0.0+1';

  static String get release => '$_appName@$_appVersion';

  static bool get isEnabled => sentryDsn.isNotEmpty;

  static double get tracesSampleRate =>
      kReleaseMode ? _releaseTracesSampleRate : _debugTracesSampleRate;

  static String get environment =>
      kReleaseMode ? _releaseEnvironment : _debugEnvironment;
}
